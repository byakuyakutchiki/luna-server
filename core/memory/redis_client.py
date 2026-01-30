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


@lru_cache()
def get_redis_client() -> RedisClient:
    """Factory pour obtenir le client Redis singleton"""
    return RedisClient()
