"""
Luna Memory Manager - API haut niveau pour la gestion mémoire
"""
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from .redis_client import RedisClient, get_redis_client
from .schemas import (
    Conversation, Message, Instruction, TaskState, Note, TrustedContact,
    MemoryQuota, PlanType, MessageRole, Channel, ConversationStatus,
    InstructionType, ActionType, TaskStatus,
)

logger = logging.getLogger(__name__)


class QuotaExceededError(Exception):
    """Erreur levée quand un quota est dépassé"""
    pass


class MaxContactsReachedError(Exception):
    """Erreur levée quand le max de contacts (5) est atteint"""
    pass


class MemoryManager:
    """
    Gestionnaire de mémoire Luna.
    Fournit une API haut niveau pour gérer les conversations,
    instructions, tâches et notes.
    """

    def __init__(
        self,
        tenant_id: int,
        plan: PlanType = PlanType.ESSENTIEL,
        redis_client: Optional[RedisClient] = None
    ):
        self.tenant_id = tenant_id
        self.plan = plan
        self.quota = MemoryQuota.for_plan(plan)
        self.redis = redis_client or get_redis_client()

    # ========================================================================
    # CONVERSATIONS
    # ========================================================================

    def create_conversation(
        self,
        contact_phone: str,
        contact_name: Optional[str] = None,
        relation: Optional[str] = None,
        channel: Channel = Channel.APP,
    ) -> Conversation:
        """
        Crée une nouvelle conversation.

        Raises:
            QuotaExceededError: Si le quota de conversations est atteint
        """
        # Vérifie le quota
        current_count = len(self.redis.get_conversation_ids(self.tenant_id))
        if current_count >= self.quota.max_conversations:
            raise QuotaExceededError(
                f"Quota de conversations atteint ({self.quota.max_conversations})"
            )

        conv = Conversation(
            tenant_id=self.tenant_id,
            contact_phone=contact_phone,
            contact_name=contact_name,
            relation=relation,
            channel=channel,
        )

        # Enregistre dans Redis
        self.redis.add_conversation(self.tenant_id, conv.id)
        self.redis.set_conversation_meta(self.tenant_id, conv.id, conv.to_redis())

        # Incrémente l'usage
        self.redis.increment_daily_usage(self.tenant_id, "conversations_created")

        logger.info(f"Created conversation {conv.id} for tenant {self.tenant_id}")
        return conv

    def get_conversation(self, conv_id: str) -> Optional[Conversation]:
        """Récupère une conversation par son ID"""
        data = self.redis.get_conversation_meta(self.tenant_id, conv_id)
        if not data:
            return None
        return Conversation.from_redis(data)

    def list_conversations(self) -> List[Conversation]:
        """Liste toutes les conversations actives"""
        conv_ids = self.redis.get_conversation_ids(self.tenant_id)
        conversations = []
        for conv_id in conv_ids:
            conv = self.get_conversation(conv_id)
            if conv:
                conversations.append(conv)
        return sorted(conversations, key=lambda c: c.last_activity, reverse=True)

    def close_conversation(self, conv_id: str) -> None:
        """Ferme une conversation"""
        data = self.redis.get_conversation_meta(self.tenant_id, conv_id)
        if data:
            data["status"] = ConversationStatus.CLOSED.value
            self.redis.set_conversation_meta(self.tenant_id, conv_id, data)

    def delete_conversation(self, conv_id: str) -> None:
        """Supprime une conversation et ses messages"""
        self.redis.remove_conversation(self.tenant_id, conv_id)
        logger.info(f"Deleted conversation {conv_id}")

    # ========================================================================
    # MESSAGES
    # ========================================================================

    def add_message(
        self,
        conv_id: str,
        role: MessageRole,
        content: str,
        channel: Channel = Channel.APP,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """
        Ajoute un message à une conversation.

        Raises:
            QuotaExceededError: Si le quota de messages est atteint
        """
        # Vérifie le quota
        current_count = self.redis.get_message_count(self.tenant_id, conv_id)
        if current_count >= self.quota.max_messages_per_conv:
            raise QuotaExceededError(
                f"Quota de messages atteint ({self.quota.max_messages_per_conv})"
            )

        msg = Message(
            role=role,
            content=content,
            channel=channel,
            metadata=metadata,
        )

        # Enregistre le message
        self.redis.add_message(self.tenant_id, conv_id, json.dumps(msg.to_redis()))

        # Met à jour les métadonnées de la conversation
        conv_data = self.redis.get_conversation_meta(self.tenant_id, conv_id)
        if conv_data:
            conv_data["last_activity"] = datetime.utcnow().isoformat()
            conv_data["message_count"] = str(current_count + 1)
            self.redis.set_conversation_meta(self.tenant_id, conv_id, conv_data)

        # Incrémente l'usage
        self.redis.increment_daily_usage(self.tenant_id, "messages_count")

        return msg

    def get_messages(
        self,
        conv_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Message]:
        """Récupère les messages d'une conversation"""
        # Redis LRANGE: start, end (inclusive)
        start = offset
        end = offset + limit - 1 if limit > 0 else -1

        messages_json = self.redis.get_messages(self.tenant_id, conv_id, start, end)
        messages = []
        for msg_json in messages_json:
            try:
                data = json.loads(msg_json)
                messages.append(Message.from_redis(data))
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to parse message: {e}")
        return messages

    def get_recent_context(self, conv_id: str, max_messages: int = 10) -> str:
        """
        Récupère le contexte récent d'une conversation pour Luna.
        Retourne un résumé formaté des derniers messages.
        """
        messages = self.get_messages(conv_id, limit=max_messages)
        if not messages:
            return "Aucun message récent."

        context_lines = []
        for msg in messages[-max_messages:]:
            role_label = {
                MessageRole.LUNA: "Luna",
                MessageRole.SUBSCRIBER: "Souscripteur",
                MessageRole.CONTACT: "Contact",
                MessageRole.SYSTEM: "Système",
            }.get(msg.role, msg.role.value)
            context_lines.append(f"{role_label}: {msg.content}")

        return "\n".join(context_lines)

    # ========================================================================
    # INSTRUCTIONS
    # ========================================================================

    def add_instruction(
        self,
        description: str,
        action: ActionType,
        instruction_type: InstructionType = InstructionType.ONE_TIME,
        schedule: Optional[str] = None,
        target: str = "self",
        message_template: Optional[str] = None,
        priority: int = 5,
    ) -> Instruction:
        """
        Ajoute une instruction du souscripteur.

        Raises:
            QuotaExceededError: Si le quota d'instructions est atteint
        """
        # Vérifie le quota
        current_count = len(self.redis.get_active_instructions(self.tenant_id))
        if current_count >= self.quota.max_instructions:
            raise QuotaExceededError(
                f"Quota d'instructions atteint ({self.quota.max_instructions})"
            )

        instr = Instruction(
            tenant_id=self.tenant_id,
            type=instruction_type,
            description=description,
            schedule=schedule,
            action=action,
            target=target,
            message_template=message_template,
            priority=priority,
        )

        self.redis.add_instruction(
            self.tenant_id,
            instr.id,
            instr.to_redis(),
            priority=priority,
        )

        logger.info(f"Added instruction {instr.id}: {description}")
        return instr

    def get_instruction(self, instr_id: str) -> Optional[Instruction]:
        """Récupère une instruction par son ID"""
        data = self.redis.get_instruction(self.tenant_id, instr_id)
        if not data:
            return None
        return Instruction.from_redis(data)

    def list_active_instructions(self) -> List[Instruction]:
        """Liste les instructions actives par priorité"""
        instr_ids = self.redis.get_active_instructions(self.tenant_id)
        instructions = []
        for instr_id in instr_ids:
            instr = self.get_instruction(instr_id)
            if instr and instr.enabled:
                instructions.append(instr)
        return instructions

    def disable_instruction(self, instr_id: str) -> None:
        """Désactive une instruction"""
        self.redis.disable_instruction(self.tenant_id, instr_id)

    def delete_instruction(self, instr_id: str) -> None:
        """Supprime une instruction"""
        self.redis.delete_instruction(self.tenant_id, instr_id)

    def mark_instruction_executed(self, instr_id: str) -> None:
        """Marque une instruction comme exécutée"""
        data = self.redis.get_instruction(self.tenant_id, instr_id)
        if data:
            data["last_executed"] = datetime.utcnow().isoformat()
            data["execution_count"] = str(int(data.get("execution_count", 0)) + 1)
            self.redis.client.hset(
                self.redis.get_instruction_key(self.tenant_id, instr_id),
                mapping=data
            )
            self.redis.increment_daily_usage(self.tenant_id, "instructions_executed")

    # ========================================================================
    # TASKS
    # ========================================================================

    def create_task(
        self,
        task_type: ActionType,
        description: str,
        context: Optional[Dict[str, Any]] = None,
        instruction_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> TaskState:
        """Crée une nouvelle tâche"""
        task = TaskState(
            tenant_id=self.tenant_id,
            type=task_type,
            description=description,
            context=context,
            instruction_id=instruction_id,
            conversation_id=conversation_id,
        )

        self.redis.add_task(self.tenant_id, task.id, task.to_redis())
        logger.info(f"Created task {task.id}: {description}")
        return task

    def get_task(self, task_id: str) -> Optional[TaskState]:
        """Récupère une tâche par son ID"""
        data = self.redis.get_task(self.tenant_id, task_id)
        if not data:
            return None
        return TaskState.from_redis(data)

    def list_pending_tasks(self) -> List[TaskState]:
        """Liste les tâches en attente"""
        task_ids = self.redis.get_pending_tasks(self.tenant_id)
        tasks = []
        for task_id in task_ids:
            task = self.get_task(task_id)
            if task:
                tasks.append(task)
        return tasks

    def complete_task(self, task_id: str, result: str = "") -> None:
        """Marque une tâche comme terminée"""
        self.redis.complete_task(self.tenant_id, task_id, result)
        self.redis.increment_daily_usage(self.tenant_id, "tasks_completed")

    def fail_task(self, task_id: str, error: str) -> None:
        """Marque une tâche comme échouée"""
        data = self.redis.get_task(self.tenant_id, task_id)
        if data:
            data["status"] = TaskStatus.FAILED.value
            data["error"] = error
            data["completed_at"] = datetime.utcnow().isoformat()
            self.redis.client.hset(
                self.redis.get_task_key(self.tenant_id, task_id),
                mapping=data
            )

    # ========================================================================
    # TRUSTED CONTACTS
    # ========================================================================

    def add_trusted_contact(
        self,
        phone: str,
        name: str,
        relation: str,
        preferred_channel: Channel = Channel.SMS,
        emergency_only: bool = False,
    ) -> TrustedContact:
        """
        Ajoute un contact de confiance.

        Raises:
            MaxContactsReachedError: Si le maximum de 5 contacts est atteint
        """
        contact = TrustedContact(
            phone=phone,
            name=name,
            relation=relation,
            verified_at=datetime.utcnow(),
            preferred_channel=preferred_channel,
            emergency_only=emergency_only,
        )

        if not self.redis.add_trusted_contact(self.tenant_id, phone, contact.to_redis()):
            raise MaxContactsReachedError("Maximum de 5 contacts de confiance atteint")

        logger.info(f"Added trusted contact {phone} ({name}) for tenant {self.tenant_id}")
        return contact

    def get_trusted_contact(self, phone: str) -> Optional[TrustedContact]:
        """Récupère un contact de confiance"""
        data = self.redis.get_contact_profile(self.tenant_id, phone)
        if not data:
            return None
        return TrustedContact.from_redis(data)

    def list_trusted_contacts(self) -> List[TrustedContact]:
        """Liste tous les contacts de confiance"""
        phones = self.redis.get_trusted_contacts(self.tenant_id)
        contacts = []
        for phone in phones:
            contact = self.get_trusted_contact(phone)
            if contact:
                contacts.append(contact)
        return contacts

    def remove_trusted_contact(self, phone: str) -> None:
        """Supprime un contact de confiance"""
        self.redis.remove_trusted_contact(self.tenant_id, phone)
        logger.info(f"Removed trusted contact {phone}")

    def get_emergency_contacts(self) -> List[TrustedContact]:
        """Récupère les contacts à alerter en cas d'urgence"""
        contacts = self.list_trusted_contacts()
        # En urgence, on contacte tout le monde sauf ceux marqués "emergency_only=False"
        # qui ont explicitement demandé à ne pas être dérangés
        return [c for c in contacts if not c.emergency_only or True]  # Tous en urgence

    # ========================================================================
    # NOTES
    # ========================================================================

    def add_note(
        self,
        content: str,
        context: str,
        source: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Note:
        """
        Ajoute une note.

        Raises:
            QuotaExceededError: Si le quota de notes est atteint
        """
        # Vérifie le quota
        current_count = len(self.redis.get_notes(self.tenant_id, limit=self.quota.max_notes + 1))
        if current_count >= self.quota.max_notes:
            raise QuotaExceededError(
                f"Quota de notes atteint ({self.quota.max_notes})"
            )

        note = Note(
            tenant_id=self.tenant_id,
            content=content,
            context=context,
            source=source,
            tags=tags or [],
        )

        self.redis.add_note(self.tenant_id, note.id, note.to_redis())
        self.redis.increment_daily_usage(self.tenant_id, "notes_created")

        logger.info(f"Added note {note.id}: {content[:50]}...")
        return note

    def get_note(self, note_id: str) -> Optional[Note]:
        """Récupère une note par son ID"""
        data = self.redis.get_note(self.tenant_id, note_id)
        if not data:
            return None
        return Note.from_redis(data)

    def list_notes(self, limit: int = 50) -> List[Note]:
        """Liste les notes récentes"""
        note_ids = self.redis.get_notes(self.tenant_id, limit=limit)
        notes = []
        for note_id in note_ids:
            note = self.get_note(note_id)
            if note:
                notes.append(note)
        return notes

    # ========================================================================
    # SESSION & CONTEXT
    # ========================================================================

    def start_session(self, channel: Channel) -> Dict[str, Any]:
        """Démarre une nouvelle session Luna"""
        session_data = {
            "started_at": datetime.utcnow().isoformat(),
            "channel": channel.value,
            "mood": "",
            "topics": "[]",
            "pending_action": "",
        }
        self.redis.set_session(self.tenant_id, session_data)
        return session_data

    def get_session(self) -> Optional[Dict[str, str]]:
        """Récupère la session courante"""
        return self.redis.get_session(self.tenant_id)

    def update_session(self, **kwargs) -> None:
        """Met à jour la session courante"""
        session = self.redis.get_session(self.tenant_id) or {}
        session.update({k: str(v) for k, v in kwargs.items()})
        self.redis.set_session(self.tenant_id, session)

    def end_session(self) -> None:
        """Termine la session courante"""
        self.redis.clear_session(self.tenant_id)

    # ========================================================================
    # QUOTA & USAGE
    # ========================================================================

    def get_memory_usage(self) -> Dict[str, Any]:
        """Retourne l'usage mémoire actuel"""
        used_bytes = self.redis.get_memory_usage(self.tenant_id)
        return {
            "used_bytes": used_bytes,
            "limit_bytes": self.quota.memory_limit_bytes,
            "used_mb": round(used_bytes / (1024 * 1024), 2),
            "limit_mb": round(self.quota.memory_limit_bytes / (1024 * 1024), 2),
            "percentage": round((used_bytes / self.quota.memory_limit_bytes) * 100, 1),
        }

    def get_daily_stats(self, date_str: Optional[str] = None) -> Dict[str, int]:
        """Retourne les statistiques d'usage quotidien"""
        return self.redis.get_daily_usage(self.tenant_id, date_str)

    def get_quota_status(self) -> Dict[str, Any]:
        """Retourne le statut complet des quotas"""
        conversations = len(self.redis.get_conversation_ids(self.tenant_id))
        instructions = len(self.redis.get_active_instructions(self.tenant_id))
        notes = len(self.redis.get_notes(self.tenant_id, limit=self.quota.max_notes + 1))
        contacts = len(self.redis.get_trusted_contacts(self.tenant_id))
        memory = self.get_memory_usage()

        return {
            "plan": self.plan.value,
            "conversations": {
                "used": conversations,
                "limit": self.quota.max_conversations,
                "percentage": round((conversations / self.quota.max_conversations) * 100, 1),
            },
            "instructions": {
                "used": instructions,
                "limit": self.quota.max_instructions,
                "percentage": round((instructions / self.quota.max_instructions) * 100, 1),
            },
            "notes": {
                "used": notes,
                "limit": self.quota.max_notes,
                "percentage": round((notes / self.quota.max_notes) * 100, 1),
            },
            "trusted_contacts": {
                "used": contacts,
                "limit": 5,
            },
            "memory": memory,
        }
