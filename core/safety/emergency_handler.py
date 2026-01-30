"""
Luna Emergency Handler - Gestion des situations d'urgence

Gère les alertes aux contacts de confiance et les situations critiques.

IMPORTANT LÉGAL:
Luna (en tant que programme informatique) n'a PAS le droit d'appeler
directement les services d'urgence (15, 17, 18, 112).

Luna peut UNIQUEMENT:
1. Suggérer fortement au souscripteur d'appeler les secours
2. Alerter les contacts de confiance par SMS
3. Recommander aux contacts de confiance d'appeler les secours

C'est aux HUMAINS (souscripteur ou contacts de confiance) de décider
d'appeler les secours.
"""
import logging
from typing import List, Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class EmergencyType(str, Enum):
    """Types d'urgence"""
    MEDICAL = "medical"  # Urgence médicale
    SAFETY = "safety"  # Sécurité (violence, intrusion)
    DISTRESS = "distress"  # Détresse psychologique
    SUICIDE_RISK = "suicide_risk"  # Risque suicidaire
    ABUSE = "abuse"  # Maltraitance
    FALL = "fall"  # Chute
    NO_RESPONSE = "no_response"  # Pas de réponse prolongée
    CUSTOM = "custom"  # Autre


class EmergencyLevel(str, Enum):
    """Niveau d'urgence"""
    INFO = "info"  # Information, pas d'action urgente
    WARNING = "warning"  # Attention, surveillance
    ALERT = "alert"  # Alerte, contacter les proches
    CRITICAL = "critical"  # Critique, appeler les secours


class AlertChannel(str, Enum):
    """Canal d'alerte"""
    SMS = "sms"
    CALL = "call"
    APP_NOTIFICATION = "app_notification"
    EMAIL = "email"


@dataclass
class EmergencyAction:
    """Action à entreprendre en cas d'urgence"""
    action_type: str  # "alert_contact", "suggest_service", "call_emergency"
    target: str  # Numéro, service, ou contact
    message: str
    priority: int = 1  # 1 = haute priorité
    executed: bool = False
    executed_at: Optional[datetime] = None
    result: Optional[str] = None


@dataclass
class EmergencyEvent:
    """Événement d'urgence"""
    id: str
    tenant_id: int
    emergency_type: EmergencyType
    level: EmergencyLevel
    description: str
    detected_at: datetime = field(default_factory=datetime.utcnow)
    source: str = "content_filter"  # Qui a détecté: content_filter, user_report, inactivity
    context: Dict[str, Any] = field(default_factory=dict)
    actions: List[EmergencyAction] = field(default_factory=list)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None


class EmergencyHandler:
    """
    Gestionnaire d'urgences pour Luna.
    Coordonne les alertes et les actions en cas de situation critique.
    """

    # Messages d'alerte par type d'urgence
    # IMPORTANT: Luna suggère aux contacts d'appeler les secours, elle ne les appelle JAMAIS elle-même
    ALERT_MESSAGES = {
        EmergencyType.MEDICAL: (
            "ALERTE LUNA - {subscriber_name} pourrait avoir besoin d'aide médicale. "
            "Détails: {description}. "
            "Merci de le/la contacter et d'appeler le 15 (SAMU) si nécessaire."
        ),
        EmergencyType.SAFETY: (
            "ALERTE LUNA - Situation préoccupante concernant {subscriber_name}. "
            "Détails: {description}. "
            "Merci de prendre contact rapidement. En cas de danger, appelez le 17."
        ),
        EmergencyType.DISTRESS: (
            "ALERTE LUNA - {subscriber_name} semble en détresse. "
            "{description}. Un appel de votre part serait bienvenu."
        ),
        EmergencyType.SUICIDE_RISK: (
            "ALERTE URGENTE LUNA - {subscriber_name} a exprimé des pensées très préoccupantes. "
            "Merci de le/la contacter IMMÉDIATEMENT. "
            "Si vous ne pouvez pas le/la joindre, appelez le 15 ou le 3114."
        ),
        EmergencyType.ABUSE: (
            "ALERTE LUNA - Situation préoccupante signalée par {subscriber_name}. "
            "{description}. Merci de prendre contact. "
            "Si situation grave, appelez le 3977 ou le 17."
        ),
        EmergencyType.FALL: (
            "ALERTE LUNA - {subscriber_name} a signalé une chute. "
            "Merci de vérifier son état. Si blessure grave, appelez le 15."
        ),
        EmergencyType.NO_RESPONSE: (
            "ALERTE LUNA - {subscriber_name} ne répond pas depuis {duration}. "
            "Merci de vérifier que tout va bien. En cas d'inquiétude, appelez le 15."
        ),
        EmergencyType.CUSTOM: (
            "ALERTE LUNA - {subscriber_name}: {description}"
        ),
    }

    # Services d'urgence par type
    EMERGENCY_SERVICES = {
        EmergencyType.MEDICAL: {"numero": "15", "nom": "SAMU"},
        EmergencyType.SAFETY: {"numero": "17", "nom": "Police"},
        EmergencyType.SUICIDE_RISK: {"numero": "3114", "nom": "Prévention suicide"},
        EmergencyType.ABUSE: {"numero": "3977", "nom": "Maltraitance"},
        EmergencyType.FALL: {"numero": "15", "nom": "SAMU"},
    }

    def __init__(self, memory_manager=None, sms_service=None):
        """
        Args:
            memory_manager: MemoryManager pour accéder aux contacts de confiance
            sms_service: Service SMS pour envoyer les alertes
        """
        self.memory = memory_manager
        self.sms = sms_service
        self._pending_events: Dict[str, EmergencyEvent] = {}

    def create_emergency(
        self,
        tenant_id: int,
        emergency_type: EmergencyType,
        description: str,
        level: EmergencyLevel = EmergencyLevel.ALERT,
        source: str = "content_filter",
        context: Optional[Dict[str, Any]] = None,
    ) -> EmergencyEvent:
        """
        Crée un événement d'urgence.

        Args:
            tenant_id: ID du tenant/souscripteur
            emergency_type: Type d'urgence
            description: Description de la situation
            level: Niveau d'urgence
            source: Source de détection
            context: Contexte additionnel

        Returns:
            EmergencyEvent créé
        """
        import uuid

        event = EmergencyEvent(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            emergency_type=emergency_type,
            level=level,
            description=description,
            source=source,
            context=context or {},
        )

        # Détermine les actions à entreprendre
        event.actions = self._determine_actions(event)

        # Stocke l'événement en attente
        self._pending_events[event.id] = event

        logger.warning(
            f"Emergency created: {event.id} - {emergency_type.value} - {level.value} "
            f"for tenant {tenant_id}"
        )

        return event

    def _determine_actions(self, event: EmergencyEvent) -> List[EmergencyAction]:
        """Détermine les actions à entreprendre pour une urgence"""
        actions = []

        # Selon le niveau d'urgence
        if event.level == EmergencyLevel.CRITICAL:
            # Suggérer d'appeler les secours
            service = self.EMERGENCY_SERVICES.get(event.emergency_type)
            if service:
                actions.append(EmergencyAction(
                    action_type="suggest_emergency_call",
                    target=service["numero"],
                    message=f"Appelez le {service['numero']} ({service['nom']})",
                    priority=1,
                ))

            # Alerter TOUS les contacts de confiance
            actions.append(EmergencyAction(
                action_type="alert_all_contacts",
                target="all",
                message=self._format_alert_message(event),
                priority=2,
            ))

        elif event.level == EmergencyLevel.ALERT:
            # Alerter les contacts de confiance (pas urgence vitale)
            actions.append(EmergencyAction(
                action_type="alert_contacts",
                target="primary",  # Contact principal d'abord
                message=self._format_alert_message(event),
                priority=1,
            ))

        elif event.level == EmergencyLevel.WARNING:
            # Notification dans l'app, pas d'alerte SMS
            actions.append(EmergencyAction(
                action_type="notify_app",
                target="subscriber",
                message="Luna a détecté une situation qui mérite attention.",
                priority=1,
            ))

        return actions

    def _format_alert_message(
        self,
        event: EmergencyEvent,
        subscriber_name: str = "votre proche",
    ) -> str:
        """Formate le message d'alerte"""
        template = self.ALERT_MESSAGES.get(
            event.emergency_type,
            self.ALERT_MESSAGES[EmergencyType.CUSTOM]
        )

        return template.format(
            subscriber_name=subscriber_name,
            description=event.description,
            duration=event.context.get("duration", "un moment"),
        )

    async def execute_emergency_actions(
        self,
        event: EmergencyEvent,
        subscriber_name: str = "votre proche",
    ) -> List[Dict[str, Any]]:
        """
        Exécute les actions d'urgence.

        Args:
            event: L'événement d'urgence
            subscriber_name: Nom du souscripteur pour les messages

        Returns:
            Liste des résultats d'exécution
        """
        results = []

        if not self.memory:
            logger.error("Cannot execute emergency actions: no memory manager")
            return results

        # Récupère les contacts de confiance
        contacts = self.memory.list_trusted_contacts()
        if not contacts:
            logger.warning(f"No trusted contacts for tenant {event.tenant_id}")
            return results

        for action in event.actions:
            if action.executed:
                continue

            result = {"action": action.action_type, "success": False, "details": ""}

            try:
                if action.action_type in ("alert_all_contacts", "alert_contacts"):
                    # Envoie des SMS aux contacts
                    message = self._format_alert_message(event, subscriber_name)

                    contacts_to_alert = contacts
                    if action.action_type == "alert_contacts":
                        # Seulement le premier contact
                        contacts_to_alert = contacts[:1]

                    for contact in contacts_to_alert:
                        # Vérifie les heures calmes (si configuré)
                        if self._is_quiet_hours(contact) and event.level != EmergencyLevel.CRITICAL:
                            logger.info(f"Skipping {contact.phone} - quiet hours")
                            continue

                        if self.sms:
                            try:
                                # Envoie le SMS
                                sms_result = self.sms.send_sms(
                                    tenant_id=event.tenant_id,
                                    to_number=contact.phone,
                                    body=message,
                                    skip_quota_check=True,  # Alertes ignorent les quotas
                                )
                                result["details"] += f"SMS sent to {contact.name}. "
                            except Exception as e:
                                result["details"] += f"Failed to SMS {contact.name}: {e}. "
                        else:
                            result["details"] += f"Would SMS {contact.name} (no SMS service). "

                    result["success"] = True

                elif action.action_type == "suggest_emergency_call":
                    # On ne fait que suggérer, on n'appelle pas automatiquement
                    result["success"] = True
                    result["details"] = f"Suggested calling {action.target}"

                elif action.action_type == "notify_app":
                    # Notification dans l'app (via WebSocket si disponible)
                    result["success"] = True
                    result["details"] = "App notification queued"

                action.executed = True
                action.executed_at = datetime.utcnow()
                action.result = result["details"]

            except Exception as e:
                logger.exception(f"Error executing action {action.action_type}")
                result["error"] = str(e)

            results.append(result)

        return results

    def _is_quiet_hours(self, contact) -> bool:
        """Vérifie si on est dans les heures calmes du contact"""
        if not contact.quiet_hours_start or not contact.quiet_hours_end:
            return False

        from datetime import datetime
        now = datetime.now().time()

        try:
            start = datetime.strptime(contact.quiet_hours_start, "%H:%M").time()
            end = datetime.strptime(contact.quiet_hours_end, "%H:%M").time()

            if start <= end:
                return start <= now <= end
            else:
                # Cas où les heures calmes passent minuit (ex: 22:00 - 07:00)
                return now >= start or now <= end
        except ValueError:
            return False

    def resolve_emergency(
        self,
        event_id: str,
        resolution_notes: str = "",
    ) -> Optional[EmergencyEvent]:
        """
        Marque une urgence comme résolue.

        Args:
            event_id: ID de l'événement
            resolution_notes: Notes de résolution

        Returns:
            L'événement mis à jour ou None si non trouvé
        """
        event = self._pending_events.get(event_id)
        if not event:
            return None

        event.resolved = True
        event.resolved_at = datetime.utcnow()
        event.resolution_notes = resolution_notes

        logger.info(f"Emergency {event_id} resolved: {resolution_notes}")

        return event

    def get_pending_emergencies(self, tenant_id: int) -> List[EmergencyEvent]:
        """Récupère les urgences non résolues pour un tenant"""
        return [
            e for e in self._pending_events.values()
            if e.tenant_id == tenant_id and not e.resolved
        ]

    def get_suggested_response(
        self,
        emergency_type: EmergencyType,
        level: EmergencyLevel,
    ) -> str:
        """
        Retourne une réponse suggérée pour Luna selon le type d'urgence.

        IMPORTANT: Luna ne peut PAS appeler les secours elle-même.
        Elle suggère au souscripteur d'appeler et/ou alerte les contacts de confiance.
        """
        responses = {
            (EmergencyType.SUICIDE_RISK, EmergencyLevel.CRITICAL): (
                "Je vous entends et je suis très inquiète pour vous. "
                "Votre vie compte. Je vous encourage vraiment à appeler le 3114, "
                "où des personnes formées peuvent vous écouter 24h/24. "
                "Puis-je prévenir quelqu'un de confiance pour vous ?"
            ),
            (EmergencyType.MEDICAL, EmergencyLevel.CRITICAL): (
                "Cela semble être une urgence médicale. "
                "Je vous recommande fortement d'appeler le 15 (SAMU) immédiatement. "
                "Voulez-vous que je prévienne vos proches pour qu'ils puissent vous aider ?"
            ),
            (EmergencyType.ABUSE, EmergencyLevel.ALERT): (
                "Ce que vous décrivez me préoccupe beaucoup. "
                "Personne ne devrait subir cela. "
                "Le 3977 peut vous aider et vous conseiller. "
                "Je suis là pour vous écouter si vous voulez en parler."
            ),
            (EmergencyType.DISTRESS, EmergencyLevel.ALERT): (
                "Je comprends que vous traversez un moment difficile. "
                "Voulez-vous m'en dire plus ? "
                "Ou préférez-vous que je contacte quelqu'un de confiance ?"
            ),
            (EmergencyType.FALL, EmergencyLevel.ALERT): (
                "Vous avez fait une chute ? "
                "Avez-vous mal quelque part ? "
                "Si vous ne pouvez pas vous relever ou si vous avez mal, "
                "je vous conseille d'appeler le 15 ou de demander à un proche de le faire. "
                "Voulez-vous que je prévienne vos contacts de confiance ?"
            ),
        }

        return responses.get(
            (emergency_type, level),
            "Je suis là pour vous. Comment puis-je vous aider ?"
        )
