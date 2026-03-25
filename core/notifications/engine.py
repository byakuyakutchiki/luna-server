"""Luna Notification Engine - Duolingo-style, gentle encouragements."""

import logging
import time
import uuid
from datetime import datetime, date
from typing import Optional

from .redis_ops import NotificationRedisOps
from .templates import get_notification_message

logger = logging.getLogger(__name__)

# Frequency caps
MAX_NOTIFICATIONS_PER_DAY = 1
MAX_NOTIFICATIONS_PER_WEEK = 5

# Self rate-limit: check every 5 minutes
CHECK_INTERVAL = 300


class NotificationEngine:
    """Generates and delivers gentle Luna notifications."""

    def __init__(self, redis_client, sms_service=None):
        self.nops = NotificationRedisOps(redis_client)
        self.rc = redis_client
        self.sms = sms_service
        self._last_check = 0

    def should_check(self) -> bool:
        now = time.time()
        if now - self._last_check < CHECK_INTERVAL:
            return False
        self._last_check = now
        return True

    async def check_all_tenants(self, gops_class):
        """Main entry point: evaluate notifications for all tenants."""
        if not self.should_check():
            return

        try:
            tenant_ids = self.rc.get_all_tenant_ids()
        except Exception as e:
            logger.warning(f"Notification engine: cannot enumerate tenants: {e}")
            return

        for tid in tenant_ids:
            try:
                self._check_tenant(tid, gops_class)
            except Exception as e:
                logger.warning(f"Notification check failed for tenant {tid}: {e}")

    def _check_tenant(self, tenant_id: int, gops_class):
        """Evaluate notification triggers for a single tenant."""
        prefs = self.nops.get_prefs(tenant_id)

        # Global kill switch
        if prefs.get("enabled") != "1":
            return

        # Frequency cap: max 1/day, max 5/week
        daily_count = self.nops.count_recent(tenant_id, hours=24)
        if daily_count >= MAX_NOTIFICATIONS_PER_DAY:
            return
        weekly_count = self.nops.count_recent(tenant_id, hours=168)
        if weekly_count >= MAX_NOTIFICATIONS_PER_WEEK:
            return

        # Check quiet hours
        if self._in_quiet_hours(prefs):
            return

        # Get player state from gamification
        gops = gops_class(self.rc)
        player = gops.get_player(tenant_id)
        if not player:
            return

        # Evaluate triggers in priority order
        notification = None

        # 1. Streak risk (highest priority)
        if not notification and prefs.get("streak_risk") == "1":
            notification = self._eval_streak_risk(player, tenant_id)

        # 2. Comeback
        if not notification and prefs.get("comeback") == "1":
            notification = self._eval_comeback(player, tenant_id)

        # 3. Mission reminder
        if not notification and prefs.get("mission_reminder") == "1":
            notification = self._eval_mission_reminder(gops, tenant_id)

        # 4. Weekly summary (Sunday)
        if not notification and prefs.get("weekly_summary") == "1":
            notification = self._eval_weekly_summary(player, tenant_id)

        if notification:
            self._deliver(tenant_id, notification)

    def deliver_level_up(self, tenant_id: int, level: int, title: str):
        """Called directly from gamification engine on level-up (event-driven)."""
        prefs = self.nops.get_prefs(tenant_id)
        if prefs.get("enabled") != "1" or prefs.get("level_up") != "1":
            return
        if self._in_quiet_hours(prefs):
            return

        notif_title, notif_body = get_notification_message(
            "level_up", level=level, title=title
        )
        notification = {
            "id": str(uuid.uuid4()),
            "type": "level_up",
            "title": notif_title,
            "body": notif_body,
            "ts": datetime.utcnow().isoformat(),
        }
        self.nops.add_pending(tenant_id, notification)
        self.nops.log_delivery(tenant_id, "level_up", "in_app")
        logger.info(f"Level-up notification queued for tenant {tenant_id}: level {level}")

    # =========================================================================
    # TRIGGER EVALUATORS
    # =========================================================================

    def _eval_streak_risk(self, player: dict, tenant_id: int) -> Optional[dict]:
        streak = int(player.get("streak_days", 0))
        if streak < 2:
            return None
        last_active = player.get("last_active_date", "")
        if not last_active:
            return None
        try:
            last_date = date.fromisoformat(last_active)
            days_since = (date.today() - last_date).days
        except ValueError:
            return None
        # Only notify if absent exactly 1 day (streak at risk tomorrow)
        if days_since != 1:
            return None
        # Don't spam: check if already sent today
        if self.nops.count_recent_by_type(tenant_id, "streak_risk", hours=20) > 0:
            return None

        title, body = get_notification_message("streak_risk", streak=streak)
        return self._make_notification("streak_risk", title, body)

    def _eval_comeback(self, player: dict, tenant_id: int) -> Optional[dict]:
        last_active = player.get("last_active_date", "")
        if not last_active:
            return None
        try:
            last_date = date.fromisoformat(last_active)
            days_absent = (date.today() - last_date).days
        except ValueError:
            return None
        if days_absent < 2:
            return None
        # Max 1 comeback per 48h
        if self.nops.count_recent_by_type(tenant_id, "comeback", hours=48) > 0:
            return None

        title, body = get_notification_message("comeback", days=days_absent)
        return self._make_notification("comeback", title, body)

    def _eval_mission_reminder(self, gops, tenant_id: int) -> Optional[dict]:
        try:
            active_ids = gops.get_active_mission_ids(tenant_id)
        except Exception:
            return None
        for mid in active_ids:
            mission = gops.get_mission(tenant_id, mid)
            if not mission or mission.get("status") != "active":
                continue
            progress = int(mission.get("progress", 0))
            start_progress = int(mission.get("start_progress", 0))
            target = int(mission.get("target", 1))
            total_needed = target - start_progress
            if total_needed <= 0:
                continue
            delta = progress - start_progress
            if delta / total_needed >= 0.7:
                remaining = target - progress
                xp = mission.get("xp_reward", "0")
                mission_title = mission.get("title", "?")
                # Max 1 per 48h
                if self.nops.count_recent_by_type(tenant_id, "mission_reminder", hours=48) > 0:
                    return None
                title, body = get_notification_message(
                    "mission_reminder",
                    mission=mission_title,
                    remaining=remaining,
                    xp=xp,
                )
                return self._make_notification("mission_reminder", title, body)
        return None

    def _eval_weekly_summary(self, player: dict, tenant_id: int) -> Optional[dict]:
        if date.today().weekday() != 6:  # Sunday only
            return None
        if self.nops.count_recent_by_type(tenant_id, "weekly_summary", hours=24) > 0:
            return None
        messages = int(player.get("total_messages", 0))
        streak = int(player.get("streak_days", 0))
        xp = int(player.get("xp", 0))
        missions_done = int(player.get("missions_completed", 0))
        title, body = get_notification_message(
            "weekly_summary",
            messages=messages,
            streak=streak,
            xp_gained=xp,
            missions_done=missions_done,
        )
        return self._make_notification("weekly_summary", title, body)

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _make_notification(self, notif_type: str, title: str, body: str) -> dict:
        return {
            "id": str(uuid.uuid4()),
            "type": notif_type,
            "title": title,
            "body": body,
            "ts": datetime.utcnow().isoformat(),
        }

    def _deliver(self, tenant_id: int, notification: dict):
        self.nops.add_pending(tenant_id, notification)
        self.nops.log_delivery(tenant_id, notification["type"], "in_app")
        logger.info(f"Notification queued for tenant {tenant_id}: {notification['type']}")

        # Also send SMS for high-priority notifications
        if self.sms and notification.get("type") in ("reminder", "streak_risk", "alert"):
            try:
                import os
                phone = os.getenv("ADMIN_PHONE", "")
                if phone:
                    body = f"[Luna] {notification.get('title', 'Luna')}: {notification.get('body', '')[:140]}"
                    self.sms.send(phone, body)
                    self.nops.log_delivery(tenant_id, notification["type"], "sms")
            except Exception as e:
                logger.warning(f"Notification SMS delivery failed: {e}")

    def _in_quiet_hours(self, prefs: dict) -> bool:
        try:
            now = datetime.now()
            current_minutes = now.hour * 60 + now.minute
            start = prefs.get("quiet_hours_start", "22:00")
            end = prefs.get("quiet_hours_end", "07:00")
            sh, sm = int(start.split(":")[0]), int(start.split(":")[1])
            eh, em = int(end.split(":")[0]), int(end.split(":")[1])
            start_min = sh * 60 + sm
            end_min = eh * 60 + em
            if start_min > end_min:
                # Overnight: e.g., 22:00 -> 07:00
                return current_minutes >= start_min or current_minutes < end_min
            else:
                return start_min <= current_minutes < end_min
        except Exception:
            return False
