"""
Luna Confirmation Manager - Gestion des confirmations d'actions

Gère le flux de confirmation:
1. Luna propose une action
2. Le souscripteur confirme ou refuse
3. Si confirmé, l'action est exécutée
4. Si pas de réponse, l'action expire

RÈGLE ABSOLUE:
Aucune action consommatrice de quota n'est exécutée
sans confirmation explicite du souscripteur.
Exception unique: alerte de sécurité vitale aux contacts de confiance.
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from .models import ActionRequest, ActionStatus, ActionType, ActionLog

logger = logging.getLogger(__name__)

# Durée par défaut avant expiration d'une demande de confirmation
DEFAULT_EXPIRATION_MINUTES = 10

# Actions qui ne nécessitent PAS de confirmation
# (uniquement les alertes de sécurité vitale)
BYPASS_CONFIRMATION_SOURCES = {"emergency_critical"}


class ConfirmationManager:
    """
    Gestionnaire de confirmations d'actions.

    Responsabilités:
    1. Créer des demandes de confirmation
    2. Suivre leur statut
    3. Valider ou rejeter
    4. Gérer l'expiration
    5. Logger chaque étape pour audit
    """

    def __init__(self, memory_manager=None):
        """
        Args:
            memory_manager: MemoryManager pour persister les demandes
        """
        self.memory = memory_manager
        # Cache en mémoire des demandes actives (tenant_id -> {action_id -> request})
        self._pending: Dict[int, Dict[str, ActionRequest]] = {}

    def propose_action(
        self,
        tenant_id: int,
        action_type: ActionType,
        target: str,
        description: str,
        message_body: Optional[str] = None,
        source: str = "luna",
        instruction_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        estimated_cost: int = 1,
        expiration_minutes: int = DEFAULT_EXPIRATION_MINUTES,
    ) -> ActionRequest:
        """
        Crée une demande d'action en attente de confirmation.

        Args:
            tenant_id: ID du tenant
            action_type: Type d'action
            target: Cible (nom du contact)
            description: Description lisible ("envoyer un SMS à Marie")
            message_body: Contenu du message si SMS
            source: Qui propose ("luna", "instruction", "emergency")
            instruction_id: ID de l'instruction source si applicable
            conversation_id: ID de la conversation en cours
            estimated_cost: Coût estimé en unités
            expiration_minutes: Délai avant expiration

        Returns:
            ActionRequest créée
        """
        request = ActionRequest(
            tenant_id=tenant_id,
            action_type=action_type,
            target=target,
            description=description,
            message_body=message_body,
            source=source,
            instruction_id=instruction_id,
            conversation_id=conversation_id,
            estimated_cost=estimated_cost,
            status=ActionStatus.AWAITING_CONFIRMATION,
            expires_at=datetime.utcnow() + timedelta(minutes=expiration_minutes),
        )

        # Bypass confirmation pour urgences critiques
        if source in BYPASS_CONFIRMATION_SOURCES:
            request.status = ActionStatus.CONFIRMED
            request.confirmed = True
            request.confirmed_at = datetime.utcnow()
            request.confirmation_method = "auto_emergency"
            logger.warning(
                f"Action {request.action_id} auto-confirmed: emergency source"
            )

        # Stocke dans le cache
        if tenant_id not in self._pending:
            self._pending[tenant_id] = {}
        self._pending[tenant_id][request.action_id] = request

        # Log
        self._log_event(request, "proposed", f"Action proposée: {description}")

        logger.info(
            f"Action proposed [{request.action_id}]: {description} "
            f"(tenant={tenant_id}, type={action_type.value})"
        )

        return request

    def confirm(
        self,
        tenant_id: int,
        action_id: str,
        method: str = "voice",
    ) -> Optional[ActionRequest]:
        """
        Confirme une action en attente.

        Args:
            tenant_id: ID du tenant
            action_id: ID de l'action à confirmer
            method: Méthode de confirmation ("voice", "text", "button")

        Returns:
            ActionRequest confirmée ou None si non trouvée/expirée
        """
        request = self._get_pending(tenant_id, action_id)
        if not request:
            logger.warning(f"Action {action_id} not found for tenant {tenant_id}")
            return None

        # Vérifie expiration
        if request.is_expired():
            request.status = ActionStatus.EXPIRED
            self._log_event(request, "expired", "Action expirée sans confirmation")
            return None

        # Confirme
        request.status = ActionStatus.CONFIRMED
        request.confirmed = True
        request.confirmed_at = datetime.utcnow()
        request.confirmation_method = method

        self._log_event(
            request, "confirmed",
            f"Action confirmée par {method}",
        )

        logger.info(f"Action confirmed [{action_id}] via {method}")
        return request

    def reject(
        self,
        tenant_id: int,
        action_id: str,
        reason: Optional[str] = None,
    ) -> Optional[ActionRequest]:
        """
        Rejette une action proposée.

        Args:
            tenant_id: ID du tenant
            action_id: ID de l'action
            reason: Raison du refus

        Returns:
            ActionRequest rejetée ou None
        """
        request = self._get_pending(tenant_id, action_id)
        if not request:
            return None

        request.status = ActionStatus.REJECTED
        request.rejection_reason = reason

        self._log_event(
            request, "rejected",
            f"Action refusée: {reason or 'pas de raison donnée'}",
        )

        logger.info(f"Action rejected [{action_id}]: {reason}")
        return request

    def cancel(
        self,
        tenant_id: int,
        action_id: str,
    ) -> Optional[ActionRequest]:
        """
        Annule une action (par Luna ou le système).

        Args:
            tenant_id: ID du tenant
            action_id: ID de l'action

        Returns:
            ActionRequest annulée ou None
        """
        request = self._get_pending(tenant_id, action_id)
        if not request:
            return None

        request.status = ActionStatus.CANCELLED

        self._log_event(request, "cancelled", "Action annulée")

        logger.info(f"Action cancelled [{action_id}]")
        return request

    def mark_executing(self, request: ActionRequest) -> None:
        """Marque une action comme en cours d'exécution"""
        request.status = ActionStatus.EXECUTING
        request.executed_at = datetime.utcnow()
        self._log_event(request, "executing", "Action en cours d'exécution")

    def mark_completed(self, request: ActionRequest, message: str = "") -> None:
        """Marque une action comme terminée"""
        request.status = ActionStatus.COMPLETED
        self._log_event(
            request, "completed",
            f"Action terminée: {message}" if message else "Action terminée",
        )

    def mark_failed(self, request: ActionRequest, error: str) -> None:
        """Marque une action comme échouée"""
        request.status = ActionStatus.FAILED
        self._log_event(request, "failed", f"Action échouée: {error}")

    def is_confirmed(self, tenant_id: int, action_id: str) -> bool:
        """Vérifie si une action est confirmée"""
        request = self._get_pending(tenant_id, action_id)
        return request is not None and request.confirmed

    def get_pending_actions(self, tenant_id: int) -> List[ActionRequest]:
        """Récupère les actions en attente de confirmation"""
        self._cleanup_expired(tenant_id)
        tenant_actions = self._pending.get(tenant_id, {})
        return [
            r for r in tenant_actions.values()
            if r.is_pending()
        ]

    def get_action(self, tenant_id: int, action_id: str) -> Optional[ActionRequest]:
        """Récupère une action par son ID"""
        return self._pending.get(tenant_id, {}).get(action_id)

    def cleanup_expired(self, tenant_id: Optional[int] = None) -> int:
        """
        Nettoie les actions expirées.

        Args:
            tenant_id: Si spécifié, nettoie uniquement ce tenant

        Returns:
            Nombre d'actions expirées
        """
        expired_count = 0
        tenants = [tenant_id] if tenant_id else list(self._pending.keys())

        for tid in tenants:
            expired_count += self._cleanup_expired(tid)

        return expired_count

    def build_confirmation_prompt(self, request: ActionRequest) -> str:
        """
        Construit le message que Luna dira pour demander confirmation.

        Args:
            request: La demande d'action

        Returns:
            Texte de confirmation à dire par Luna
        """
        if request.action_type == ActionType.SEND_SMS:
            if request.message_body:
                preview = request.message_body[:60]
                if len(request.message_body) > 60:
                    preview += "..."
                return (
                    f"Souhaitez-vous que j'envoie un SMS à {request.target} "
                    f'disant : "{preview}" ?'
                )
            return f"Souhaitez-vous que j'envoie un SMS à {request.target} ?"

        elif request.action_type == ActionType.CALL:
            return f"Souhaitez-vous que j'appelle {request.target} ?"

        elif request.action_type == ActionType.ALERT_CONTACTS:
            return (
                "Souhaitez-vous que j'alerte vos contacts de confiance ? "
                "Ils recevront un SMS les informant de la situation."
            )

        elif request.action_type == ActionType.START_VISIO:
            return f"Souhaitez-vous démarrer un appel vidéo avec {request.target} ?"

        return f"Souhaitez-vous que je {request.description} ?"

    def build_completion_message(
        self,
        request: ActionRequest,
        success: bool,
        error: Optional[str] = None,
    ) -> str:
        """
        Construit le message que Luna dira après exécution.

        Args:
            request: La demande d'action
            success: Si l'action a réussi
            error: Message d'erreur si échec

        Returns:
            Texte de résultat à dire par Luna
        """
        if success:
            if request.action_type == ActionType.SEND_SMS:
                return f"C'est fait, j'ai envoyé le SMS à {request.target}."
            elif request.action_type == ActionType.ALERT_CONTACTS:
                return "Vos contacts de confiance ont été alertés."
            elif request.action_type == ActionType.CALL:
                return f"L'appel vers {request.target} est lancé."
            return f"L'action a été effectuée : {request.description}."
        else:
            if error and "quota" in error.lower():
                return (
                    "Je suis désolée, votre quota de SMS pour ce mois est atteint. "
                    "L'envoi n'a pas pu être effectué."
                )
            return (
                f"Je n'ai pas pu {request.description}. "
                "Souhaitez-vous que je réessaie ?"
            )

    # =========================================================================
    # MÉTHODES INTERNES
    # =========================================================================

    def _get_pending(
        self, tenant_id: int, action_id: str
    ) -> Optional[ActionRequest]:
        """Récupère une action depuis le cache"""
        return self._pending.get(tenant_id, {}).get(action_id)

    def _cleanup_expired(self, tenant_id: int) -> int:
        """Nettoie les actions expirées d'un tenant"""
        expired_count = 0
        tenant_actions = self._pending.get(tenant_id, {})

        for action_id, request in list(tenant_actions.items()):
            if request.is_pending() and request.is_expired():
                request.status = ActionStatus.EXPIRED
                self._log_event(request, "expired", "Action expirée")
                expired_count += 1

        return expired_count

    def _log_event(
        self,
        request: ActionRequest,
        event: str,
        description: str,
    ) -> None:
        """Log un événement d'action pour audit"""
        log = ActionLog(
            tenant_id=request.tenant_id,
            action_id=request.action_id,
            action_type=request.action_type,
            event=event,
            description=description,
            details={
                "target": request.target,
                "source": request.source,
                "instruction_id": request.instruction_id,
            },
            source=request.source,
        )

        # Stocke dans Redis si disponible
        if self.memory:
            try:
                self.memory.add_note(
                    content=f"Action [{event}]: {description}",
                    context="action_log",
                    source="confirmation_manager",
                    tags=["action", event, request.action_type.value],
                )
            except Exception as e:
                logger.warning(f"Could not log action to memory: {e}")

        logger.debug(f"Action log: {log.to_dict()}")
