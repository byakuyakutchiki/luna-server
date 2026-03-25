"""
Luna Instruction Executor - Exécution des instructions

Responsable de l'exécution effective des instructions:
- Routage vers les bons services (SMS, rappels, etc.)
- Vérification des conditions
- Gestion des erreurs d'exécution
- Logging des résultats
"""
import logging
from typing import Optional, Dict, Any, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from .parser import ParsedInstruction, ActionType, ConditionType
from .scheduler import ScheduledTask, TaskStatus

logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    """Statut d'exécution"""
    SUCCESS = "success"
    PARTIAL = "partial"  # Partiellement exécuté
    FAILED = "failed"
    SKIPPED = "skipped"  # Condition non remplie
    BLOCKED = "blocked"  # Bloqué (quota, sécurité)
    PENDING_CONFIRMATION = "pending_confirmation"  # En attente de confirmation


@dataclass
class ExecutionResult:
    """Résultat d'exécution d'une instruction"""
    status: ExecutionStatus
    instruction_id: str
    action_type: ActionType
    message: str  # Message pour l'utilisateur
    details: Dict[str, Any] = field(default_factory=dict)
    executed_at: datetime = field(default_factory=datetime.utcnow)
    error: Optional[str] = None
    requires_followup: bool = False
    followup_action: Optional[str] = None


# Type pour les handlers d'action
ActionHandler = Callable[[ParsedInstruction, Dict[str, Any]], Awaitable[ExecutionResult]]


class InstructionExecutor:
    """
    Exécuteur d'instructions Luna.

    Responsabilités:
    1. Router les instructions vers les bons handlers
    2. Vérifier les conditions d'exécution
    3. Demander confirmation si nécessaire
    4. Exécuter et logger les résultats
    """

    def __init__(
        self,
        memory_manager=None,
        sms_service=None,
        safety_guardian=None,
        action_service=None,
        voice_service=None,
        visio_service=None,
    ):
        """
        Args:
            memory_manager: Gestionnaire de mémoire Redis
            sms_service: Service d'envoi SMS
            safety_guardian: Gardien de sécurité
            action_service: Service de confirmation d'actions
            voice_service: TwilioVoiceClient pour les appels sortants
            visio_service: TavusClient pour les visioconférences
        """
        self.memory = memory_manager
        self.sms = sms_service
        self.safety = safety_guardian
        self.action_service = action_service
        self.voice = voice_service
        self.visio = visio_service

        # Handlers par type d'action (alignés avec parser.py ActionType)
        self._handlers: Dict[ActionType, ActionHandler] = {
            ActionType.REMINDER: self._handle_reminder,
            ActionType.SMS_CONTACT: self._handle_sms_contact,
            ActionType.CALL_CONTACT: self._handle_call_contact,
            ActionType.VISIO_CONTACT: self._handle_visio_contact,
            ActionType.WAKE_UP: self._handle_wake_up,
            ActionType.CHECK_IN: self._handle_check_in,
            ActionType.DAILY_ROUTINE: self._handle_daily_routine,
            ActionType.SURVEILLANCE: self._handle_surveillance,
            ActionType.NOTE: self._handle_note,
            ActionType.INFORMATION: self._handle_information,
            ActionType.READING: self._handle_reading,
            ActionType.GAME: self._handle_game,
            ActionType.MUSIC: self._handle_music,
            ActionType.GRATITUDE: self._handle_gratitude,
        }

    async def execute(
        self,
        task: ScheduledTask,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        Exécute une tâche planifiée.

        Args:
            task: La tâche à exécuter
            context: Contexte d'exécution optionnel

        Returns:
            Résultat de l'exécution
        """
        context = context or {}
        instruction = task.instruction

        logger.info(f"Executing instruction {task.instruction_id}: {instruction.action_type.value}")

        # 1. Vérifier les conditions
        if not await self._check_conditions(instruction, context):
            return ExecutionResult(
                status=ExecutionStatus.SKIPPED,
                instruction_id=task.instruction_id,
                action_type=instruction.action_type,
                message="Conditions non remplies pour l'exécution",
                details={"condition": instruction.condition.value},
            )

        # 2. Vérification de sécurité
        if self.safety:
            can_proceed, block_message = self.safety.can_proceed(instruction.original_text)
            if not can_proceed:
                return ExecutionResult(
                    status=ExecutionStatus.BLOCKED,
                    instruction_id=task.instruction_id,
                    action_type=instruction.action_type,
                    message=block_message or "Action bloquée pour raison de sécurité",
                    error="safety_block",
                )

        # 3. Vérifier si confirmation requise (pour actions consommatrices)
        if self._requires_confirmation(instruction) and self.action_service:
            confirmation_result = await self._request_confirmation(task, context)
            if confirmation_result:
                return confirmation_result

        # 4. Exécuter l'action
        handler = self._handlers.get(instruction.action_type)
        if not handler:
            handler = self._handle_generic

        try:
            result = await handler(instruction, context)
            result.instruction_id = task.instruction_id

            # Log dans la mémoire
            if self.memory:
                self._log_execution(task, result)

            return result

        except Exception as e:
            logger.error(f"Error executing instruction {task.instruction_id}: {e}")
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                instruction_id=task.instruction_id,
                action_type=instruction.action_type,
                message="Une erreur s'est produite lors de l'exécution",
                error=str(e),
            )

    def _requires_confirmation(self, instruction: ParsedInstruction) -> bool:
        """Détermine si l'instruction nécessite une confirmation utilisateur"""
        # Actions consommatrices de quota
        confirmation_required = {
            ActionType.SMS_CONTACT,
            ActionType.CALL_CONTACT,
            ActionType.VISIO_CONTACT,
        }
        # Le réveil ne demande PAS confirmation (sinon ça sert à rien)
        return instruction.action_type in confirmation_required

    async def _request_confirmation(
        self,
        task: ScheduledTask,
        context: Dict[str, Any],
    ) -> Optional[ExecutionResult]:
        """
        Demande confirmation à l'utilisateur avant exécution.

        Returns:
            ExecutionResult si en attente de confirmation, None si déjà confirmé
        """
        if not self.action_service:
            return None

        # Vérifie si déjà confirmé
        action_id = context.get("action_id")
        if action_id and await self.action_service.is_confirmed(action_id):
            return None

        # Crée une demande de confirmation
        instruction = task.instruction
        description = self._build_confirmation_description(instruction)

        action_request = await self.action_service.create_action_request(
            tenant_id=task.tenant_id,
            action_type=instruction.action_type.value,
            target=instruction.target or "",
            description=description,
            instruction_id=task.instruction_id,
        )

        return ExecutionResult(
            status=ExecutionStatus.PENDING_CONFIRMATION,
            instruction_id=task.instruction_id,
            action_type=instruction.action_type,
            message=f"Confirmez-vous que je dois {description} ?",
            details={"action_id": action_request.action_id},
            requires_followup=True,
            followup_action="await_confirmation",
        )

    def _build_confirmation_description(self, instruction: ParsedInstruction) -> str:
        """Construit la description pour la demande de confirmation"""
        target = instruction.target or "votre contact"

        if instruction.action_type == ActionType.SMS_CONTACT:
            return f"envoyer un SMS à {target}"
        elif instruction.action_type == ActionType.CALL_CONTACT:
            return f"appeler {target}"
        elif instruction.action_type == ActionType.VISIO_CONTACT:
            return f"lancer une visio avec {target}"
        else:
            return instruction.original_text

    async def _check_conditions(
        self,
        instruction: ParsedInstruction,
        context: Dict[str, Any],
    ) -> bool:
        """Vérifie si les conditions d'exécution sont remplies"""
        condition = instruction.condition

        if condition == ConditionType.NONE:
            return True

        if condition == ConditionType.IF_NO_RESPONSE:
            # Vérifie si pas de réponse depuis un certain temps
            last_activity = context.get("last_user_activity")
            if last_activity:
                # Récupère la durée depuis les params
                duration = instruction.condition_params.get("duration", 2)
                unit = instruction.condition_params.get("unit", "heure")

                # Convertit en secondes
                if unit in ("heure", "heures"):
                    threshold_seconds = duration * 3600
                elif unit in ("minute", "minutes"):
                    threshold_seconds = duration * 60
                elif unit in ("jour", "jours"):
                    threshold_seconds = duration * 86400
                else:
                    threshold_seconds = 7200  # 2h par défaut

                elapsed = (datetime.utcnow() - last_activity).total_seconds()
                return elapsed >= threshold_seconds
            # Pas d'activité connue = condition remplie
            return True

        elif condition == ConditionType.IF_CONFIRMED:
            # L'action a été confirmée par l'utilisateur
            return context.get("confirmed", False)

        elif condition == ConditionType.IF_WEATHER:
            # Vérifier les conditions météo (nécessiterait une API météo)
            # Pour l'instant, on considère la condition remplie
            return True

        elif condition == ConditionType.IF_TIME_PASSED:
            # Vérifie si X temps s'est écoulé depuis un événement
            event_time = context.get("event_time")
            if event_time:
                duration = instruction.condition_params.get("duration", 1)
                elapsed = (datetime.utcnow() - event_time).total_seconds()
                return elapsed >= (duration * 3600)  # Supposé en heures
            return False

        return True

    # =========================================================================
    # HANDLERS D'ACTION
    # =========================================================================

    async def _handle_reminder(
        self,
        instruction: ParsedInstruction,
        context: Dict[str, Any],
    ) -> ExecutionResult:
        """
        Gère les rappels généraux.

        Envoie un SMS au souscripteur + notification in-app.
        """
        message = instruction.message_template or "C'est l'heure de votre rappel"

        # Envoyer un SMS de rappel au souscripteur
        sms_sent = False
        subscriber_phone = context.get("subscriber_phone", "")
        if self.sms and subscriber_phone:
            try:
                ok, details = self.sms.send(subscriber_phone, f"[Luna] Rappel : {message}")
                sms_sent = ok
                if ok:
                    logger.info(f"Reminder SMS sent to {subscriber_phone}: {message[:50]}")
                else:
                    logger.warning(f"Reminder SMS failed: {details}")
            except Exception as e:
                logger.warning(f"Reminder SMS error: {e}")

        # Sauvegarder en note pour traçabilité
        if self.memory:
            try:
                self.memory.add_note(
                    content=f"[Rappel execute] {message}" + (" (SMS envoye)" if sms_sent else " (in-app uniquement)"),
                    context="reminder_executed",
                    tags=["rappel", "instruction"],
                )
            except Exception:
                pass

        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            instruction_id="",
            action_type=ActionType.REMINDER,
            message=message,
            details={
                "reminder_text": message,
                "delivery_method": "sms" if sms_sent else "in_app",
                "sms_sent": sms_sent,
            },
            requires_followup=True,
            followup_action="speak_to_user",
        )

    async def _handle_sms_contact(
        self,
        instruction: ParsedInstruction,
        context: Dict[str, Any],
    ) -> ExecutionResult:
        """
        Gère l'envoi de SMS aux contacts de confiance.

        IMPORTANT: Nécessite confirmation préalable.
        """
        if not self.sms:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                instruction_id="",
                action_type=ActionType.SMS_CONTACT,
                message="Service SMS non disponible",
                error="sms_service_unavailable",
            )

        target = instruction.target
        message = instruction.message_template

        if not target or target in ("self", "contact_unknown"):
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                instruction_id="",
                action_type=ActionType.SMS_CONTACT,
                message="Aucun destinataire spécifié",
                error="no_recipient",
            )

        if not message:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                instruction_id="",
                action_type=ActionType.SMS_CONTACT,
                message="Aucun message spécifié",
                error="no_message",
            )

        # Récupère le numéro de téléphone du contact
        phone_number = await self._resolve_contact_phone(target, context)
        if not phone_number:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                instruction_id="",
                action_type=ActionType.SMS_CONTACT,
                message=f"Numéro de téléphone non trouvé pour {target}",
                error="contact_not_found",
            )

        # Envoie le SMS
        tenant_id = context.get("tenant_id")
        success, result = await self.sms.send_sms(tenant_id, phone_number, message)

        if success:
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                instruction_id="",
                action_type=ActionType.SMS_CONTACT,
                message=f"SMS envoyé à {target}",
                details={
                    "recipient": target,
                    "phone": phone_number,
                    "message_preview": message[:50] + "..." if len(message) > 50 else message,
                },
            )
        else:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                instruction_id="",
                action_type=ActionType.SMS_CONTACT,
                message=f"Échec de l'envoi du SMS à {target}",
                error=result.get("error", "unknown_error"),
            )

    async def _handle_call_contact(
        self,
        instruction: ParsedInstruction,
        context: Dict[str, Any],
    ) -> ExecutionResult:
        """
        Gère les appels téléphoniques aux contacts via Twilio Voice.

        Luna appelle le contact, et quand il décroche, il parle avec Luna
        via OpenAI Realtime (Media Stream).
        """
        if not self.voice:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                instruction_id="",
                action_type=ActionType.CALL_CONTACT,
                message="Service d'appel vocal non disponible",
                error="voice_service_unavailable",
            )

        target = instruction.target
        if not target or target in ("self", "contact_unknown"):
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                instruction_id="",
                action_type=ActionType.CALL_CONTACT,
                message="Aucun destinataire spécifié pour l'appel",
                error="no_recipient",
            )

        # Résoudre le numéro du contact
        phone_number = await self._resolve_contact_phone(target, context)
        if not phone_number:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                instruction_id="",
                action_type=ActionType.CALL_CONTACT,
                message=f"Numéro de téléphone non trouvé pour {target}",
                error="contact_not_found",
            )

        # Lancer l'appel via Twilio
        success, data = await self.voice.initiate_call_async(phone_number)

        if success:
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                instruction_id="",
                action_type=ActionType.CALL_CONTACT,
                message=f"Appel lancé vers {target}",
                details={
                    "recipient": target,
                    "phone": phone_number,
                    "call_sid": data.get("call_sid", ""),
                },
            )
        else:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                instruction_id="",
                action_type=ActionType.CALL_CONTACT,
                message=f"Échec de l'appel vers {target}",
                error=data.get("error", "unknown_error"),
            )

    async def _handle_visio_contact(
        self,
        instruction: ParsedInstruction,
        context: Dict[str, Any],
    ) -> ExecutionResult:
        """
        Gère les visioconférences planifiées avec un contact.

        Crée la session Tavus et envoie le lien par SMS au contact.
        """
        if not self.visio:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                instruction_id="",
                action_type=ActionType.VISIO_CONTACT,
                message="Service visio non disponible",
                error="visio_service_unavailable",
            )
        if not self.sms:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                instruction_id="",
                action_type=ActionType.VISIO_CONTACT,
                message="Service SMS non disponible pour envoyer le lien visio",
                error="sms_service_unavailable",
            )

        target = instruction.target
        if not target or target in ("self", "contact_unknown"):
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                instruction_id="",
                action_type=ActionType.VISIO_CONTACT,
                message="Aucun contact spécifié pour la visio",
                error="no_recipient",
            )

        phone_number = await self._resolve_contact_phone(target, context)
        if not phone_number:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                instruction_id="",
                action_type=ActionType.VISIO_CONTACT,
                message=f"Numéro non trouvé pour {target}",
                error="contact_not_found",
            )

        # Créer la visio Tavus
        tenant_id = context.get("tenant_id", 0)
        import os
        visio_max = int(os.getenv("VISIO_MAX_DURATION", "15")) * 60
        greeting = f"Bonjour {target} ! C'est Luna. Bienvenue en visio !"
        visio_context = f"Tu es Luna. Visio planifiée avec {target}. Sois chaleureuse."

        success_visio, data = await self.visio.create_conversation(
            tenant_id=tenant_id,
            custom_greeting=greeting,
            context=visio_context,
            max_duration=visio_max,
        )
        if not success_visio:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                instruction_id="",
                action_type=ActionType.VISIO_CONTACT,
                message=f"Impossible de créer la visio : {data.get('error', 'inconnu')}",
                error="visio_creation_failed",
            )

        visio_url = data["conversation_url"]

        # Envoyer le lien par SMS
        from integrations.twilio.sms_client import TwilioSMSClient
        normalized = TwilioSMSClient.normalize_phone(phone_number)
        invite_msg = f"[Luna] Visio planifiée ! Rejoignez ici : {visio_url}"
        success_sms, _ = self.sms.send(normalized, invite_msg)

        return ExecutionResult(
            status=ExecutionStatus.SUCCESS if success_sms else ExecutionStatus.PARTIAL,
            instruction_id="",
            action_type=ActionType.VISIO_CONTACT,
            message=f"Visio créée avec {target}" + (" (SMS envoyé)" if success_sms else " (échec SMS, lien disponible)"),
            details={
                "recipient": target,
                "visio_url": visio_url,
                "sms_sent": success_sms,
            },
        )

    async def _handle_wake_up(
        self,
        instruction: ParsedInstruction,
        context: Dict[str, Any],
    ) -> ExecutionResult:
        """
        Gère le réveil : Luna appelle le souscripteur via Twilio.

        Le téléphone sonne comme un réveil. Quand le souscripteur décroche,
        Luna lui dit bonjour via OpenAI Realtime.
        """
        if not self.voice:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                instruction_id="",
                action_type=ActionType.WAKE_UP,
                message="Service d'appel vocal non disponible pour le réveil",
                error="voice_service_unavailable",
            )

        # Le réveil appelle le souscripteur (pas un contact)
        # On utilise le numéro admin/subscriber depuis le contexte ou l'env
        import os
        subscriber_phone = context.get("subscriber_phone") or os.getenv("ADMIN_PHONE", "")

        if not subscriber_phone:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                instruction_id="",
                action_type=ActionType.WAKE_UP,
                message="Numéro du souscripteur non configuré pour le réveil",
                error="no_subscriber_phone",
            )

        success, data = await self.voice.initiate_call_async(subscriber_phone)

        if success:
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                instruction_id="",
                action_type=ActionType.WAKE_UP,
                message="Réveil lancé ! Luna vous appelle.",
                details={
                    "phone": subscriber_phone,
                    "call_sid": data.get("call_sid", ""),
                    "delivery_method": "twilio_call",
                },
            )
        else:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                instruction_id="",
                action_type=ActionType.WAKE_UP,
                message="Échec du réveil (appel impossible)",
                error=data.get("error", "unknown_error"),
            )

    async def _handle_check_in(
        self,
        instruction: ParsedInstruction,
        context: Dict[str, Any],
    ) -> ExecutionResult:
        """
        Gère les vérifications de bien-être.

        Luna vérifie que le souscripteur va bien.
        """
        check_message = instruction.message_template or "Comment allez-vous aujourd'hui ?"

        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            instruction_id="",
            action_type=ActionType.CHECK_IN,
            message="Vérification de bien-être initiée",
            details={
                "check_message": check_message,
                "delivery_method": "luna_voice",
            },
            requires_followup=True,
            followup_action="initiate_check_in_conversation",
        )

    async def _handle_daily_routine(
        self,
        instruction: ParsedInstruction,
        context: Dict[str, Any],
    ) -> ExecutionResult:
        """
        Gère les routines quotidiennes.
        """
        message = instruction.message_template or "C'est l'heure de votre routine"

        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            instruction_id="",
            action_type=ActionType.DAILY_ROUTINE,
            message=message,
            details={
                "routine_message": message,
                "delivery_method": "luna_voice",
            },
            requires_followup=True,
            followup_action="speak_to_user",
        )

    async def _handle_surveillance(
        self,
        instruction: ParsedInstruction,
        context: Dict[str, Any],
    ) -> ExecutionResult:
        """
        Gère la surveillance/monitoring.

        Si pas de réponse pendant X temps, alerte les contacts.

        IMPORTANT:
        - Luna n'appelle JAMAIS les services d'urgence directement
        - Elle suggère aux contacts de le faire si nécessaire
        """
        if not self.sms:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                instruction_id="",
                action_type=ActionType.SURVEILLANCE,
                message="Service d'alerte non disponible",
                error="alert_service_unavailable",
            )

        tenant_id = context.get("tenant_id")
        target = instruction.target or "vos contacts de confiance"

        alert_message = (
            f"[YAWatch Luna] Alerte: Votre proche ne répond pas depuis un moment. "
            f"Pourriez-vous vérifier qu'il va bien ? "
            f"Si vous êtes inquiet, nous vous recommandons fortement d'appeler les secours."
        )

        # Récupère les contacts de confiance
        contacts = await self._get_trusted_contacts(tenant_id)
        if not contacts:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                instruction_id="",
                action_type=ActionType.SURVEILLANCE,
                message="Aucun contact de confiance configuré",
                error="no_trusted_contacts",
            )

        # Envoie l'alerte à chaque contact
        sent_count = 0
        errors = []

        for contact in contacts:
            success, result = await self.sms.send_sms(
                tenant_id,
                contact["phone"],
                alert_message,
            )
            if success:
                sent_count += 1
            else:
                errors.append(f"{contact['name']}: {result.get('error', 'erreur')}")

        if sent_count > 0:
            return ExecutionResult(
                status=ExecutionStatus.SUCCESS if not errors else ExecutionStatus.PARTIAL,
                instruction_id="",
                action_type=ActionType.SURVEILLANCE,
                message=f"Alerte de surveillance envoyée à {sent_count} contact(s)",
                details={
                    "contacts_alerted": sent_count,
                    "errors": errors if errors else None,
                },
            )
        else:
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                instruction_id="",
                action_type=ActionType.SURVEILLANCE,
                message="Échec de l'envoi des alertes de surveillance",
                error="; ".join(errors),
            )

    async def _handle_note(
        self,
        instruction: ParsedInstruction,
        context: Dict[str, Any],
    ) -> ExecutionResult:
        """
        Gère la prise de notes.
        """
        content = instruction.message_template or instruction.original_text

        # Stocke la note en mémoire
        if self.memory:
            try:
                await self.memory.add_note(
                    content=content,
                    context="user_note",
                    source="instruction_executor",
                    tags=["note", "utilisateur"],
                )
            except Exception as e:
                logger.warning(f"Could not save note to memory: {e}")

        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            instruction_id="",
            action_type=ActionType.NOTE,
            message=f"Note enregistrée: {content[:50]}..." if len(content) > 50 else f"Note enregistrée: {content}",
            details={
                "note_content": content,
            },
        )

    async def _handle_information(
        self,
        instruction: ParsedInstruction,
        context: Dict[str, Any],
    ) -> ExecutionResult:
        """
        Gère les demandes d'information.

        Luna informe le souscripteur de quelque chose.
        """
        message = instruction.message_template or "Voici l'information demandée"

        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            instruction_id="",
            action_type=ActionType.INFORMATION,
            message=message,
            details={
                "information": message,
                "delivery_method": "luna_voice",
            },
            requires_followup=True,
            followup_action="speak_to_user",
        )

    async def _handle_reading(
        self,
        instruction: ParsedInstruction,
        context: Dict[str, Any],
    ) -> ExecutionResult:
        """Luna lit un texte, une histoire ou un poème au souscripteur."""
        message = instruction.message_template or "C'est l'heure de votre moment lecture. Installez-vous confortablement."
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            instruction_id="",
            action_type=ActionType.READING,
            message=message,
            details={"delivery_method": "luna_voice", "reading_type": "story"},
            requires_followup=True,
            followup_action="speak_to_user",
        )

    async def _handle_game(
        self,
        instruction: ParsedInstruction,
        context: Dict[str, Any],
    ) -> ExecutionResult:
        """Luna propose un jeu (quiz, devinette, culture générale)."""
        message = instruction.message_template or "C'est l'heure du jeu ! Prêt pour un petit quiz ?"
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            instruction_id="",
            action_type=ActionType.GAME,
            message=message,
            details={"delivery_method": "luna_voice", "game_type": "quiz"},
            requires_followup=True,
            followup_action="initiate_game_conversation",
        )

    async def _handle_music(
        self,
        instruction: ParsedInstruction,
        context: Dict[str, Any],
    ) -> ExecutionResult:
        """Luna propose un moment musical (chante, fredonne, suggère)."""
        message = instruction.message_template or "C'est votre moment musical. Que souhaitez-vous écouter aujourd'hui ?"
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            instruction_id="",
            action_type=ActionType.MUSIC,
            message=message,
            details={"delivery_method": "luna_voice"},
            requires_followup=True,
            followup_action="speak_to_user",
        )

    async def _handle_gratitude(
        self,
        instruction: ParsedInstruction,
        context: Dict[str, Any],
    ) -> ExecutionResult:
        """Luna guide un exercice de gratitude."""
        message = instruction.message_template or "Prenons un moment pour la gratitude. Quelles sont les 3 choses positives de votre journée ?"
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            instruction_id="",
            action_type=ActionType.GRATITUDE,
            message=message,
            details={"delivery_method": "luna_voice"},
            requires_followup=True,
            followup_action="initiate_gratitude_conversation",
        )

    async def _handle_generic(
        self,
        instruction: ParsedInstruction,
        context: Dict[str, Any],
    ) -> ExecutionResult:
        """
        Handler générique pour les types d'action non reconnus.
        """
        return ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            instruction_id="",
            action_type=instruction.action_type,
            message=f"Instruction notée: {instruction.original_text}",
            details={
                "original_instruction": instruction.original_text,
            },
        )

    # =========================================================================
    # HELPERS
    # =========================================================================

    async def _resolve_contact_phone(
        self,
        contact_name: str,
        context: Dict[str, Any],
    ) -> Optional[str]:
        """Résout le nom d'un contact vers son numéro de téléphone"""
        if not self.memory:
            return None

        # Cherche dans les contacts de confiance
        tenant_id = context.get("tenant_id")
        contacts = await self._get_trusted_contacts(tenant_id)

        contact_name_lower = contact_name.lower()
        for contact in contacts:
            if contact_name_lower in contact.get("name", "").lower():
                return contact.get("phone")
            # Cherche aussi par relation (fils, fille, etc.)
            if contact_name_lower in contact.get("relation", "").lower():
                return contact.get("phone")

        return None

    async def _get_trusted_contacts(
        self,
        tenant_id: Optional[int],
    ) -> list:
        """Récupère la liste des contacts de confiance"""
        if not self.memory or not tenant_id:
            return []

        try:
            # list_trusted_contacts() is sync and uses self.tenant_id internally
            contacts = self.memory.list_trusted_contacts()
            return [
                {"name": c.name, "phone": c.phone, "relation": c.relation}
                for c in contacts
            ]
        except Exception as e:
            logger.warning(f"Error fetching trusted contacts: {e}")
            return []

    def _log_execution(
        self,
        task: ScheduledTask,
        result: ExecutionResult,
    ) -> None:
        """Log l'exécution dans la mémoire avec reasoning"""
        try:
            reasoning = (
                f"Instruction executee automatiquement: "
                f"{task.instruction.action_type.value} - "
                f"declenchee par le scheduler ({task.instruction.original_text[:80]})"
            )
            self.memory.add_note(
                content=f"Exécution instruction: {result.message}\n[Raison: {reasoning}]",
                context="instruction_execution",
                source="instruction_executor",
                tags=[
                    "execution",
                    result.status.value,
                    task.instruction.action_type.value,
                    "reasoning",
                ],
            )
        except Exception as e:
            logger.warning(f"Could not log execution to memory: {e}")


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_instruction_executor(
    memory_manager=None,
    sms_service=None,
    safety_guardian=None,
    action_service=None,
    voice_service=None,
    visio_service=None,
) -> InstructionExecutor:
    """
    Factory pour créer un InstructionExecutor configuré.

    Args:
        memory_manager: MemoryManager pour la persistance
        sms_service: SMSService pour l'envoi de SMS
        safety_guardian: SafetyGuardian pour les vérifications
        action_service: ActionService pour les confirmations
        voice_service: TwilioVoiceClient pour les appels sortants
        visio_service: TavusClient pour les visioconférences

    Returns:
        InstructionExecutor configuré
    """
    return InstructionExecutor(
        memory_manager=memory_manager,
        sms_service=sms_service,
        safety_guardian=safety_guardian,
        action_service=action_service,
        voice_service=voice_service,
        visio_service=visio_service,
    )
