"""Redis operations for Luna notification system."""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger(__name__)

TTL_NOTIFICATION_LOG = 30 * 24 * 60 * 60  # 30 jours
TTL_PENDING = 7 * 24 * 60 * 60  # 7 jours
MAX_PENDING = 20

DEFAULT_PREFS = {
    "enabled": "1",
    "streak_risk": "1",
    "comeback": "1",
    "mission_reminder": "1",
    "level_up": "1",
    "weekly_summary": "1",
    "sound": "1",
    "quiet_hours_start": "22:00",
    "quiet_hours_end": "07:00",
}


class NotificationRedisOps:
    """Couche CRUD Redis pour les notifications Luna."""

    def __init__(self, redis_client):
        self.rc = redis_client

    def get_prefs(self, tenant_id: int) -> Dict[str, str]:
        key = self.rc._key(tenant_id, "notification_prefs")
        data = self.rc.client.hgetall(key)
        if not data:
            self.rc.client.hset(key, mapping=DEFAULT_PREFS)
            return dict(DEFAULT_PREFS)
        return data

    def update_pref(self, tenant_id: int, field: str, value: str) -> None:
        key = self.rc._key(tenant_id, "notification_prefs")
        self.rc.client.hset(key, field, value)

    def add_pending(self, tenant_id: int, notification: dict) -> None:
        key = self.rc._key(tenant_id, "notifications", "pending")
        self.rc.client.lpush(key, json.dumps(notification))
        self.rc.client.ltrim(key, 0, MAX_PENDING - 1)
        self.rc.client.expire(key, TTL_PENDING)

    def pop_pending(self, tenant_id: int, limit: int = 5) -> List[dict]:
        key = self.rc._key(tenant_id, "notifications", "pending")
        results = []
        for _ in range(limit):
            item = self.rc.client.rpop(key)
            if not item:
                break
            try:
                results.append(json.loads(item))
            except (json.JSONDecodeError, TypeError):
                pass
        return results

    def peek_pending(self, tenant_id: int) -> int:
        key = self.rc._key(tenant_id, "notifications", "pending")
        return self.rc.client.llen(key)

    def log_delivery(self, tenant_id: int, notif_type: str, channel: str) -> None:
        key = self.rc._key(tenant_id, "notifications", "log")
        entry = json.dumps({
            "type": notif_type,
            "channel": channel,
            "ts": datetime.utcnow().isoformat(),
        })
        self.rc.client.zadd(key, {entry: time.time()})
        self.rc.client.expire(key, TTL_NOTIFICATION_LOG)
        # Trim old entries (keep last 200)
        self.rc.client.zremrangebyrank(key, 0, -201)

    def count_recent(self, tenant_id: int, hours: int = 24) -> int:
        key = self.rc._key(tenant_id, "notifications", "log")
        cutoff = time.time() - (hours * 3600)
        return self.rc.client.zcount(key, cutoff, "+inf")

    def count_recent_by_type(self, tenant_id: int, notif_type: str, hours: int = 24) -> int:
        key = self.rc._key(tenant_id, "notifications", "log")
        cutoff = time.time() - (hours * 3600)
        entries = self.rc.client.zrangebyscore(key, cutoff, "+inf")
        count = 0
        for e in entries:
            try:
                data = json.loads(e)
                if data.get("type") == notif_type:
                    count += 1
            except (json.JSONDecodeError, TypeError):
                pass
        return count
