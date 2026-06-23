"""
Luna Action Dispatcher - Exécution des actions confirmées

Responsable de:
- Router les actions vers les bons services
- Vérifier les quotas avant exécution
- Exécuter et retourner le résultat
- Gérer les erreurs et retries

IMPORTANT:
- Ne JAMAIS exécuter sans confirmation préalable
- Toujours vérifier le quota avant envoi
- Logger chaque action pour traçabilité
"""
import asyncio
import logging
from typing import Optional, Dict, Any, Tuple

from .models import ActionRequest, ActionResult, ActionStatus, ActionType
from .confirmation import ConfirmationManager
from .quota_guard import QuotaGuard, QuotaStatus

logger = logging.getLogger(__name__)


class ActionDispatcher:
    """
    Dispatche et exécute les actions confirmées.

    Flow:
    1. Vérifie que l'action est confirmée
    2. Vérifie le quota
    3. Exécute via le bon service
    4. Met à jour le statut
    5. Log le résultat
    """

    # Disclaimer ajoute aux messages d'alerte en mode assistance_only
    LEGAL_DISCLAIMER = (
        " [Ce message est une aide contextuelle, pas une alerte de securite garantie.]"
    )

    def __init__(
        self,
        confirmation_manager: ConfirmationManager,
        quota_guard: QuotaGuard,
        sms_service=None,
        memory_manager=None,
        legal_mode: str = "assistance_only",
    ):
        """
        Args:
            confirmation_manager: Gestionnaire de confirmations
            quota_guard: Garde-fou des quotas
            sms_service: Service SMS pour l'envoi
            memory_manager: Gestionnaire de mémoire
            legal_mode: Mode legal (assistance_only par defaut)
        """
        self.confirmation = confirmation_manager
        self.quota = quota_guard
        self.sms = sms_service
        self.memory = memory_manager
        self.legal_mode = legal_mode

    async def dispatch(
        self,
        request: ActionRequest,
    ) -> ActionResult:
        """
        Dispatche et exécute une action confirmée.

        Args:
            request: L'action à exécuter (doit être confirmée)

        Returns:
            ActionResult avec le résultat
        """
        # 1. Vérifie la confirmation
        if not request.confirmed and request.source not in ("emergency_critical",):
            return ActionResult(
                action_id=request.action_id,
                success=False,
                message="Action non confirmée",
                error="not_confirmed",
            )

        # 2. Vérifie le quota
        quota_status = self.quota.check(
            tenant_id=request.tenant_id,
            action_type=request.action_type,
            estimated_cost=request.estimated_cost,
        )

        if not quota_status.allowed:
            self.confirmation.mark_failed(request, "quota_exceeded")
            return ActionResult(
                action_id=request.action_id,
                success=False,
                message=quota_status.message,
                error="quota_exceeded",
                details={"quota": quota_status.to_dict()},
            )

        # 3. Avertissement quota si nécessaire
        quota_warning = None
        if quota_status.should_warn:
            quota_warning = quota_status.warning_message

        # 4. Exécute l'action
        self.confirmation.mark_executing(request)

        try:
            result = await self._execute(request)

            # 5. Met à jour le quota
            if result.success:
                self.quota.increment(
                    tenant_id=request.tenant_id,
                    action_type=request.action_type,
                    cost=request.estimated_cost,
                )
                self.confirmation.mark_completed(request, result.message)

                # Ajoute l'avertissement quota au résultat
                if quota_warning:
                    result.details["quota_warning"] = quota_warning
            else:
                self.confirmation.mark_failed(request, result.error or "unknown")

            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Action dispatch failed [{request.action_id}]: {error_msg}")
            self.confirmation.mark_failed(request, error_msg)
            return ActionResult(
                action_id=request.action_id,
                success=False,
                message="Une erreur s'est produite",
                error=error_msg,
            )

    async def dispatch_with_retry(
        self,
        request: ActionRequest,
        max_retries: int = 2,
    ) -> ActionResult:
        """
        Dispatche avec retry automatique en cas d'échec.

        Args:
            request: L'action à exécuter
            max_retries: Nombre max de tentatives

        Returns:
            ActionResult du dernier essai
        """
        last_result = None

        for attempt in range(max_retries + 1):
            result = await self.dispatch(request)

            if result.success:
                return result

            last_result = result

            # Ne pas retry pour certaines erreurs
            if result.error in ("not_confirmed", "quota_exceeded", "no_sms_service"):
                return result

            logger.warning(
                f"Action retry [{request.action_id}]: "
                f"attempt {attempt + 1}/{max_retries + 1}"
            )

        return last_result

    async def _execute(self, request: ActionRequest) -> ActionResult:
        """Route et exécute l'action selon son type"""
        handlers = {
            ActionType.SEND_SMS: self._execute_sms,
            ActionType.CALL: self._execute_call,
            ActionType.ALERT_CONTACTS: self._execute_alert_contacts,
            ActionType.START_VISIO: self._execute_visio,
        }

        handler = handlers.get(request.action_type)
        if not handler:
            return ActionResult(
                action_id=request.action_id,
                success=False,
                message=f"Type d'action non supporté: {request.action_type.value}",
                error="unsupported_action",
            )

        return await handler(request)

    # =========================================================================
    # HANDLERS D'EXÉCUTION
    # =========================================================================

    async def _execute_sms(self, request: ActionRequest) -> ActionResult:
        """Exécute l'envoi d'un SMS"""
        if not self.sms:
            return ActionResult(
                action_id=request.action_id,
                success=False,
                message="Service SMS non disponible",
                error="no_sms_service",
            )

        phone = request.target_phone
        if not phone:
            # Essaie de résoudre le numéro
            phone = await self._resolve_phone(request.tenant_id, request.target)

        if not phone:
            return ActionResult(
                action_id=request.action_id,
                success=False,
                message=f"Numéro de {request.target} non trouvé",
                error="contact_not_found",
            )

        body = request.message_body or ""
        if not body:
            return ActionResult(
                action_id=request.action_id,
                success=False,
                message="Aucun contenu de message",
                error="empty_message",
            )

        # Envoi via le service SMS
        try:
            success, result = await asyncio.to_thread(self.sms.send, phone, body)

            if success:
                return ActionResult(
                    action_id=request.action_id,
                    success=True,
                    message=f"SMS envoyé à {request.target}",
                    details={
                        "recipient": request.target,
                        "phone": phone,
                        "segments": result.get("segments", 1),
                        "sid": result.get("sid"),
                    },
                )
            else:
                return ActionResult(
                    action_id=request.action_id,
                    success=False,
                    message=f"Échec de l'envoi à {request.target}",
                    error=result.get("error", "sms_send_failed"),
                )
        except Exception as e:
            return ActionResult(
                action_id=request.action_id,
                success=False,
                message="Erreur lors de l'envoi du SMS",
                error=str(e),
            )

    async def _execute_call(self, request: ActionRequest) -> ActionResult:
        """Exécute un appel téléphonique (future fonctionnalité)"""
        return ActionResult(
            action_id=request.action_id,
            success=False,
            message="Les appels téléphoniques seront disponibles prochainement",
            error="feature_not_available",
        )

    async def _execute_alert_contacts(self, request: ActionRequest) -> ActionResult:
        """
        Alerte tous les contacts de confiance par SMS.

        IMPORTANT:
        - Luna n'appelle JAMAIS les services d'urgence directement
        - Le message suggère aux contacts d'appeler les secours si nécessaire
        """
        if not self.sms:
            return ActionResult(
                action_id=request.action_id,
                success=False,
                message="Service SMS non disponible",
                error="no_sms_service",
            )

        # Récupère les contacts de confiance
        contacts = await self._get_trusted_contacts(request.tenant_id)
        if not contacts:
            return ActionResult(
                action_id=request.action_id,
                success=False,
                message="Aucun contact de confiance configuré",
                error="no_trusted_contacts",
            )

        alert_body = request.message_body or (
            "[YAWatch Luna] Alerte concernant votre proche. "
            "Pourriez-vous vérifier qu'il va bien ? "
            "Si vous êtes inquiet, nous vous recommandons fortement "
            "d'appeler les secours."
        )

        # En mode assistance_only, ajouter le disclaimer legal
        if self.legal_mode == "assistance_only":
            alert_body += self.LEGAL_DISCLAIMER

        sent = 0
        failed = []

        for contact in contacts:
            try:
                success, result = await self.sms.send_sms(
                    request.tenant_id,
                    contact["phone"],
                    alert_body,
                )
                if success:
                    sent += 1
                else:
                    failed.append(contact["name"])
            except Exception as e:
                failed.append(contact["name"])
                logger.error(f"Alert SMS to {contact['name']} failed: {e}")

        if sent > 0:
            return ActionResult(
                action_id=request.action_id,
                success=True,
                message=f"Alerte envoyée à {sent} contact(s)",
                details={
                    "contacts_alerted": sent,
                    "failed": failed if failed else None,
                },
            )
        else:
            return ActionResult(
                action_id=request.action_id,
                success=False,
                message="Impossible d'alerter les contacts",
                error="all_alerts_failed",
                details={"failed_contacts": failed},
            )

    async def _execute_visio(self, request: ActionRequest) -> ActionResult:
        """Démarre un appel vidéo (future fonctionnalité via Tavus)"""
        return ActionResult(
            action_id=request.action_id,
            success=False,
            message="Les appels vidéo seront disponibles prochainement",
            error="feature_not_available",
        )

    # =========================================================================
    # HELPERS
    # =========================================================================

    async def _resolve_phone(
        self,
        tenant_id: int,
        contact_name: str,
    ) -> Optional[str]:
        """Résout un nom de contact vers un numéro de téléphone"""
        if not self.memory:
            return None

        contacts = await self._get_trusted_contacts(tenant_id)
        name_lower = contact_name.lower()

        for contact in contacts:
            if name_lower in contact.get("name", "").lower():
                return contact.get("phone")
            if name_lower in contact.get("relation", "").lower():
                return contact.get("phone")

        return None

    async def _get_trusted_contacts(self, tenant_id: int) -> list:
        """Récupère les contacts de confiance"""
        if not self.memory:
            return []

        try:
            contacts = self.memory.list_trusted_contacts()
            return [
                {"name": c.name, "phone": c.phone, "relation": c.relation}
                for c in contacts
            ]
        except Exception as e:
            logger.warning(f"Error fetching trusted contacts: {e}")
            return []


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_action_dispatcher(
    confirmation_manager: ConfirmationManager,
    quota_guard: QuotaGuard,
    sms_service=None,
    memory_manager=None,
) -> ActionDispatcher:
    """
    Factory pour créer un ActionDispatcher configuré.

    Args:
        confirmation_manager: Gestionnaire de confirmations
        quota_guard: Garde-fou des quotas
        sms_service: Service SMS
        memory_manager: Gestionnaire de mémoire

    Returns:
        ActionDispatcher configuré
    """
    return ActionDispatcher(
        confirmation_manager=confirmation_manager,
        quota_guard=quota_guard,
        sms_service=sms_service,
        memory_manager=memory_manager,
    )
