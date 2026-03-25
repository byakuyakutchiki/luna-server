"""Operations Redis pour les interactions sociales entre souscripteurs."""

import json
import logging
import secrets
import string
from datetime import datetime, date
from typing import Optional, Dict, List, Set

logger = logging.getLogger(__name__)

# TTL constants
TTL_DM_ROOM = 30 * 24 * 60 * 60       # 30 jours
TTL_DM_MESSAGES = 30 * 24 * 60 * 60    # 30 jours
TTL_ONLINE = 5 * 60                     # 5 minutes (heartbeat)
TTL_FRIEND_REQUEST = 30 * 24 * 60 * 60  # 30 jours
TTL_REPORT = 90 * 24 * 60 * 60         # 90 jours

MAX_DM_MESSAGES = 100
MAX_FRIENDS = 50
MAX_BLOCKED = 50
FRIEND_CODE_LENGTH = 6


class SocialRedisOps:
    """Couche CRUD Redis pour les interactions sociales.

    Toutes les cles sont prefixees 'social:' (scope exploitant, pas tenant).
    Compose sur le meme redis.StrictRedis client que RedisClient.
    """

    def __init__(self, redis_client):
        """redis_client: instance de RedisClient (core.memory.redis_client)."""
        self.rc = redis_client
        self.client = redis_client.client

    def _key(self, *parts) -> str:
        """Cle Redis social avec prefixe."""
        return "social:" + ":".join(str(p) for p in parts)

    # =================================================================
    # SOCIAL PROFILE
    # =================================================================

    def get_social_profile(self, tid) -> Optional[Dict[str, str]]:
        key = self._key("profile", tid)
        data = self.client.hgetall(key)
        return data if data else None

    def set_social_profile(self, tid, data: Dict[str, str]) -> None:
        key = self._key("profile", tid)
        self.client.hset(key, mapping=data)

    def update_social_profile(self, tid, field: str, value: str) -> None:
        key = self._key("profile", tid)
        self.client.hset(key, field, value)

    def get_all_social_profiles(self) -> List[Dict[str, str]]:
        """Retourne tous les profils sociaux (pour discover)."""
        profiles = []
        cursor = 0
        while True:
            cursor, keys = self.client.scan(cursor, match="social:profile:*", count=100)
            for key in keys:
                data = self.client.hgetall(key)
                if data:
                    # Extract tid from key social:profile:{tid}
                    parts = key.split(":")
                    if len(parts) >= 3:
                        data["tid"] = parts[2]
                        profiles.append(data)
            if cursor == 0:
                break
        return profiles

    # =================================================================
    # FRIEND CODE (6 chars alphanum, unique)
    # =================================================================

    def get_friend_code(self, tid) -> str:
        """Retourne le code ami du souscripteur, le cree si inexistant."""
        rev_key = self._key("friend_code_rev", tid)
        code = self.client.get(rev_key)
        if code:
            return code

        # Generate unique code
        for _ in range(10):
            chars = string.ascii_uppercase + string.digits
            code = "".join(secrets.choice(chars) for _ in range(FRIEND_CODE_LENGTH))
            code_key = self._key("friend_code", code)
            # SETNX for atomicity
            if self.client.setnx(code_key, str(tid)):
                self.client.set(rev_key, code)
                return code

        # Fallback: use tid-based code
        code = f"U{str(tid).zfill(FRIEND_CODE_LENGTH - 1)}"
        code_key = self._key("friend_code", code)
        self.client.set(code_key, str(tid))
        self.client.set(rev_key, code)
        return code

    def resolve_friend_code(self, code: str) -> Optional[str]:
        """Resout un code ami en tenant_id. Retourne None si invalide."""
        code_key = self._key("friend_code", code.upper())
        return self.client.get(code_key)

    # =================================================================
    # FRIEND REQUESTS
    # =================================================================

    def send_friend_request(self, from_tid, to_tid) -> bool:
        """Envoie une demande d'ami. Retourne False si deja ami/bloque/deja envoye."""
        from_tid, to_tid = str(from_tid), str(to_tid)

        # Check blocks
        if self.is_blocked(from_tid, to_tid) or self.is_blocked(to_tid, from_tid):
            return False

        # Check already friends
        if self.client.sismember(self._key("friends", from_tid), to_tid):
            return False

        # Check already sent
        if self.client.sismember(self._key("sent_requests", from_tid), to_tid):
            return False

        now = datetime.utcnow().timestamp()
        # Add to receiver's incoming requests
        self.client.zadd(self._key("friend_requests", to_tid), {from_tid: now})
        self.client.expire(self._key("friend_requests", to_tid), TTL_FRIEND_REQUEST)
        # Track sent (with same TTL as friend_requests)
        self.client.sadd(self._key("sent_requests", from_tid), to_tid)
        self.client.expire(self._key("sent_requests", from_tid), TTL_FRIEND_REQUEST)
        return True

    def get_friend_requests(self, tid) -> List[str]:
        """Demandes recues en attente (liste de tids)."""
        key = self._key("friend_requests", tid)
        return self.client.zrange(key, 0, -1) or []

    def get_pending_request_count(self, tid) -> int:
        key = self._key("friend_requests", tid)
        return self.client.zcard(key) or 0

    def accept_friend_request(self, tid, requester_tid) -> bool:
        """Accepter une demande. Cree l'amitie mutuelle."""
        tid, requester_tid = str(tid), str(requester_tid)

        # Verify request exists
        req_key = self._key("friend_requests", tid)
        if not self.client.zscore(req_key, requester_tid):
            return False

        # Check max friends
        if self.client.scard(self._key("friends", tid)) >= MAX_FRIENDS:
            return False
        if self.client.scard(self._key("friends", requester_tid)) >= MAX_FRIENDS:
            return False

        # Add mutual friendship
        self.client.sadd(self._key("friends", tid), requester_tid)
        self.client.sadd(self._key("friends", requester_tid), tid)

        # Remove request
        self.client.zrem(req_key, requester_tid)
        self.client.srem(self._key("sent_requests", requester_tid), tid)
        return True

    def decline_friend_request(self, tid, requester_tid) -> bool:
        """Refuser une demande."""
        tid, requester_tid = str(tid), str(requester_tid)
        req_key = self._key("friend_requests", tid)
        removed = self.client.zrem(req_key, requester_tid)
        self.client.srem(self._key("sent_requests", requester_tid), tid)
        return bool(removed)

    # =================================================================
    # FRIENDS
    # =================================================================

    def get_friends(self, tid) -> Set[str]:
        key = self._key("friends", tid)
        return self.client.smembers(key) or set()

    def remove_friend(self, tid, friend_tid) -> bool:
        """Retire l'amitie mutuelle."""
        tid, friend_tid = str(tid), str(friend_tid)
        r1 = self.client.srem(self._key("friends", tid), friend_tid)
        r2 = self.client.srem(self._key("friends", friend_tid), tid)
        return bool(r1 or r2)

    def get_friend_count(self, tid) -> int:
        return self.client.scard(self._key("friends", tid)) or 0

    # =================================================================
    # BLOCK / UNBLOCK
    # =================================================================

    def block_user(self, tid, target_tid) -> bool:
        """Bloque un utilisateur. Retire amitie + demandes d'ami en attente."""
        tid, target_tid = str(tid), str(target_tid)
        if self.client.scard(self._key("blocked", tid)) >= MAX_BLOCKED:
            return False
        self.client.sadd(self._key("blocked", tid), target_tid)
        # Remove friendship if exists
        self.remove_friend(tid, target_tid)
        # Remove pending friend requests in both directions
        self.client.zrem(self._key("friend_requests", tid), target_tid)
        self.client.zrem(self._key("friend_requests", target_tid), tid)
        self.client.srem(self._key("sent_requests", tid), target_tid)
        self.client.srem(self._key("sent_requests", target_tid), tid)
        return True

    def unblock_user(self, tid, target_tid) -> bool:
        tid, target_tid = str(tid), str(target_tid)
        return bool(self.client.srem(self._key("blocked", tid), target_tid))

    def is_blocked(self, tid, target_tid) -> bool:
        """Check if tid has blocked target_tid."""
        return bool(self.client.sismember(self._key("blocked", str(tid)), str(target_tid)))

    def get_blocked(self, tid) -> Set[str]:
        return self.client.smembers(self._key("blocked", tid)) or set()

    # =================================================================
    # DM ROOMS
    # =================================================================

    def _dm_room_id(self, tid1, tid2) -> str:
        """Deterministic room ID for a DM pair (sorted)."""
        a, b = sorted([str(tid1), str(tid2)])
        return f"dm_{a}_{b}"

    def create_dm_room(self, tid1, tid2) -> Optional[str]:
        """Cree ou recupere un DM room entre deux amis."""
        tid1, tid2 = str(tid1), str(tid2)

        # Must be friends
        if not self.client.sismember(self._key("friends", tid1), tid2):
            return None

        # Check blocks
        if self.is_blocked(tid1, tid2) or self.is_blocked(tid2, tid1):
            return None

        room_id = self._dm_room_id(tid1, tid2)
        room_key = self._key("dm", room_id)

        # Create if not exists
        if not self.client.exists(room_key):
            now = datetime.utcnow().isoformat()
            self.client.hset(room_key, mapping={
                "room_id": room_id,
                "tid1": tid1,
                "tid2": tid2,
                "created_at": now,
                "last_message_at": now,
            })

        self.client.expire(room_key, TTL_DM_ROOM)

        # Index for both users
        now_ts = datetime.utcnow().timestamp()
        self.client.zadd(self._key("dm_index", tid1), {room_id: now_ts})
        self.client.zadd(self._key("dm_index", tid2), {room_id: now_ts})
        return room_id

    def get_dm_rooms(self, tid) -> List[Dict[str, str]]:
        """Retourne les conversations DM du souscripteur (recentes en premier)."""
        index_key = self._key("dm_index", tid)
        room_ids = self.client.zrevrange(index_key, 0, 19) or []
        rooms = []
        for room_id in room_ids:
            room_key = self._key("dm", room_id)
            data = self.client.hgetall(room_key)
            if data:
                rooms.append(data)
        return rooms

    def get_dm_room(self, room_id: str) -> Optional[Dict[str, str]]:
        room_key = self._key("dm", room_id)
        data = self.client.hgetall(room_key)
        return data if data else None

    def add_dm_message(self, room_id: str, sender_tid, text: str) -> Dict:
        """Ajoute un message au DM. Retourne le message cree."""
        msg = {
            "id": secrets.token_hex(6),
            "sender": str(sender_tid),
            "text": text,
            "ts": datetime.utcnow().isoformat(),
        }
        msg_key = self._key("dm", room_id, "messages")
        self.client.lpush(msg_key, json.dumps(msg))
        self.client.ltrim(msg_key, 0, MAX_DM_MESSAGES - 1)
        self.client.expire(msg_key, TTL_DM_MESSAGES)

        # Update last_message_at on room
        room_key = self._key("dm", room_id)
        self.client.hset(room_key, "last_message_at", msg["ts"])
        self.client.expire(room_key, TTL_DM_ROOM)

        # Update index timestamps for both users + unread counter for receiver
        room_data = self.client.hgetall(room_key)
        if room_data:
            now_ts = datetime.utcnow().timestamp()
            tid1 = room_data.get("tid1", "")
            tid2 = room_data.get("tid2", "")
            self.client.zadd(self._key("dm_index", tid1), {room_id: now_ts})
            self.client.zadd(self._key("dm_index", tid2), {room_id: now_ts})
            # Increment unread for the OTHER user
            receiver = tid2 if str(sender_tid) == tid1 else tid1
            self.client.hincrby(self._key("dm_unread", receiver), room_id, 1)

        return msg

    def mark_dm_read(self, tid, room_id: str) -> None:
        """Marque un DM comme lu (reset le compteur non-lu pour ce room)."""
        self.client.hdel(self._key("dm_unread", str(tid)), room_id)

    def get_unread_dm_count(self, tid) -> int:
        """Nombre total de DM non-lus toutes rooms confondues."""
        data = self.client.hgetall(self._key("dm_unread", str(tid)))
        if not data:
            return 0
        total = 0
        for v in data.values():
            try:
                total += int(v)
            except (ValueError, TypeError):
                pass
        return total

    def get_unread_dm_per_room(self, tid) -> Dict[str, int]:
        """Compteur non-lu par room_id."""
        data = self.client.hgetall(self._key("dm_unread", str(tid)))
        if not data:
            return {}
        result = {}
        for room_id, count in data.items():
            try:
                c = int(count)
                if c > 0:
                    result[room_id] = c
            except (ValueError, TypeError):
                pass
        return result

    def get_dm_messages(self, room_id: str, limit: int = 50) -> List[Dict]:
        """Retourne les derniers messages d'un DM (recents en premier)."""
        msg_key = self._key("dm", room_id, "messages")
        raw = self.client.lrange(msg_key, 0, min(limit, MAX_DM_MESSAGES) - 1) or []
        messages = []
        for r in raw:
            try:
                messages.append(json.loads(r))
            except (json.JSONDecodeError, TypeError):
                continue
        return messages

    # =================================================================
    # REPORTS
    # =================================================================

    def report_user(self, reporter_tid, target_tid, reason: str) -> None:
        report = {
            "reporter": str(reporter_tid),
            "target": str(target_tid),
            "reason": reason,
            "ts": datetime.utcnow().isoformat(),
        }
        key = self._key("reports")
        self.client.lpush(key, json.dumps(report))
        self.client.ltrim(key, 0, 199)  # Keep last 200 reports
        self.client.expire(key, TTL_REPORT)

    def get_reports(self, limit: int = 50) -> List[Dict]:
        key = self._key("reports")
        raw = self.client.lrange(key, 0, limit - 1) or []
        reports = []
        for r in raw:
            try:
                reports.append(json.loads(r))
            except (json.JSONDecodeError, TypeError):
                continue
        return reports

    # =================================================================
    # ONLINE PRESENCE
    # =================================================================

    def set_online(self, tid) -> None:
        key = self._key("online")
        now = datetime.utcnow().timestamp()
        self.client.zadd(key, {str(tid): now})
        # Periodically purge stale entries (every ~50 heartbeats via probabilistic cleanup)
        if int(now) % 50 == 0:
            cutoff = now - TTL_ONLINE * 2
            self.client.zremrangebyscore(key, 0, cutoff)

    def set_offline(self, tid) -> None:
        key = self._key("online")
        self.client.zrem(key, str(tid))

    def is_online(self, tid) -> bool:
        key = self._key("online")
        score = self.client.zscore(key, str(tid))
        if score is None:
            return False
        # Online if heartbeat within TTL_ONLINE
        return (datetime.utcnow().timestamp() - score) < TTL_ONLINE

    def get_online_tids(self) -> Set[str]:
        """Retourne tous les tids en ligne (heartbeat recent)."""
        key = self._key("online")
        cutoff = datetime.utcnow().timestamp() - TTL_ONLINE
        return set(self.client.zrangebyscore(key, cutoff, "+inf") or [])

    def get_online_friends(self, tid) -> Set[str]:
        """Retourne les amis en ligne."""
        friends = self.get_friends(tid)
        if not friends:
            return set()
        online = self.get_online_tids()
        return friends & online
