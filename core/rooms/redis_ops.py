"""Opérations Redis pour les salons famille."""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set

from .models import TTL_ROOM, TTL_ROOM_MESSAGES, MAX_ROOM_MESSAGES

logger = logging.getLogger(__name__)


class RoomRedisOps:
    """CRUD Redis pour les salons famille."""

    def __init__(self, redis_client):
        self.rc = redis_client

    def _key(self, tenant_id, *parts):
        return self.rc._key(tenant_id, "room", *parts)

    def _index_key(self, tenant_id):
        return self.rc._key(tenant_id, "rooms", "active")

    # ═══════════════════════════════════════════════════════════════════════
    # ROOM CRUD
    # ═══════════════════════════════════════════════════════════════════════

    def create_room(self, tenant_id: int, room_data: dict) -> str:
        room_id = room_data["id"]
        key = self._key(tenant_id, room_id)
        self.rc.client.hset(key, mapping=room_data)
        self.rc.client.expire(key, TTL_ROOM)
        # Add to active index
        self.rc.client.sadd(self._index_key(tenant_id), room_id)
        self.rc.client.expire(self._index_key(tenant_id), TTL_ROOM)
        logger.info(f"Room {room_id} created for tenant {tenant_id}")
        return room_id

    def get_room(self, tenant_id: int, room_id: str) -> Optional[dict]:
        key = self._key(tenant_id, room_id)
        data = self.rc.client.hgetall(key)
        return data if data else None

    def update_room(self, tenant_id: int, room_id: str, fields: dict) -> None:
        key = self._key(tenant_id, room_id)
        fields["updated_at"] = datetime.utcnow().isoformat()
        self.rc.client.hset(key, mapping=fields)

    def delete_room(self, tenant_id: int, room_id: str) -> None:
        self.rc.client.delete(self._key(tenant_id, room_id))
        self.rc.client.delete(self._key(tenant_id, room_id, "members"))
        self.rc.client.delete(self._key(tenant_id, room_id, "messages"))
        self.rc.client.srem(self._index_key(tenant_id), room_id)
        logger.info(f"Room {room_id} deleted for tenant {tenant_id}")

    def list_rooms(self, tenant_id: int) -> List[dict]:
        room_ids = self.rc.client.smembers(self._index_key(tenant_id)) or set()
        rooms = []
        for rid in room_ids:
            r = self.get_room(tenant_id, rid)
            if r:
                rooms.append(r)
            else:
                # Expired room, clean up index
                self.rc.client.srem(self._index_key(tenant_id), rid)
        return rooms

    # ═══════════════════════════════════════════════════════════════════════
    # PARTICIPANTS
    # ═══════════════════════════════════════════════════════════════════════

    def join_room(self, tenant_id: int, room_id: str, phone: str) -> bool:
        key = self._key(tenant_id, room_id, "members")
        count = self.rc.client.scard(key) or 0
        room = self.get_room(tenant_id, room_id)
        max_p = int(room.get("max_participants", "10")) if room else 10
        if count >= max_p:
            return False
        self.rc.client.sadd(key, phone)
        self.rc.client.expire(key, TTL_ROOM)
        return True

    def leave_room(self, tenant_id: int, room_id: str, phone: str) -> None:
        key = self._key(tenant_id, room_id, "members")
        self.rc.client.srem(key, phone)

    def get_participants(self, tenant_id: int, room_id: str) -> Set[str]:
        key = self._key(tenant_id, room_id, "members")
        return self.rc.client.smembers(key) or set()

    def count_participants(self, tenant_id: int, room_id: str) -> int:
        key = self._key(tenant_id, room_id, "members")
        return self.rc.client.scard(key) or 0

    # ═══════════════════════════════════════════════════════════════════════
    # MESSAGES
    # ═══════════════════════════════════════════════════════════════════════

    def add_message(self, tenant_id: int, room_id: str, msg_json: str) -> None:
        key = self._key(tenant_id, room_id, "messages")
        self.rc.client.lpush(key, msg_json)
        self.rc.client.ltrim(key, 0, MAX_ROOM_MESSAGES - 1)
        self.rc.client.expire(key, TTL_ROOM_MESSAGES)

    def get_messages(self, tenant_id: int, room_id: str,
                     limit: int = 50) -> List[str]:
        key = self._key(tenant_id, room_id, "messages")
        return self.rc.client.lrange(key, 0, min(limit, MAX_ROOM_MESSAGES) - 1) or []

    # ═══════════════════════════════════════════════════════════════════════
    # TTL REFRESH
    # ═══════════════════════════════════════════════════════════════════════

    def touch_room(self, tenant_id: int, room_id: str) -> None:
        """Refresh TTL on all room keys (called on activity)."""
        for suffix in [room_id, f"{room_id}:members", f"{room_id}:messages"]:
            key = self._key(tenant_id, suffix)
            self.rc.client.expire(key, TTL_ROOM)
