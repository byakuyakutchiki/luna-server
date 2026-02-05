"""
Luna Redis Client - Client Redis avec gestion des clés Luna
"""
import os
import logging
from typing import Optional, List, Dict, Any
from functools import lru_cache
import redis

logger = logging.getLogger(__name__)

# Configuration Redis par défaut
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_PREFIX = "luna"

# TTL par défaut (en secondes)
TTL_MESSAGES = 30 * 24 * 60 * 60  # 30 jours
TTL_SESSIONS = 24 * 60 * 60  # 24 heures
TTL_COMPLETED_TASKS = 7 * 24 * 60 * 60  # 7 jours
TTL_NOTES = 90 * 24 * 60 * 60  # 90 jours
TTL_DAILY_USAGE = 90 * 24 * 60 * 60  # 90 jours


class RedisClient:
    """
    Client Redis pour Luna avec gestion des clés préfixées.
    """

    def __init__(self, url: str = REDIS_URL, prefix: str = REDIS_PREFIX):
        self.prefix = prefix
        self._client: Optional[redis.Redis] = None
        self._url = url

    @property
    def client(self) -> redis.Redis:
        """Lazy initialization du client Redis"""
        if self._client is None:
            self._client = redis.from_url(
                self._url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
        return self._client

    def _key(self, *parts: str) -> str:
        """Construit une clé Redis avec le préfixe"""
        return f"{self.prefix}:{':'.join(str(p) for p in parts)}"

    # ========================================================================
    # HEALTH CHECK
    # ========================================================================

    def ping(self) -> bool:
        """Vérifie la connexion Redis"""
        try:
            return self.client.ping()
        except redis.RedisError as e:
            logger.error(f"Redis ping failed: {e}")
            return False

    def get_info(self) -> Dict[str, Any]:
        """Retourne les infos Redis"""
        try:
            info = self.client.info()
            return {
                "connected": True,
                "version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "uptime_days": info.get("uptime_in_days"),
            }
        except redis.RedisError as e:
            return {"connected": False, "error": str(e)}

    # ========================================================================
    # CONVERSATIONS
    # ========================================================================

    def get_conversations_key(self, tenant_id: int) -> str:
        """Clé pour la liste des conversations d'un tenant"""
        return self._key(tenant_id, "conversations")

    def get_conversation_meta_key(self, tenant_id: int, conv_id: str) -> str:
        """Clé pour les métadonnées d'une conversation"""
        return self._key(tenant_id, "conv", conv_id, "meta")

    def get_conversation_messages_key(self, tenant_id: int, conv_id: str) -> str:
        """Clé pour les messages d'une conversation"""
        return self._key(tenant_id, "conv", conv_id, "messages")

    def add_conversation(self, tenant_id: int, conv_id: str) -> None:
        """Ajoute une conversation à la liste du tenant"""
        self.client.sadd(self.get_conversations_key(tenant_id), conv_id)

    def remove_conversation(self, tenant_id: int, conv_id: str) -> None:
        """Supprime une conversation"""
        key = self.get_conversations_key(tenant_id)
        self.client.srem(key, conv_id)
        # Supprime aussi les données associées
        self.client.delete(
            self.get_conversation_meta_key(tenant_id, conv_id),
            self.get_conversation_messages_key(tenant_id, conv_id),
        )

    def get_conversation_ids(self, tenant_id: int) -> List[str]:
        """Retourne les IDs de toutes les conversations du tenant"""
        return list(self.client.smembers(self.get_conversations_key(tenant_id)))

    def set_conversation_meta(self, tenant_id: int, conv_id: str, data: Dict[str, str]) -> None:
        """Définit les métadonnées d'une conversation"""
        key = self.get_conversation_meta_key(tenant_id, conv_id)
        self.client.hset(key, mapping=data)
        self.client.expire(key, TTL_MESSAGES)

    def get_conversation_meta(self, tenant_id: int, conv_id: str) -> Optional[Dict[str, str]]:
        """Récupère les métadonnées d'une conversation"""
        key = self.get_conversation_meta_key(tenant_id, conv_id)
        data = self.client.hgetall(key)
        return data if data else None

    def add_message(self, tenant_id: int, conv_id: str, message_json: str) -> None:
        """Ajoute un message à une conversation"""
        key = self.get_conversation_messages_key(tenant_id, conv_id)
        self.client.rpush(key, message_json)
        self.client.expire(key, TTL_MESSAGES)

    def get_messages(
        self,
        tenant_id: int,
        conv_id: str,
        start: int = 0,
        end: int = -1
    ) -> List[str]:
        """Récupère les messages d'une conversation"""
        key = self.get_conversation_messages_key(tenant_id, conv_id)
        return self.client.lrange(key, start, end)

    def get_message_count(self, tenant_id: int, conv_id: str) -> int:
        """Compte les messages d'une conversation"""
        key = self.get_conversation_messages_key(tenant_id, conv_id)
        return self.client.llen(key)

    # ========================================================================
    # INSTRUCTIONS
    # ========================================================================

    def get_instructions_active_key(self, tenant_id: int) -> str:
        """Clé pour les instructions actives"""
        return self._key(tenant_id, "instructions", "active")

    def get_instruction_key(self, tenant_id: int, instr_id: str) -> str:
        """Clé pour une instruction"""
        return self._key(tenant_id, "instruction", instr_id)

    def add_instruction(
        self,
        tenant_id: int,
        instr_id: str,
        data: Dict[str, str],
        priority: int = 5
    ) -> None:
        """Ajoute une instruction"""
        # Stocke les données
        key = self.get_instruction_key(tenant_id, instr_id)
        self.client.hset(key, mapping=data)

        # Ajoute à l'index des actives si enabled
        if data.get("enabled") == "1":
            self.client.zadd(
                self.get_instructions_active_key(tenant_id),
                {instr_id: priority}
            )

    def get_instruction(self, tenant_id: int, instr_id: str) -> Optional[Dict[str, str]]:
        """Récupère une instruction"""
        key = self.get_instruction_key(tenant_id, instr_id)
        data = self.client.hgetall(key)
        return data if data else None

    def get_active_instructions(self, tenant_id: int) -> List[str]:
        """Récupère les IDs des instructions actives par priorité"""
        key = self.get_instructions_active_key(tenant_id)
        # Retourne par priorité décroissante
        return self.client.zrevrange(key, 0, -1)

    def disable_instruction(self, tenant_id: int, instr_id: str) -> None:
        """Désactive une instruction"""
        # Met à jour le flag
        key = self.get_instruction_key(tenant_id, instr_id)
        self.client.hset(key, "enabled", "0")
        # Retire de l'index actif
        self.client.zrem(self.get_instructions_active_key(tenant_id), instr_id)

    def delete_instruction(self, tenant_id: int, instr_id: str) -> None:
        """Supprime une instruction"""
        self.client.delete(self.get_instruction_key(tenant_id, instr_id))
        self.client.zrem(self.get_instructions_active_key(tenant_id), instr_id)

    # ========================================================================
    # TASKS
    # ========================================================================

    def get_tasks_pending_key(self, tenant_id: int) -> str:
        """Clé pour les tâches en attente"""
        return self._key(tenant_id, "tasks", "pending")

    def get_tasks_completed_key(self, tenant_id: int) -> str:
        """Clé pour les tâches terminées"""
        return self._key(tenant_id, "tasks", "completed")

    def get_task_key(self, tenant_id: int, task_id: str) -> str:
        """Clé pour une tâche"""
        return self._key(tenant_id, "task", task_id)

    def add_task(self, tenant_id: int, task_id: str, data: Dict[str, str]) -> None:
        """Ajoute une tâche"""
        import time
        key = self.get_task_key(tenant_id, task_id)
        self.client.hset(key, mapping=data)
        self.client.zadd(
            self.get_tasks_pending_key(tenant_id),
            {task_id: time.time()}
        )

    def get_task(self, tenant_id: int, task_id: str) -> Optional[Dict[str, str]]:
        """Récupère une tâche"""
        key = self.get_task_key(tenant_id, task_id)
        data = self.client.hgetall(key)
        return data if data else None

    def complete_task(self, tenant_id: int, task_id: str, result: str = "") -> None:
        """Marque une tâche comme terminée"""
        import time
        # Met à jour le statut
        key = self.get_task_key(tenant_id, task_id)
        self.client.hset(key, mapping={
            "status": "completed",
            "completed_at": str(time.time()),
            "result": result,
        })
        # Déplace de pending à completed
        self.client.zrem(self.get_tasks_pending_key(tenant_id), task_id)
        self.client.zadd(
            self.get_tasks_completed_key(tenant_id),
            {task_id: time.time()}
        )
        # TTL sur la tâche complétée
        self.client.expire(key, TTL_COMPLETED_TASKS)

    def get_pending_tasks(self, tenant_id: int) -> List[str]:
        """Récupère les IDs des tâches en attente"""
        return self.client.zrange(self.get_tasks_pending_key(tenant_id), 0, -1)

    # ========================================================================
    # TRUSTED CONTACTS
    # ========================================================================

    def get_trusted_contacts_key(self, tenant_id: int) -> str:
        """Clé pour la liste des contacts de confiance"""
        return self._key(tenant_id, "trusted_contacts")

    def get_contact_profile_key(self, tenant_id: int, phone: str) -> str:
        """Clé pour le profil d'un contact"""
        return self._key(tenant_id, "contact", phone, "profile")

    def add_trusted_contact(self, tenant_id: int, phone: str, data: Dict[str, str]) -> bool:
        """
        Ajoute un contact de confiance.
        Retourne False si le maximum (5) est atteint.
        """
        key = self.get_trusted_contacts_key(tenant_id)
        if self.client.scard(key) >= 5:
            return False
        self.client.sadd(key, phone)
        self.client.hset(self.get_contact_profile_key(tenant_id, phone), mapping=data)
        return True

    def get_trusted_contacts(self, tenant_id: int) -> List[str]:
        """Récupère les numéros des contacts de confiance"""
        return list(self.client.smembers(self.get_trusted_contacts_key(tenant_id)))

    def get_contact_profile(self, tenant_id: int, phone: str) -> Optional[Dict[str, str]]:
        """Récupère le profil d'un contact"""
        key = self.get_contact_profile_key(tenant_id, phone)
        data = self.client.hgetall(key)
        return data if data else None

    def remove_trusted_contact(self, tenant_id: int, phone: str) -> None:
        """Supprime un contact de confiance"""
        self.client.srem(self.get_trusted_contacts_key(tenant_id), phone)
        self.client.delete(self.get_contact_profile_key(tenant_id, phone))

    # ========================================================================
    # NOTES
    # ========================================================================

    def get_notes_key(self, tenant_id: int) -> str:
        """Clé pour la liste des notes"""
        return self._key(tenant_id, "notes")

    def get_note_key(self, tenant_id: int, note_id: str) -> str:
        """Clé pour une note"""
        return self._key(tenant_id, "note", note_id)

    def add_note(self, tenant_id: int, note_id: str, data: Dict[str, str]) -> None:
        """Ajoute une note"""
        import time
        key = self.get_note_key(tenant_id, note_id)
        self.client.hset(key, mapping=data)
        self.client.expire(key, TTL_NOTES)
        self.client.zadd(self.get_notes_key(tenant_id), {note_id: time.time()})

    def get_note(self, tenant_id: int, note_id: str) -> Optional[Dict[str, str]]:
        """Récupère une note"""
        key = self.get_note_key(tenant_id, note_id)
        data = self.client.hgetall(key)
        return data if data else None

    def get_notes(self, tenant_id: int, limit: int = 50) -> List[str]:
        """Récupère les IDs des notes récentes"""
        return self.client.zrevrange(self.get_notes_key(tenant_id), 0, limit - 1)

    # ========================================================================
    # QUOTA & USAGE
    # ========================================================================

    def get_quota_key(self, tenant_id: int) -> str:
        """Clé pour les quotas mémoire"""
        return self._key(tenant_id, "quota", "memory")

    def get_usage_key(self, tenant_id: int, date: str) -> str:
        """Clé pour l'usage quotidien (date format: YYYY-MM-DD)"""
        return self._key(tenant_id, "usage", date)

    def get_memory_usage(self, tenant_id: int) -> int:
        """Calcule l'usage mémoire approximatif d'un tenant (en bytes)"""
        pattern = self._key(tenant_id, "*")
        total = 0
        for key in self.client.scan_iter(match=pattern):
            try:
                total += self.client.memory_usage(key) or 0
            except redis.RedisError:
                pass
        return total

    def increment_daily_usage(self, tenant_id: int, field: str, amount: int = 1) -> int:
        """Incrémente un compteur d'usage quotidien"""
        from datetime import date
        key = self.get_usage_key(tenant_id, date.today().isoformat())
        result = self.client.hincrby(key, field, amount)
        self.client.expire(key, TTL_DAILY_USAGE)
        return result

    def get_daily_usage(self, tenant_id: int, date_str: Optional[str] = None) -> Dict[str, int]:
        """Récupère l'usage d'un jour"""
        from datetime import date
        if date_str is None:
            date_str = date.today().isoformat()
        key = self.get_usage_key(tenant_id, date_str)
        data = self.client.hgetall(key)
        return {k: int(v) for k, v in data.items()}

    # ========================================================================
    # SESSION
    # ========================================================================

    def get_session_key(self, tenant_id: int) -> str:
        """Clé pour la session courante"""
        return self._key(tenant_id, "session", "current")

    def set_session(self, tenant_id: int, data: Dict[str, str]) -> None:
        """Définit la session courante"""
        key = self.get_session_key(tenant_id)
        self.client.hset(key, mapping=data)
        self.client.expire(key, TTL_SESSIONS)

    def get_session(self, tenant_id: int) -> Optional[Dict[str, str]]:
        """Récupère la session courante"""
        key = self.get_session_key(tenant_id)
        data = self.client.hgetall(key)
        return data if data else None

    def clear_session(self, tenant_id: int) -> None:
        """Efface la session courante"""
        self.client.delete(self.get_session_key(tenant_id))


    # ========================================================================
    # SUBSCRIBER PROFILE
    # ========================================================================

    def get_profile_key(self, tenant_id: int) -> str:
        """Cle pour le profil souscripteur"""
        return self._key(tenant_id, "profile")

    def set_profile(self, tenant_id: int, data: Dict[str, str]) -> None:
        """Enregistre le profil souscripteur"""
        key = self.get_profile_key(tenant_id)
        self.client.hset(key, mapping=data)

    def get_profile(self, tenant_id: int) -> Optional[Dict[str, str]]:
        """Recupere le profil souscripteur"""
        key = self.get_profile_key(tenant_id)
        data = self.client.hgetall(key)
        return data if data else None

    def update_profile(self, tenant_id: int, fields: Dict[str, str]) -> None:
        """Met a jour des champs specifiques du profil"""
        key = self.get_profile_key(tenant_id)
        self.client.hset(key, mapping=fields)


    # ========================================================================
    # PERCEPTION (aide contextuelle visuelle)
    # ========================================================================

    TTL_PERCEPTION_STATE = 60 * 60  # 1h (stale si camera off)
    TTL_PERCEPTION_HISTORY = 24 * 60 * 60  # 24h
    TTL_PERCEPTION_EVENTS = 7 * 24 * 60 * 60  # 7 jours

    def set_perception_state(self, tenant_id: int, data: Dict[str, str]) -> None:
        key = self._key(tenant_id, "perception", "state")
        self.client.hset(key, mapping=data)
        self.client.expire(key, self.TTL_PERCEPTION_STATE)

    def get_perception_state(self, tenant_id: int) -> Optional[Dict[str, str]]:
        key = self._key(tenant_id, "perception", "state")
        data = self.client.hgetall(key)
        return data if data else None

    def set_perception_enabled(self, tenant_id: int, enabled: bool) -> None:
        key = self._key(tenant_id, "perception", "enabled")
        self.client.set(key, "1" if enabled else "0")

    def is_perception_enabled(self, tenant_id: int) -> bool:
        key = self._key(tenant_id, "perception", "enabled")
        return self.client.get(key) == "1"

    def add_perception_history(self, tenant_id: int, state_json: str) -> None:
        key = self._key(tenant_id, "perception", "history")
        self.client.lpush(key, state_json)
        self.client.ltrim(key, 0, 99)
        self.client.expire(key, self.TTL_PERCEPTION_HISTORY)

    def add_perception_event(self, tenant_id: int, event_json: str) -> None:
        import time as _time
        key = self._key(tenant_id, "perception", "events")
        self.client.zadd(key, {event_json: _time.time()})
        self.client.expire(key, self.TTL_PERCEPTION_EVENTS)

    # =========================================================================
    # BEHAVIORAL MEMORY (locked identity + rules)
    # =========================================================================

    # =========================================================================
    # EVENT LOG (journal chronologique humain)
    # =========================================================================

    TTL_EVENT_LOG = 90 * 24 * 60 * 60  # 90 jours
    EVENT_LOG_MAX = 500  # Max entries

    def add_event_log(self, tenant_id: int, event_json: str) -> None:
        """Add an event to the chronological event log."""
        key = self._key(tenant_id, "event_log")
        self.client.lpush(key, event_json)
        self.client.ltrim(key, 0, self.EVENT_LOG_MAX - 1)
        self.client.expire(key, self.TTL_EVENT_LOG)

    def get_event_log(self, tenant_id: int, limit: int = 50, offset: int = 0) -> list:
        """Retrieve events from the chronological log."""
        key = self._key(tenant_id, "event_log")
        return list(self.client.lrange(key, offset, offset + limit - 1))

    # =========================================================================
    # BEHAVIORAL MEMORY (locked identity + rules)
    # =========================================================================

    def set_behavioral_memory(self, tenant_id: int, key_name: str, value: str) -> None:
        """Store a behavioral memory value (identity_core or behavior_rules)."""
        key = self._key(tenant_id, "behavioral", key_name)
        self.client.set(key, value)

    def get_behavioral_memory(self, tenant_id: int, key_name: str) -> Optional[str]:
        """Retrieve a behavioral memory value."""
        key = self._key(tenant_id, "behavioral", key_name)
        val = self.client.get(key)
        if val is None:
            return None
        return val if isinstance(val, str) else val.decode("utf-8")


    # =========================================================================
    # FAMILY PACK
    # =========================================================================

    TTL_FAMILY = 365 * 24 * 60 * 60  # 1 an
    TTL_FAMILY_MESSAGES = 90 * 24 * 60 * 60  # 90 jours
    TTL_FAMILY_AUDIT = 365 * 24 * 60 * 60  # 1 an
    TTL_OTP = 10 * 60  # 10 minutes

    # --- Family Group ---

    def get_family_group_key(self, tenant_id: int) -> str:
        """Cle pour le groupe familial"""
        return self._key(tenant_id, "family", "group")

    def set_family_group(self, tenant_id: int, data: Dict[str, str]) -> None:
        """Cree ou met a jour le groupe familial"""
        key = self.get_family_group_key(tenant_id)
        self.client.hset(key, mapping=data)
        self.client.expire(key, self.TTL_FAMILY)

    def get_family_group(self, tenant_id: int) -> Optional[Dict[str, str]]:
        """Recupere le groupe familial"""
        key = self.get_family_group_key(tenant_id)
        data = self.client.hgetall(key)
        return data if data else None

    def delete_family_group(self, tenant_id: int) -> None:
        """Supprime le groupe familial"""
        self.client.delete(self.get_family_group_key(tenant_id))

    # --- Family Members ---

    def get_family_members_key(self, tenant_id: int) -> str:
        """Cle pour la liste des membres famille"""
        return self._key(tenant_id, "family", "members")

    def get_family_member_key(self, tenant_id: int, phone: str) -> str:
        """Cle pour un membre famille"""
        return self._key(tenant_id, "family", "member", phone)

    def add_family_member(self, tenant_id: int, phone: str, data: Dict[str, str]) -> bool:
        """Ajoute un membre famille. Retourne False si quota atteint."""
        members_key = self.get_family_members_key(tenant_id)
        # Verifier quota (max 15 pour premium)
        if self.client.scard(members_key) >= 15:
            return False
        self.client.sadd(members_key, phone)
        member_key = self.get_family_member_key(tenant_id, phone)
        self.client.hset(member_key, mapping=data)
        self.client.expire(member_key, self.TTL_FAMILY)
        return True

    def get_family_members(self, tenant_id: int) -> List[str]:
        """Recupere les phones des membres famille"""
        return list(self.client.smembers(self.get_family_members_key(tenant_id)))

    def get_family_member(self, tenant_id: int, phone: str) -> Optional[Dict[str, str]]:
        """Recupere un membre famille"""
        key = self.get_family_member_key(tenant_id, phone)
        data = self.client.hgetall(key)
        return data if data else None

    def update_family_member(self, tenant_id: int, phone: str, fields: Dict[str, str]) -> None:
        """Met a jour des champs d'un membre"""
        key = self.get_family_member_key(tenant_id, phone)
        self.client.hset(key, mapping=fields)

    def remove_family_member(self, tenant_id: int, phone: str) -> None:
        """Supprime un membre famille"""
        self.client.srem(self.get_family_members_key(tenant_id), phone)
        self.client.delete(self.get_family_member_key(tenant_id, phone))

    def get_family_members_by_role(self, tenant_id: int, role: str) -> List[str]:
        """Recupere les phones des membres avec un role specifique"""
        members = []
        for phone in self.get_family_members(tenant_id):
            data = self.get_family_member(tenant_id, phone)
            if data and data.get("role") == role:
                members.append(phone)
        return members

    # --- OTP Verification ---

    def set_otp(self, phone: str, otp: str) -> None:
        """Stocke un OTP temporaire pour verification"""
        key = self._key("otp", phone)
        self.client.setex(key, self.TTL_OTP, otp)

    def verify_otp(self, phone: str, otp: str) -> bool:
        """Verifie un OTP et le supprime si valide"""
        key = self._key("otp", phone)
        stored = self.client.get(key)
        if stored == otp:
            self.client.delete(key)
            return True
        return False

    # --- Escalation Rules ---

    def get_escalation_rules_key(self, tenant_id: int) -> str:
        """Cle pour la liste des regles d'escalade"""
        return self._key(tenant_id, "family", "escalation_rules")

    def get_escalation_rule_key(self, tenant_id: int, rule_id: str) -> str:
        """Cle pour une regle d'escalade"""
        return self._key(tenant_id, "family", "escalation", rule_id)

    def add_escalation_rule(self, tenant_id: int, rule_id: str, data: Dict[str, str]) -> None:
        """Ajoute une regle d'escalade"""
        self.client.sadd(self.get_escalation_rules_key(tenant_id), rule_id)
        key = self.get_escalation_rule_key(tenant_id, rule_id)
        self.client.hset(key, mapping=data)
        self.client.expire(key, self.TTL_FAMILY)

    def get_escalation_rules(self, tenant_id: int) -> List[str]:
        """Recupere les IDs des regles d'escalade"""
        return list(self.client.smembers(self.get_escalation_rules_key(tenant_id)))

    def get_escalation_rule(self, tenant_id: int, rule_id: str) -> Optional[Dict[str, str]]:
        """Recupere une regle d'escalade"""
        key = self.get_escalation_rule_key(tenant_id, rule_id)
        data = self.client.hgetall(key)
        return data if data else None

    def delete_escalation_rule(self, tenant_id: int, rule_id: str) -> None:
        """Supprime une regle d'escalade"""
        self.client.srem(self.get_escalation_rules_key(tenant_id), rule_id)
        self.client.delete(self.get_escalation_rule_key(tenant_id, rule_id))

    # --- Family Messages ---

    def get_family_messages_key(self, tenant_id: int) -> str:
        """Cle pour la liste des messages famille"""
        return self._key(tenant_id, "family", "messages")

    def get_family_message_key(self, tenant_id: int, msg_id: str) -> str:
        """Cle pour un message famille"""
        return self._key(tenant_id, "family", "message", msg_id)

    def add_family_message(self, tenant_id: int, msg_id: str, data: Dict[str, str]) -> None:
        """Ajoute un message famille"""
        import time
        self.client.zadd(self.get_family_messages_key(tenant_id), {msg_id: time.time()})
        key = self.get_family_message_key(tenant_id, msg_id)
        self.client.hset(key, mapping=data)
        self.client.expire(key, self.TTL_FAMILY_MESSAGES)

    def get_family_messages(self, tenant_id: int, limit: int = 50) -> List[str]:
        """Recupere les IDs des messages recents"""
        return self.client.zrevrange(self.get_family_messages_key(tenant_id), 0, limit - 1)

    def get_family_message(self, tenant_id: int, msg_id: str) -> Optional[Dict[str, str]]:
        """Recupere un message famille"""
        key = self.get_family_message_key(tenant_id, msg_id)
        data = self.client.hgetall(key)
        return data if data else None

    def update_family_message(self, tenant_id: int, msg_id: str, fields: Dict[str, str]) -> None:
        """Met a jour un message famille"""
        key = self.get_family_message_key(tenant_id, msg_id)
        self.client.hset(key, mapping=fields)

    def get_unread_messages_for_member(self, tenant_id: int, phone: str) -> List[str]:
        """Recupere les messages non lus pour un membre"""
        import json
        unread = []
        for msg_id in self.get_family_messages(tenant_id, limit=100):
            data = self.get_family_message(tenant_id, msg_id)
            if data:
                read_by = json.loads(data.get("read_by", "[]"))
                # Message groupe ou destine a ce membre
                if not data.get("to_phone") or data.get("to_phone") == phone:
                    if phone not in read_by:
                        unread.append(msg_id)
        return unread

    # --- Family Audit Log ---

    def get_family_audit_key(self, tenant_id: int) -> str:
        """Cle pour le journal d'audit famille"""
        return self._key(tenant_id, "family", "audit")

    def add_family_audit(self, tenant_id: int, audit_json: str) -> None:
        """Ajoute une entree au journal d'audit"""
        key = self.get_family_audit_key(tenant_id)
        self.client.lpush(key, audit_json)
        self.client.ltrim(key, 0, 999)  # Max 1000 entries
        self.client.expire(key, self.TTL_FAMILY_AUDIT)

    def get_family_audit(self, tenant_id: int, limit: int = 50) -> List[str]:
        """Recupere les entrees d'audit recentes"""
        key = self.get_family_audit_key(tenant_id)
        return list(self.client.lrange(key, 0, limit - 1))

    # --- Active Escalations (in progress) ---

    def get_active_escalation_key(self, tenant_id: int, event_id: str) -> str:
        """Cle pour une escalade en cours"""
        return self._key(tenant_id, "family", "active_escalation", event_id)

    def set_active_escalation(self, tenant_id: int, event_id: str, data: Dict[str, str]) -> None:
        """Enregistre une escalade en cours"""
        key = self.get_active_escalation_key(tenant_id, event_id)
        self.client.hset(key, mapping=data)
        self.client.expire(key, 24 * 60 * 60)  # 24h max

    def get_active_escalation(self, tenant_id: int, event_id: str) -> Optional[Dict[str, str]]:
        """Recupere une escalade en cours"""
        key = self.get_active_escalation_key(tenant_id, event_id)
        data = self.client.hgetall(key)
        return data if data else None

    def delete_active_escalation(self, tenant_id: int, event_id: str) -> None:
        """Supprime une escalade (resolue)"""
        self.client.delete(self.get_active_escalation_key(tenant_id, event_id))


@lru_cache()
def get_redis_client() -> RedisClient:
    """Factory pour obtenir le client Redis singleton"""
    return RedisClient()
