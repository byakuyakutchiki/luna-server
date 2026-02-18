"""Operations Redis pour la gamification IA Watch World."""

import json
import logging
from datetime import date, datetime
from typing import Optional, Dict, List, Set

logger = logging.getLogger(__name__)

# TTL constants
TTL_ACTIVITY = 90 * 24 * 60 * 60  # 90 jours
TTL_STABILITY = 7 * 24 * 60 * 60  # 7 jours
TTL_COMPLETED_MISSION = 30 * 24 * 60 * 60  # 30 jours
TTL_DAILY_CAP = 48 * 60 * 60  # 48 heures
TTL_ADMIN_METRICS = 60 * 60  # 1 heure

ACTIVITY_MAX = 50
MAX_ACTIVE_MISSIONS = 3


class GamificationRedisOps:
    """Couche CRUD Redis pour la gamification. Compose sur RedisClient."""

    def __init__(self, redis_client):
        self.rc = redis_client

    # =====================================================================
    # PLAYER STATE
    # =====================================================================

    def get_player(self, tenant_id) -> Optional[Dict[str, str]]:
        key = self.rc._key(tenant_id, "world", "player")
        data = self.rc.client.hgetall(key)
        return data if data else None

    def set_player(self, tenant_id, data: Dict[str, str]) -> None:
        key = self.rc._key(tenant_id, "world", "player")
        self.rc.client.hset(key, mapping=data)

    def increment_player_field(self, tenant_id, field: str, amount: int = 1) -> int:
        key = self.rc._key(tenant_id, "world", "player")
        return self.rc.client.hincrby(key, field, amount)

    def set_player_field(self, tenant_id, field: str, value: str) -> None:
        key = self.rc._key(tenant_id, "world", "player")
        self.rc.client.hset(key, field, value)

    def get_player_field(self, tenant_id, field: str) -> Optional[str]:
        key = self.rc._key(tenant_id, "world", "player")
        return self.rc.client.hget(key, field)

    # =====================================================================
    # BADGES
    # =====================================================================

    def get_badges(self, tenant_id) -> Set[str]:
        key = self.rc._key(tenant_id, "world", "badges")
        return self.rc.client.smembers(key) or set()

    def add_badge(self, tenant_id, badge_id: str, detail: Dict[str, str]) -> None:
        set_key = self.rc._key(tenant_id, "world", "badges")
        self.rc.client.sadd(set_key, badge_id)
        detail_key = self.rc._key(tenant_id, "world", "badge", badge_id)
        self.rc.client.hset(detail_key, mapping=detail)

    def get_badge_detail(self, tenant_id, badge_id: str) -> Optional[Dict[str, str]]:
        key = self.rc._key(tenant_id, "world", "badge", badge_id)
        data = self.rc.client.hgetall(key)
        return data if data else None

    # =====================================================================
    # MISSIONS
    # =====================================================================

    def get_active_mission_ids(self, tenant_id) -> Set[str]:
        key = self.rc._key(tenant_id, "world", "missions", "active")
        return self.rc.client.smembers(key) or set()

    def add_mission(self, tenant_id, mission_id: str, data: Dict[str, str]) -> None:
        active_key = self.rc._key(tenant_id, "world", "missions", "active")
        mission_key = self.rc._key(tenant_id, "world", "mission", mission_id)
        self.rc.client.sadd(active_key, mission_id)
        self.rc.client.hset(mission_key, mapping=data)

    def get_mission(self, tenant_id, mission_id: str) -> Optional[Dict[str, str]]:
        key = self.rc._key(tenant_id, "world", "mission", mission_id)
        data = self.rc.client.hgetall(key)
        return data if data else None

    def update_mission_field(self, tenant_id, mission_id: str, field: str, value: str) -> None:
        key = self.rc._key(tenant_id, "world", "mission", mission_id)
        self.rc.client.hset(key, field, value)

    def complete_mission(self, tenant_id, mission_id: str) -> None:
        now = datetime.utcnow()
        # Update mission status
        mission_key = self.rc._key(tenant_id, "world", "mission", mission_id)
        self.rc.client.hset(mission_key, mapping={
            "status": "completed",
            "completed_at": now.isoformat(),
        })
        self.rc.client.expire(mission_key, TTL_COMPLETED_MISSION)
        # Move from active to completed
        active_key = self.rc._key(tenant_id, "world", "missions", "active")
        self.rc.client.srem(active_key, mission_id)
        completed_key = self.rc._key(tenant_id, "world", "missions", "completed")
        self.rc.client.zadd(completed_key, {mission_id: now.timestamp()})

    def get_completed_missions_count(self, tenant_id) -> int:
        key = self.rc._key(tenant_id, "world", "missions", "completed")
        return self.rc.client.zcard(key) or 0

    def get_active_mission_types(self, tenant_id) -> Set[str]:
        """Returns the set of mission types currently active."""
        types = set()
        for mid in self.get_active_mission_ids(tenant_id):
            m = self.get_mission(tenant_id, mid)
            if m:
                types.add(m.get("type", ""))
        return types

    def get_recently_completed_types(self, tenant_id, days: int = 7) -> Set[str]:
        """Returns mission types completed in the last N days."""
        key = self.rc._key(tenant_id, "world", "missions", "completed")
        cutoff = (datetime.utcnow().timestamp()) - (days * 86400)
        recent_ids = self.rc.client.zrangebyscore(key, cutoff, "+inf")
        types = set()
        for mid in (recent_ids or []):
            m = self.get_mission(tenant_id, mid)
            if m:
                types.add(m.get("type", ""))
        return types

    # =====================================================================
    # ACTIVITY FEED
    # =====================================================================

    def add_activity(self, tenant_id, event_json: str) -> None:
        key = self.rc._key(tenant_id, "world", "activity")
        self.rc.client.lpush(key, event_json)
        self.rc.client.ltrim(key, 0, ACTIVITY_MAX - 1)
        self.rc.client.expire(key, TTL_ACTIVITY)

    def get_activity(self, tenant_id, limit: int = 30) -> List[str]:
        key = self.rc._key(tenant_id, "world", "activity")
        return self.rc.client.lrange(key, 0, min(limit, ACTIVITY_MAX) - 1) or []

    # =====================================================================
    # STABILITY GAUGE
    # =====================================================================

    def get_stability(self, tenant_id) -> Optional[Dict[str, str]]:
        key = self.rc._key(tenant_id, "world", "stability")
        data = self.rc.client.hgetall(key)
        return data if data else None

    def set_stability(self, tenant_id, data: Dict[str, str]) -> None:
        key = self.rc._key(tenant_id, "world", "stability")
        self.rc.client.hset(key, mapping=data)
        self.rc.client.expire(key, TTL_STABILITY)

    # =====================================================================
    # SHOP / INVENTORY
    # =====================================================================

    def get_inventory(self, tenant_id) -> Set[str]:
        """Get set of owned item IDs."""
        key = self.rc._key(tenant_id, "world", "inventory")
        return self.rc.client.smembers(key) or set()

    def add_to_inventory(self, tenant_id, item_id: str, detail: Dict[str, str]) -> None:
        """Add item to player inventory."""
        set_key = self.rc._key(tenant_id, "world", "inventory")
        self.rc.client.sadd(set_key, item_id)
        detail_key = self.rc._key(tenant_id, "world", "item", item_id)
        self.rc.client.hset(detail_key, mapping=detail)

    def get_item_detail(self, tenant_id, item_id: str) -> Optional[Dict[str, str]]:
        """Get detail of an owned item."""
        key = self.rc._key(tenant_id, "world", "item", item_id)
        data = self.rc.client.hgetall(key)
        return data if data else None

    def get_active_bonus(self, tenant_id, bonus_id: str) -> Optional[Dict[str, str]]:
        """Get active bonus data (returns None if expired/TTL)."""
        key = self.rc._key(tenant_id, "world", "bonus", bonus_id)
        data = self.rc.client.hgetall(key)
        return data if data else None

    def set_active_bonus(self, tenant_id, bonus_id: str, data: Dict[str, str],
                         ttl: int = 86400) -> None:
        """Activate a bonus with auto-expiration TTL."""
        key = self.rc._key(tenant_id, "world", "bonus", bonus_id)
        self.rc.client.hset(key, mapping=data)
        self.rc.client.expire(key, ttl)

    # =====================================================================
    # DAILY XP CAP
    # =====================================================================

    def check_and_increment_daily_cap(self, tenant_id, action: str) -> int:
        """Atomically increment daily action counter. Returns new count."""
        today = date.today().isoformat()
        key = self.rc._key(tenant_id, "world", "dailycap", today, action)
        count = self.rc.client.incr(key)
        if count == 1:
            self.rc.client.expire(key, TTL_DAILY_CAP)
        return count

    # =====================================================================
    # ADMIN METRICS (cached)
    # =====================================================================

    def get_admin_metrics(self) -> Optional[Dict[str, str]]:
        key = self.rc._key("admin", "world", "metrics")
        data = self.rc.client.hgetall(key)
        return data if data else None

    def set_admin_metrics(self, data: Dict[str, str]) -> None:
        key = self.rc._key("admin", "world", "metrics")
        self.rc.client.hset(key, mapping=data)
        self.rc.client.expire(key, TTL_ADMIN_METRICS)

    # =====================================================================
    # FAMILY LEVEL
    # =====================================================================

    def get_family_level(self, tenant_id) -> Optional[Dict[str, str]]:
        key = self.rc._key(tenant_id, "world", "family_level")
        data = self.rc.client.hgetall(key)
        return data if data else None

    def set_family_level(self, tenant_id, data: Dict[str, str]) -> None:
        key = self.rc._key(tenant_id, "world", "family_level")
        self.rc.client.hset(key, mapping=data)

    def increment_family_xp(self, tenant_id, amount: int) -> int:
        key = self.rc._key(tenant_id, "world", "family_level")
        return self.rc.client.hincrby(key, "family_xp", amount)

    def get_family_xp(self, tenant_id) -> int:
        key = self.rc._key(tenant_id, "world", "family_level")
        val = self.rc.client.hget(key, "family_xp")
        return int(val) if val else 0

    # =====================================================================
    # ACTIVE OUTFIT
    # =====================================================================

    def get_active_outfit(self, tenant_id) -> Optional[str]:
        key = self.rc._key(tenant_id, "world", "active_outfit")
        return self.rc.client.get(key)

    def set_active_outfit(self, tenant_id, outfit_id: str) -> None:
        key = self.rc._key(tenant_id, "world", "active_outfit")
        if outfit_id:
            self.rc.client.set(key, outfit_id)
        else:
            self.rc.client.delete(key)

    # =====================================================================
    # ACTIVE FRAME (profile frame)
    # =====================================================================

    def get_active_frame(self, tenant_id) -> Optional[str]:
        key = self.rc._key(tenant_id, "world", "active_frame")
        return self.rc.client.get(key)

    def set_active_frame(self, tenant_id, frame_id: str) -> None:
        key = self.rc._key(tenant_id, "world", "active_frame")
        if frame_id:
            self.rc.client.set(key, frame_id)
        else:
            self.rc.client.delete(key)

    # =====================================================================
    # AVATAR TYPE (subscriber appearance choice)
    # =====================================================================

    def get_avatar_type(self, tenant_id) -> Optional[str]:
        key = self.rc._key(tenant_id, "world", "avatar_type")
        return self.rc.client.get(key)

    def set_avatar_type(self, tenant_id, avatar_type: str) -> None:
        key = self.rc._key(tenant_id, "world", "avatar_type")
        if avatar_type:
            self.rc.client.set(key, avatar_type)
        else:
            self.rc.client.delete(key)

    # =====================================================================
    # ACTIVE WORLD (world1 / world2)
    # =====================================================================

    def get_active_world(self, tenant_id) -> str:
        key = self.rc._key(tenant_id, "world", "active_world")
        val = self.rc.client.get(key)
        return val if val else "world1"

    def set_active_world(self, tenant_id, world: str) -> None:
        key = self.rc._key(tenant_id, "world", "active_world")
        self.rc.client.set(key, world)
