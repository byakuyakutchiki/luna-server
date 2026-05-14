"""
Luna Redis Client - Client Redis avec gestion des clés Luna
"""
import os
import json
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
        """Lazy initialization du client Redis avec connection pool dimensionne."""
        if self._client is None:
            pool = redis.ConnectionPool.from_url(
                self._url,
                decode_responses=True,
                max_connections=100,          # Scale: 1000+ users simultanes
                socket_timeout=10,            # Tolerant sous charge
                socket_connect_timeout=5,
                socket_keepalive=True,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            self._client = redis.Redis(connection_pool=pool)
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

    def get_all_tenant_ids(self) -> List[int]:
        """Scan Redis pour trouver tous les tenant IDs existants."""
        tenant_ids = set()
        pattern = f"{self.prefix}:*:profile"
        try:
            for key in self.client.scan_iter(match=pattern, count=100):
                parts = key.split(":")
                if len(parts) >= 3:
                    try:
                        tenant_ids.add(int(parts[1]))
                    except (ValueError, IndexError):
                        pass
        except redis.RedisError as e:
            logger.error(f"Redis scan error: {e}")
        return sorted(tenant_ids)

    def purge_tenant(self, tenant_id: int) -> int:
        """Supprime TOUTES les cles Redis d'un tenant. Retourne le nombre de cles supprimees."""
        pattern = f"{self.prefix}:{tenant_id}:*"
        count = 0
        try:
            for key in self.client.scan_iter(match=pattern, count=200):
                self.client.delete(key)
                count += 1
            # Supprimer aussi l'index tenant
            self.client.zrem(f"{self.prefix}:auth:tenant_index", tenant_id)
        except redis.RedisError as e:
            logger.error(f"Purge tenant {tenant_id} error: {e}")
        return count

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

    def add_trusted_contact(self, tenant_id: int, phone: str, data: Dict[str, str], max_contacts: int = 5) -> bool:
        """
        Ajoute un contact de confiance.
        Retourne False si le maximum est atteint.
        """
        key = self.get_trusted_contacts_key(tenant_id)
        if self.client.scard(key) >= max_contacts:
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

    def remove_trusted_contact(self, tenant_id: int, phone: str) -> bool:
        """Supprime un contact de confiance. Retourne True si supprime, False si inexistant."""
        removed = self.client.srem(self.get_trusted_contacts_key(tenant_id), phone)
        self.client.delete(self.get_contact_profile_key(tenant_id, phone))
        return bool(removed)

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

    def delete_note(self, tenant_id: int, note_id: str) -> bool:
        """Supprime une note. Retourne True si supprimée."""
        key = self.get_note_key(tenant_id, note_id)
        deleted = self.client.delete(key)
        self.client.zrem(self.get_notes_key(tenant_id), note_id)
        return bool(deleted)

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
    # SESSION (defini dans la section Unified Memory ci-dessous)
    # ========================================================================


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

    def get_all_family_members(self, tenant_id: int) -> List[Dict[str, str]]:
        """Recupere tous les membres famille avec leurs donnees completes"""
        phones = self.get_family_members(tenant_id)
        members = []
        for phone in phones:
            data = self.get_family_member(tenant_id, phone)
            if data:
                members.append(data)
        return members

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


    # =========================================================================
    # UNIFIED MEMORY - Session temps reel multi-canal
    # =========================================================================

    TTL_SESSION = 24 * 60 * 60  # 24 heures
    TTL_UNIFIED_MESSAGES = 30 * 24 * 60 * 60  # 30 jours
    TTL_CONTEXT = 60 * 60  # 1 heure (contexte temps reel)
    MAX_UNIFIED_MESSAGES = 1000  # Max messages par tenant

    # --- Session Active ---

    def get_session_key(self, tenant_id: int) -> str:
        """Cle pour la session active"""
        return self._key(tenant_id, "session", "active")

    def set_session(self, tenant_id: int, data: Dict[str, str]) -> None:
        """Cree ou met a jour la session active"""
        key = self.get_session_key(tenant_id)
        self.client.hset(key, mapping=data)
        self.client.expire(key, self.TTL_SESSION)

    def get_session(self, tenant_id: int) -> Optional[Dict[str, str]]:
        """Recupere la session active"""
        key = self.get_session_key(tenant_id)
        data = self.client.hgetall(key)
        return data if data else None

    def update_session(self, tenant_id: int, updates: Dict[str, str]) -> None:
        """Met a jour des champs de la session"""
        key = self.get_session_key(tenant_id)
        if self.client.exists(key):
            self.client.hset(key, mapping=updates)

    def delete_session(self, tenant_id: int) -> None:
        """Supprime la session active"""
        self.client.delete(self.get_session_key(tenant_id))

    # --- Contexte Temps Reel ---

    def get_context_key(self, tenant_id: int) -> str:
        """Cle pour le contexte temps reel"""
        return self._key(tenant_id, "context", "realtime")

    def set_context(self, tenant_id: int, data: Dict[str, str]) -> None:
        """Definit le contexte temps reel"""
        key = self.get_context_key(tenant_id)
        self.client.hset(key, mapping=data)
        self.client.expire(key, self.TTL_CONTEXT)

    def get_context(self, tenant_id: int) -> Optional[Dict[str, str]]:
        """Recupere le contexte temps reel"""
        key = self.get_context_key(tenant_id)
        data = self.client.hgetall(key)
        return data if data else None

    def update_context(self, tenant_id: int, updates: Dict[str, str]) -> None:
        """Met a jour le contexte"""
        key = self.get_context_key(tenant_id)
        self.client.hset(key, mapping=updates)
        self.client.expire(key, self.TTL_CONTEXT)

    # --- Messages Unifies (tous canaux) ---

    def get_unified_messages_key(self, tenant_id: int) -> str:
        """Cle pour la liste des messages unifies"""
        return self._key(tenant_id, "unified", "messages")

    def add_unified_message(self, tenant_id: int, msg_id: str, data: Dict[str, str]) -> None:
        """Ajoute un message unifie"""
        list_key = self.get_unified_messages_key(tenant_id)
        msg_key = self._key(tenant_id, "unified", "message", msg_id)

        # Stocker le message
        self.client.hset(msg_key, mapping=data)
        self.client.expire(msg_key, self.TTL_UNIFIED_MESSAGES)

        # Ajouter a la liste (score = timestamp)
        import time
        self.client.zadd(list_key, {msg_id: time.time()})

        # Limiter la taille
        count = self.client.zcard(list_key)
        if count > self.MAX_UNIFIED_MESSAGES:
            # Supprimer les plus anciens
            to_remove = self.client.zrange(list_key, 0, count - self.MAX_UNIFIED_MESSAGES - 1)
            for old_id in to_remove:
                self.client.delete(self._key(tenant_id, "unified", "message", old_id))
            self.client.zremrangebyrank(list_key, 0, count - self.MAX_UNIFIED_MESSAGES - 1)

    def get_unified_message(self, tenant_id: int, msg_id: str) -> Optional[Dict[str, str]]:
        """Recupere un message unifie"""
        key = self._key(tenant_id, "unified", "message", msg_id)
        data = self.client.hgetall(key)
        return data if data else None

    def get_unified_messages(self, tenant_id: int, limit: int = 50,
                             channel: Optional[str] = None) -> List[Dict[str, str]]:
        """Recupere les derniers messages unifies"""
        list_key = self.get_unified_messages_key(tenant_id)
        msg_ids = self.client.zrevrange(list_key, 0, limit * 2 - 1)  # Prendre plus pour filtrer

        messages = []
        for msg_id in msg_ids:
            msg = self.get_unified_message(tenant_id, msg_id)
            if msg:
                if channel is None or msg.get("channel") == channel:
                    messages.append(msg)
                    if len(messages) >= limit:
                        break
        return messages

    def get_recent_context_messages(self, tenant_id: int, count: int = 10) -> List[Dict[str, str]]:
        """Recupere les N derniers messages pour le contexte OpenAI"""
        return self.get_unified_messages(tenant_id, limit=count)

    # --- Handoff de canal ---

    def get_handoffs_key(self, tenant_id: int) -> str:
        """Cle pour l'historique des handoffs"""
        return self._key(tenant_id, "unified", "handoffs")

    def add_handoff(self, tenant_id: int, handoff_id: str, data: Dict[str, str]) -> None:
        """Enregistre un changement de canal"""
        list_key = self.get_handoffs_key(tenant_id)
        handoff_key = self._key(tenant_id, "unified", "handoff", handoff_id)

        self.client.hset(handoff_key, mapping=data)
        self.client.expire(handoff_key, self.TTL_UNIFIED_MESSAGES)

        import time
        self.client.zadd(list_key, {handoff_id: time.time()})
        # Garder max 100 handoffs
        self.client.zremrangebyrank(list_key, 0, -101)

    def get_last_handoff(self, tenant_id: int) -> Optional[Dict[str, str]]:
        """Recupere le dernier handoff"""
        list_key = self.get_handoffs_key(tenant_id)
        handoff_ids = self.client.zrevrange(list_key, 0, 0)
        if handoff_ids:
            return self.client.hgetall(self._key(tenant_id, "unified", "handoff", handoff_ids[0]))
        return None

    # --- Pub/Sub pour temps reel ---

    def publish_event(self, tenant_id: int, event_type: str, data: Dict[str, Any]) -> None:
        """Publie un evenement temps reel"""
        import json
        channel = f"{self.prefix}:events:{tenant_id}"
        payload = json.dumps({"type": event_type, "data": data})
        self.client.publish(channel, payload)

    def get_events_channel(self, tenant_id: int) -> str:
        """Retourne le nom du channel pour subscribe"""
        return f"{self.prefix}:events:{tenant_id}"

    # --- Voice Session (pour WebSocket) ---

    def get_voice_session_key(self, tenant_id: int) -> str:
        """Cle pour la session voix active"""
        return self._key(tenant_id, "voice", "session")

    def set_voice_session(self, tenant_id: int, data: Dict[str, str]) -> None:
        """Cree une session voix"""
        key = self.get_voice_session_key(tenant_id)
        self.client.hset(key, mapping=data)
        self.client.expire(key, 60 * 60)  # 1 heure max

    def get_voice_session(self, tenant_id: int) -> Optional[Dict[str, str]]:
        """Recupere la session voix"""
        key = self.get_voice_session_key(tenant_id)
        data = self.client.hgetall(key)
        return data if data else None

    def delete_voice_session(self, tenant_id: int) -> None:
        """Termine la session voix"""
        self.client.delete(self.get_voice_session_key(tenant_id))


    # =========================================================================
    # THEMES & PERSONNALISATION
    # =========================================================================

    TTL_THEME = 365 * 24 * 60 * 60  # 1 an

    def get_user_theme_key(self, tenant_id: int, user_phone: str) -> str:
        """Cle pour les preferences de theme d'un utilisateur"""
        return self._key(tenant_id, "theme", "user", user_phone)

    def set_user_theme(self, tenant_id: int, user_phone: str, data: Dict[str, str]) -> None:
        """Definit les preferences de theme d'un utilisateur"""
        key = self.get_user_theme_key(tenant_id, user_phone)
        self.client.hset(key, mapping=data)
        self.client.expire(key, self.TTL_THEME)

    def get_user_theme(self, tenant_id: int, user_phone: str) -> Optional[Dict[str, str]]:
        """Recupere les preferences de theme d'un utilisateur"""
        key = self.get_user_theme_key(tenant_id, user_phone)
        data = self.client.hgetall(key)
        return data if data else None

    def delete_user_theme(self, tenant_id: int, user_phone: str) -> None:
        """Supprime les preferences de theme"""
        self.client.delete(self.get_user_theme_key(tenant_id, user_phone))

    def get_all_user_themes(self, tenant_id: int) -> List[Dict[str, str]]:
        """Recupere tous les themes utilisateurs du tenant"""
        pattern = self._key(tenant_id, "theme", "user", "*")
        themes = []
        for key in self.client.scan_iter(match=pattern):
            data = self.client.hgetall(key)
            if data:
                themes.append(data)
        return themes


    # =========================================================================
    # ASSISTANT PRO - Taches & Documents iteratifs
    # =========================================================================

    TTL_ASSISTANT_TASK = 30 * 24 * 60 * 60  # 30 jours
    TTL_EMAIL_DRAFT = 7 * 24 * 60 * 60  # 7 jours

    def get_assistant_task_key(self, tenant_id: int, task_id: str) -> str:
        """Cle pour une tache assistant"""
        return self._key(tenant_id, "assistant", "task", task_id)

    def get_assistant_tasks_key(self, tenant_id: int) -> str:
        """Cle pour la liste des taches"""
        return self._key(tenant_id, "assistant", "tasks")

    def add_assistant_task(self, tenant_id: int, task_id: str, data: Dict[str, str]) -> None:
        """Ajoute une tache assistant"""
        task_key = self.get_assistant_task_key(tenant_id, task_id)
        list_key = self.get_assistant_tasks_key(tenant_id)

        self.client.hset(task_key, mapping=data)
        self.client.expire(task_key, self.TTL_ASSISTANT_TASK)

        import time
        self.client.zadd(list_key, {task_id: time.time()})

    def get_assistant_task(self, tenant_id: int, task_id: str) -> Optional[Dict[str, str]]:
        """Recupere une tache"""
        key = self.get_assistant_task_key(tenant_id, task_id)
        data = self.client.hgetall(key)
        return data if data else None

    def update_assistant_task(self, tenant_id: int, task_id: str, updates: Dict[str, str]) -> None:
        """Met a jour une tache"""
        key = self.get_assistant_task_key(tenant_id, task_id)
        if self.client.exists(key):
            self.client.hset(key, mapping=updates)

    def get_assistant_tasks(self, tenant_id: int, limit: int = 50) -> List[Dict[str, str]]:
        """Recupere les dernieres taches"""
        list_key = self.get_assistant_tasks_key(tenant_id)
        task_ids = self.client.zrevrange(list_key, 0, limit - 1)

        tasks = []
        for task_id in task_ids:
            task = self.get_assistant_task(tenant_id, task_id)
            if task:
                tasks.append(task)
        return tasks

    def get_task_versions(self, tenant_id: int, original_task_id: str) -> List[Dict[str, str]]:
        """Recupere toutes les versions d'une tache (parent + enfants)"""
        all_tasks = self.get_assistant_tasks(tenant_id, limit=100)
        versions = []
        for task in all_tasks:
            if task.get("id") == original_task_id or task.get("parent_task_id") == original_task_id:
                versions.append(task)
        # Trier par version
        versions.sort(key=lambda t: int(t.get("version", 1)))
        return versions

    # --- Email Drafts ---

    def get_email_draft_key(self, tenant_id: int, draft_id: str) -> str:
        """Cle pour un brouillon email"""
        return self._key(tenant_id, "email", "draft", draft_id)

    def save_email_draft(self, tenant_id: int, draft_id: str, data: Dict[str, str]) -> None:
        """Sauvegarde un brouillon email"""
        key = self.get_email_draft_key(tenant_id, draft_id)
        self.client.hset(key, mapping=data)
        self.client.expire(key, self.TTL_EMAIL_DRAFT)

    def get_email_draft(self, tenant_id: int, draft_id: str) -> Optional[Dict[str, str]]:
        """Recupere un brouillon email"""
        key = self.get_email_draft_key(tenant_id, draft_id)
        data = self.client.hgetall(key)
        return data if data else None

    def delete_email_draft(self, tenant_id: int, draft_id: str) -> None:
        """Supprime un brouillon"""
        self.client.delete(self.get_email_draft_key(tenant_id, draft_id))

    # =========================================================================
    # EMAIL INTEGRATION (Gmail OAuth2 per-tenant)
    # =========================================================================

    def save_email_integration(self, tenant_id: int, data: Dict[str, str]) -> None:
        """Sauvegarde ou met a jour l'integration email d'un tenant (merge)."""
        key = self._key(str(tenant_id), "email_integration")
        self.client.hset(key, mapping=data)

    def get_email_integration(self, tenant_id: int) -> Optional[Dict[str, str]]:
        """Recupere l'integration email d'un tenant."""
        key = self._key(str(tenant_id), "email_integration")
        data = self.client.hgetall(key)
        return data if data else None

    def delete_email_integration(self, tenant_id: int) -> None:
        """Supprime l'integration email d'un tenant (deconnexion)."""
        key = self._key(str(tenant_id), "email_integration")
        self.client.delete(key)

    # =========================================================================
    # AUTH STORE (multi-tenant client authentication)
    # =========================================================================

    def get_next_tenant_id(self) -> int:
        """Attribue le prochain tenant_id (auto-increment, demarre a 2)."""
        key = self._key("auth", "next_tenant_id")
        # Si la cle n'existe pas, l'initialiser a 1 pour que INCR retourne 2
        if not self.client.exists(key):
            self.client.set(key, 1)
        return self.client.incr(key)

    def create_auth_record(self, email: str, password_hash: str,
                           tenant_id: int, plan: str = "essentiel") -> bool:
        """Cree un enregistrement auth. Retourne False si email deja pris."""
        import time as _time
        key = self._key("auth", email.lower())
        record = json.dumps({
            "tenant_id": tenant_id,
            "password_hash": password_hash,
            "plan": plan,
            "active": True,
            "created_at": _time.time(),
            "email": email.lower(),
        })
        # SETNX = atomique, anti-doublon
        created = self.client.setnx(key, record)
        if created:
            self.add_to_tenant_index(tenant_id, _time.time())
        return bool(created)

    def get_auth_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Recupere l'enregistrement auth par email."""
        key = self._key("auth", email.lower())
        data = self.client.get(key)
        if data:
            return json.loads(data)
        return None

    def update_auth_record(self, email: str, updates: Dict[str, Any]) -> bool:
        """Met a jour des champs dans l'enregistrement auth."""
        key = self._key("auth", email.lower())
        data = self.client.get(key)
        if not data:
            return False
        record = json.loads(data)
        record.update(updates)
        self.client.set(key, json.dumps(record))
        return True

    def get_auth_by_tenant_id(self, tenant_id: int) -> Optional[Dict[str, Any]]:
        """Retrouve un enregistrement auth par tenant_id (scan)."""
        pattern = self._key("auth", "*")
        skip = {self._key("auth", "next_tenant_id"), self._key("auth", "tenant_index")}
        for key in self.client.scan_iter(match=pattern, count=100):
            if key in skip:
                continue
            data = self.client.get(key)
            if data:
                record = json.loads(data)
                if record.get("tenant_id") == tenant_id:
                    return record
        return None

    def add_to_tenant_index(self, tenant_id: int, timestamp: float) -> None:
        """Ajoute un tenant au sorted set index."""
        key = self._key("auth", "tenant_index")
        self.client.zadd(key, {str(tenant_id): timestamp})

    def get_all_auth_records(self) -> List[Dict[str, Any]]:
        """Recupere tous les enregistrements auth."""
        pattern = self._key("auth", "*")
        skip = {self._key("auth", "next_tenant_id"), self._key("auth", "tenant_index")}
        records = []
        for key in self.client.scan_iter(match=pattern, count=100):
            if key in skip:
                continue
            data = self.client.get(key)
            if data:
                try:
                    records.append(json.loads(data))
                except json.JSONDecodeError:
                    pass
        records.sort(key=lambda r: r.get("tenant_id", 0))
        return records


@lru_cache()
def get_redis_client() -> RedisClient:
    """Factory pour obtenir le client Redis singleton"""
    return RedisClient()
