"""Opérations Redis pour la couche sociale du Monde de Luna.

Clés utilisées (préfixées par tenant) :
  luna:{tid}:world:privacy       → hash (paramètres confidentialité)
  luna:{tid}:world:avatar        → hash (config avatar)
  luna:{tid}:world:invitations   → zset (invitations reçues, score=timestamp)
  luna:{tid}:world:sent_invites  → zset (invitations envoyées)
  luna:{tid}:world:presence      → hash (position + statut dans le monde)
  luna:{tid}:world:chat          → list (messages du monde, max 100)
  luna:{tid}:world:visitors      → set (tids des visiteurs actuels)
  luna:{tid}:world:host          → string (tid de l'hôte du monde)
  luna:{tid}:world:joined_at    → string (timestamp d'entrée dans le monde)
  luna:{tid}:world:notifications → list (notifications non lues, max 50)

Clés globales (scope monde) :
  world:active:{world_id}        → zset (tids actifs dans ce monde, score=timestamp)
  world:invitation:{invite_id}   → hash (détail d'une invitation)
"""

import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Set

logger = logging.getLogger(__name__)

# TTL constants
TTL_INVITATION = 24 * 60 * 60          # 24h
TTL_WORLD_PRESENCE = 10 * 60           # 10 min (heartbeat monde)
TTL_CHAT_MESSAGE = 24 * 60 * 60        # 24h
TTL_NOTIFICATION = 7 * 24 * 60 * 60    # 7 jours
MAX_WORLD_CHAT = 100
MAX_NOTIFICATIONS = 50
MAX_INVITATIONS_PENDING = 10


class WorldRedisOps:
    """Couche CRUD Redis pour le Monde de Luna social."""

    def __init__(self, redis_client):
        """redis_client: instance de RedisClient (core.memory.redis_client)."""
        self.rc = redis_client
        self.client = redis_client.client

    def _key(self, tid, *parts) -> str:
        """Clé Redis préfixée par tenant luna:{tid}:world:{...}"""
        return f"luna:{tid}:world:{':'.join(str(p) for p in parts)}"

    def _world_key(self, *parts) -> str:
        """Clé Redis globale scope monde."""
        return f"world:{':'.join(str(p) for p in parts)}"

    # =================================================================
    # PRIVACY SETTINGS
    # =================================================================

    def get_privacy(self, tid) -> Dict[str, str]:
        """Récupère les paramètres de confidentialité."""
        key = self._key(tid, "privacy")
        data = self.client.hgetall(key)
        if not data:
            defaults = {
                "visible_on_map": "true",
                "visible_in_world": "true",
                "accept_friend_requests": "true",
                "accept_world_invites": "true",
                "approximate_location_only": "true",
                "total_invisible": "false",
                "world_public": "false",
            }
            self.client.hset(key, mapping=defaults)
            return defaults
        if "world_public" not in data:
            data["world_public"] = "false"
        return data

    def set_privacy(self, tid, settings: Dict[str, str]) -> None:
        """Met à jour les paramètres de confidentialité."""
        tid = str(tid)
        key = self._key(tid, "privacy")
        self.client.hset(key, mapping=settings)
        # Maintain global public-worlds index
        if settings.get("world_public") == "true" and settings.get("total_invisible") != "true":
            self.client.sadd("world:public_worlds", tid)
        else:
            self.client.srem("world:public_worlds", tid)

    def is_visible_on_map(self, tid) -> bool:
        """L'utilisateur est-il visible sur la carte ?"""
        data = self.get_privacy(tid)
        if data.get("total_invisible") == "true":
            return False
        return data.get("visible_on_map", "true") == "true"

    def is_visible_in_world(self, tid) -> bool:
        """L'utilisateur est-il visible dans le monde ?"""
        data = self.get_privacy(tid)
        if data.get("total_invisible") == "true":
            return False
        return data.get("visible_in_world", "true") == "true"

    def accepts_friend_requests(self, tid) -> bool:
        data = self.get_privacy(tid)
        if data.get("total_invisible") == "true":
            return False
        return data.get("accept_friend_requests", "true") == "true"

    def accepts_world_invites(self, tid) -> bool:
        data = self.get_privacy(tid)
        if data.get("total_invisible") == "true":
            return False
        return data.get("accept_world_invites", "true") == "true"

    def is_world_public(self, tid) -> bool:
        """Le monde de cet utilisateur est-il public (accessible à tous ses amis) ?"""
        data = self.get_privacy(tid)
        if data.get("total_invisible") == "true":
            return False
        return data.get("world_public", "false") == "true"

    # =================================================================
    # AVATAR CONFIG
    # =================================================================

    def get_avatar(self, tid) -> Dict[str, str]:
        """Récupère la configuration avatar."""
        key = self._key(tid, "avatar")
        data = self.client.hgetall(key)
        if not data:
            defaults = {
                "gender": "neutral",
                "body_style": "standard",
                "hair": "default",
                "outfit": "default",
                "aura": "none",
                "frame": "none",
                "primary_color": "#a78bfa",
                "badge_featured": "",
                "face_expression": "smile",
            }
            self.client.hset(key, mapping=defaults)
            return defaults
        return data

    def set_avatar(self, tid, config: Dict[str, str]) -> None:
        """Met à jour la configuration avatar."""
        key = self._key(tid, "avatar")
        self.client.hset(key, mapping=config)

    # =================================================================
    # WORLD INVITATIONS
    # =================================================================

    def create_invitation(self, from_tid, to_tid, message: str = "") -> Optional[str]:
        """Crée une invitation dans le monde. Retourne l'ID ou None si impossible."""
        from_tid, to_tid = str(from_tid), str(to_tid)

        # Vérifier que le destinataire accepte les invitations
        if not self.accepts_world_invites(to_tid):
            return None

        # Vérifier pas déjà dans le monde de l'hôte
        visitors = self.get_visitors(from_tid)
        if to_tid in visitors:
            return None

        # Vérifier limite d'invitations en attente
        pending = self.client.zcard(self._key(to_tid, "invitations"))
        if pending >= MAX_INVITATIONS_PENDING:
            return None

        invite_id = secrets.token_hex(8)
        now = datetime.utcnow().timestamp()
        invite_data = {
            "id": invite_id,
            "from_tid": from_tid,
            "to_tid": to_tid,
            "message": message or "",
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        }

        # Stocker l'invitation
        self.client.hset(self._world_key("invitation", invite_id), mapping=invite_data)
        self.client.expire(self._world_key("invitation", invite_id), TTL_INVITATION)

        # Ajouter à la liste des invitations reçues du destinataire
        self.client.zadd(self._key(to_tid, "invitations"), {invite_id: now})
        self.client.expire(self._key(to_tid, "invitations"), TTL_INVITATION)

        # Ajouter à la liste des invitations envoyées
        self.client.zadd(self._key(from_tid, "sent_invites"), {invite_id: now})
        self.client.expire(self._key(from_tid, "sent_invites"), TTL_INVITATION)

        return invite_id

    def get_invitation(self, invite_id: str) -> Optional[Dict[str, str]]:
        """Récupère le détail d'une invitation."""
        data = self.client.hgetall(self._world_key("invitation", invite_id))
        return data if data else None

    def get_pending_invitations(self, tid) -> List[Dict]:
        """Récupère les invitations reçues en attente avec détails."""
        tid = str(tid)
        invite_ids = self.client.zrange(self._key(tid, "invitations"), 0, -1)
        invitations = []
        for iid in (invite_ids or []):
            data = self.get_invitation(iid)
            if data and data.get("status") == "pending":
                # Vérifier expiration
                expires = data.get("expires_at", "")
                if expires:
                    try:
                        exp_dt = datetime.fromisoformat(expires)
                        if datetime.utcnow() > exp_dt:
                            self._expire_invitation(iid)
                            continue
                    except Exception:
                        pass
                invitations.append(data)
        return invitations

    def get_sent_invitations(self, tid) -> List[Dict]:
        """Récupère les invitations envoyées avec détails."""
        tid = str(tid)
        invite_ids = self.client.zrange(self._key(tid, "sent_invites"), 0, -1)
        invitations = []
        for iid in (invite_ids or []):
            data = self.get_invitation(iid)
            if data:
                invitations.append(data)
        return invitations

    def _expire_invitation(self, invite_id: str) -> None:
        """Marque une invitation comme expirée et nettoie."""
        key = self._world_key("invitation", invite_id)
        data = self.client.hgetall(key)
        if data:
            self.client.hset(key, "status", "expired")
            from_tid = data.get("from_tid", "")
            to_tid = data.get("to_tid", "")
            self.client.zrem(self._key(from_tid, "sent_invites"), invite_id)
            self.client.zrem(self._key(to_tid, "invitations"), invite_id)

    def respond_invitation(self, invite_id: str, action: str) -> bool:
        """Accepte ou refuse une invitation. Retourne True si succès."""
        data = self.get_invitation(invite_id)
        if not data or data.get("status") != "pending":
            return False

        from_tid = data.get("from_tid", "")
        to_tid = data.get("to_tid", "")

        if action == "accept":
            self.client.hset(self._world_key("invitation", invite_id), "status", "accepted")
            self.client.hset(self._world_key("invitation", invite_id), "responded_at", datetime.utcnow().isoformat())
            # Ajouter le visiteur au monde de l'hôte
            self.add_visitor(from_tid, to_tid)
            # Notifier l'hôte
            self.add_notification(from_tid, {
                "type": "world_invite_accepted",
                "message": f"Un ami a rejoint votre Monde de Luna !",
                "from_tid": to_tid,
                "invite_id": invite_id,
                "ts": datetime.utcnow().isoformat(),
            })
        elif action == "decline":
            self.client.hset(self._world_key("invitation", invite_id), "status", "refused")
            self.client.hset(self._world_key("invitation", invite_id), "responded_at", datetime.utcnow().isoformat())
            # Notifier l'hôte
            self.add_notification(from_tid, {
                "type": "world_invite_declined",
                "message": "Une invitation a été refusée.",
                "from_tid": to_tid,
                "invite_id": invite_id,
                "ts": datetime.utcnow().isoformat(),
            })
        else:
            return False

        # Nettoyer les listes
        self.client.zrem(self._key(to_tid, "invitations"), invite_id)
        self.client.zrem(self._key(from_tid, "sent_invites"), invite_id)
        return True

    def cancel_invitation(self, from_tid, invite_id: str) -> bool:
        """Annule une invitation envoyée."""
        data = self.get_invitation(invite_id)
        if not data or data.get("from_tid") != str(from_tid) or data.get("status") != "pending":
            return False
        to_tid = data.get("to_tid", "")
        self.client.hset(self._world_key("invitation", invite_id), "status", "cancelled")
        self.client.zrem(self._key(from_tid, "sent_invites"), invite_id)
        self.client.zrem(self._key(to_tid, "invitations"), invite_id)
        return True

    # =================================================================
    # WORLD PRESENCE & VISITORS
    # =================================================================

    def set_presence(self, tid, world_id: str, x: float = None, y: float = None, status: str = "online") -> None:
        """Met à jour la présence dans un monde."""
        tid = str(tid)
        key = self._key(tid, "presence")
        data = {
            "world_id": world_id,
            "status": status,
            "updated_at": datetime.utcnow().isoformat(),
        }
        if x is not None:
            data["x"] = str(round(x, 2))
        if y is not None:
            data["y"] = str(round(y, 2))
        self.client.hset(key, mapping=data)
        self.client.expire(key, TTL_WORLD_PRESENCE)

        # Index global
        self.client.zadd(self._world_key("active", world_id), {tid: datetime.utcnow().timestamp()})

    def get_presence(self, tid) -> Optional[Dict[str, str]]:
        """Récupère la présence actuelle."""
        return self.client.hgetall(self._key(tid, "presence")) or None

    def clear_presence(self, tid) -> None:
        """Supprime la présence (quand l'utilisateur quitte le monde)."""
        tid = str(tid)
        presence = self.get_presence(tid)
        if presence:
            world_id = presence.get("world_id", "world1")
            self.client.zrem(self._world_key("active", world_id), tid)
        self.client.delete(self._key(tid, "presence"))

    def get_active_in_world(self, world_id: str, limit: int = 50) -> List[str]:
        """Récupère les tids actifs dans un monde."""
        cutoff = datetime.utcnow().timestamp() - TTL_WORLD_PRESENCE
        return self.client.zrangebyscore(self._world_key("active", world_id), cutoff, "+inf", start=0, num=limit) or []

    def add_visitor(self, host_tid, visitor_tid) -> None:
        """Ajoute un visiteur au monde d'un hôte."""
        host_tid, visitor_tid = str(host_tid), str(visitor_tid)
        self.client.sadd(self._key(host_tid, "visitors"), visitor_tid)
        self.client.expire(self._key(host_tid, "visitors"), TTL_WORLD_PRESENCE * 2)
        # Marquer que le visiteur a rejoint ce monde
        self.client.set(self._key(visitor_tid, "host"), host_tid, ex=TTL_WORLD_PRESENCE * 2)
        self.client.set(self._key(visitor_tid, "joined_at"), datetime.utcnow().isoformat(), ex=TTL_WORLD_PRESENCE * 2)

    def remove_visitor(self, host_tid, visitor_tid) -> None:
        """Retire un visiteur du monde."""
        host_tid, visitor_tid = str(host_tid), str(visitor_tid)
        self.client.srem(self._key(host_tid, "visitors"), visitor_tid)
        self.client.delete(self._key(visitor_tid, "host"))
        self.client.delete(self._key(visitor_tid, "joined_at"))
        self.clear_presence(visitor_tid)

    def get_visitors(self, host_tid) -> Set[str]:
        """Récupère les visiteurs actuels du monde."""
        return self.client.smembers(self._key(host_tid, "visitors")) or set()

    def get_host(self, tid) -> Optional[str]:
        """Récupère l'hôte du monde dans lequel l'utilisateur est."""
        host = self.client.get(self._key(tid, "host"))
        return host.decode() if isinstance(host, bytes) else host

    # =================================================================
    # WORLD CHAT
    # =================================================================

    def add_chat_message(self, world_host_tid, sender_tid, sender_name: str, text: str) -> Dict:
        """Ajoute un message au chat du monde."""
        msg = {
            "id": secrets.token_hex(6),
            "sender_tid": str(sender_tid),
            "sender_name": sender_name,
            "text": text,
            "ts": datetime.utcnow().isoformat(),
        }
        key = self._key(world_host_tid, "chat")
        self.client.lpush(key, json.dumps(msg, ensure_ascii=False))
        self.client.ltrim(key, 0, MAX_WORLD_CHAT - 1)
        self.client.expire(key, TTL_CHAT_MESSAGE)
        return msg

    def get_chat_messages(self, world_host_tid, limit: int = 50) -> List[Dict]:
        """Récupère les derniers messages du chat."""
        key = self._key(world_host_tid, "chat")
        raw = self.client.lrange(key, 0, min(limit, MAX_WORLD_CHAT) - 1) or []
        messages = []
        for r in raw:
            try:
                messages.append(json.loads(r))
            except Exception:
                continue
        return messages

    # =================================================================
    # NOTIFICATIONS
    # =================================================================

    def add_notification(self, tid, notification: Dict) -> None:
        """Ajoute une notification pour un utilisateur."""
        key = self._key(tid, "notifications")
        self.client.lpush(key, json.dumps(notification, ensure_ascii=False))
        self.client.ltrim(key, 0, MAX_NOTIFICATIONS - 1)
        self.client.expire(key, TTL_NOTIFICATION)

    def get_notifications(self, tid, limit: int = 20) -> List[Dict]:
        """Récupère les notifications non lues."""
        key = self._key(tid, "notifications")
        raw = self.client.lrange(key, 0, min(limit, MAX_NOTIFICATIONS) - 1) or []
        notifications = []
        for r in raw:
            try:
                notifications.append(json.loads(r))
            except Exception:
                continue
        return notifications

    def clear_notifications(self, tid) -> None:
        """Supprime toutes les notifications."""
        self.client.delete(self._key(tid, "notifications"))

    def get_notification_count(self, tid) -> int:
        """Nombre de notifications non lues."""
        return self.client.llen(self._key(tid, "notifications")) or 0

    # =================================================================
    # CLEANUP
    # =================================================================

    def cleanup_expired_invitations(self) -> int:
        """Nettoie les invitations expirées. Retourne le nombre nettoyé."""
        # Scan toutes les invitations
        cleaned = 0
        cursor = 0
        while True:
            cursor, keys = self.client.scan(cursor, match="world:invitation:*", count=100)
            for key in keys:
                data = self.client.hgetall(key)
                if data:
                    status = data.get("status", "")
                    expires = data.get("expires_at", "")
                    if status == "pending" and expires:
                        try:
                            exp_dt = datetime.fromisoformat(expires)
                            if datetime.utcnow() > exp_dt:
                                invite_id = key.decode().split(":")[-1] if isinstance(key, bytes) else key.split(":")[-1]
                                self._expire_invitation(invite_id)
                                cleaned += 1
                        except Exception:
                            pass
            if cursor == 0:
                break
        return cleaned
