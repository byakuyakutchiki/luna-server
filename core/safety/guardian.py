"""
Luna Safety Guardian - Gardien principal de sécurité

Coordonne tous les aspects de sécurité:
- Filtrage de contenu
- Connaissances légales
- Gestion des urgences
- Alertes aux contacts
"""
import logging
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

from .content_filter import ContentFilter, ContentCategory, FilterResult, RiskLevel
from .legal_knowledge import LegalKnowledge, LegalDomain
from .emergency_handler import EmergencyHandler, EmergencyType, EmergencyLevel, EmergencyEvent

logger = logging.getLogger(__name__)


class SafetyLevel(str, Enum):
    """Niveau de sécurité global"""
    OK = "ok"  # Tout va bien
    CAUTION = "caution"  # Attention requise
    WARNING = "warning"  # Avertissement, intervention Luna
    ALERT = "alert"  # Alerte, contacter les proches
    CRITICAL = "critical"  # Critique, urgence vitale


@dataclass
class SafetyCheck:
    """Résultat d'une vérification de sécurité"""
    level: SafetyLevel
    category: ContentCategory
    requires_intervention: bool
    luna_response: Optional[str]  # Réponse suggérée pour Luna
    alert_contacts: bool
    block_action: bool
    legal_domain: Optional[LegalDomain]
    services_to_suggest: List[str]
    emergency_event: Optional[EmergencyEvent]


class SafetyGuardian:
    """
    Gardien de sécurité principal pour Luna.

    Responsabilités:
    1. Vérifier chaque message/demande avant traitement
    2. Détecter les situations dangereuses
    3. Appliquer les limites légales
    4. Déclencher les alertes si nécessaire
    5. Fournir des réponses appropriées à Luna
    """

    # Mapping entre catégories de contenu et domaines légaux
    CATEGORY_TO_LEGAL_DOMAIN = {
        # MEDICAL_ADVICE retiré (risque juridique)
        ContentCategory.LEGAL_ADVICE: LegalDomain.PROTECTION_PERSONNES,
        ContentCategory.ABUSE: LegalDomain.ABUS_MALTRAITANCE,
        ContentCategory.SUICIDE_RISK: LegalDomain.PROTECTION_PERSONNES,
        ContentCategory.EMERGENCY: LegalDomain.URGENCES,
        ContentCategory.PERSONAL_DATA: LegalDomain.PROTECTION_DONNEES,
    }

    # Mapping entre catégories et types d'urgence
    CATEGORY_TO_EMERGENCY = {
        ContentCategory.SUICIDE_RISK: EmergencyType.SUICIDE_RISK,
        ContentCategory.EMERGENCY: EmergencyType.SAFETY,  # Urgence générale, pas médical
        ContentCategory.ABUSE: EmergencyType.ABUSE,
        ContentCategory.DISTRESS: EmergencyType.DISTRESS,
    }

    # Mots/expressions interdits dans les reponses Luna (legal compliance)
    FORBIDDEN_PROMISES = [
        "je surveille", "je garantis", "je protege", "sous surveillance",
        "systeme de securite", "dispositif medical", "je diagnostique",
        "diagnostic", "je vous assure que rien", "surveillance garantie",
        "protection assuree", "detection certaine",
    ]

    def __init__(
        self,
        tenant_id: int,
        memory_manager=None,
        sms_service=None,
        legal_mode: str = "assistance_only",
    ):
        """
        Args:
            tenant_id: ID du tenant/souscripteur
            memory_manager: MemoryManager pour accéder aux données
            sms_service: Service SMS pour les alertes
            legal_mode: Mode legal (assistance_only par defaut)
        """
        self.tenant_id = tenant_id
        self.memory = memory_manager
        self.legal_mode = legal_mode
        self.emergency_handler = EmergencyHandler(memory_manager, sms_service)

    def check(self, text: str, context: Optional[Dict[str, Any]] = None) -> SafetyCheck:
        """
        Vérifie un texte (message ou demande) et retourne le résultat de sécurité.

        Args:
            text: Le texte à vérifier
            context: Contexte optionnel (conversation_id, channel, etc.)

        Returns:
            SafetyCheck avec toutes les informations nécessaires
        """
        context = context or {}

        # 1. Analyse du contenu
        filter_result = ContentFilter.analyze(text)

        # 2. Détermine le domaine légal si applicable
        legal_domain = self.CATEGORY_TO_LEGAL_DOMAIN.get(filter_result.category)

        # 3. Détermine le niveau de sécurité global
        safety_level = self._risk_to_safety_level(filter_result.risk_level)

        # 4. Prépare les services à suggérer
        services = []
        if legal_domain:
            services = [
                f"{s.nom} ({s.numero})" if s.numero else s.nom
                for s in LegalKnowledge.get_relevant_services(legal_domain)
            ]

        # 5. Crée un événement d'urgence si nécessaire
        emergency_event = None
        if filter_result.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            emergency_type = self.CATEGORY_TO_EMERGENCY.get(
                filter_result.category,
                EmergencyType.CUSTOM
            )
            emergency_level = (
                EmergencyLevel.CRITICAL
                if filter_result.risk_level == RiskLevel.CRITICAL
                else EmergencyLevel.ALERT
            )
            emergency_event = self.emergency_handler.create_emergency(
                tenant_id=self.tenant_id,
                emergency_type=emergency_type,
                description=f"Détecté: {filter_result.category.value}",
                level=emergency_level,
                source="safety_guardian",
                context={"text_preview": text[:100], **context},
            )

        # 6. Détermine la réponse Luna
        luna_response = self._build_luna_response(filter_result, legal_domain, services)

        return SafetyCheck(
            level=safety_level,
            category=filter_result.category,
            requires_intervention=filter_result.requires_action,
            luna_response=luna_response,
            alert_contacts=filter_result.alert_contacts,
            block_action=filter_result.block_request,
            legal_domain=legal_domain,
            services_to_suggest=services,
            emergency_event=emergency_event,
        )

    def _risk_to_safety_level(self, risk: RiskLevel) -> SafetyLevel:
        """Convertit un niveau de risque en niveau de sécurité"""
        mapping = {
            RiskLevel.NONE: SafetyLevel.OK,
            RiskLevel.LOW: SafetyLevel.CAUTION,
            RiskLevel.MEDIUM: SafetyLevel.WARNING,
            RiskLevel.HIGH: SafetyLevel.ALERT,
            RiskLevel.CRITICAL: SafetyLevel.CRITICAL,
        }
        return mapping.get(risk, SafetyLevel.OK)

    def _build_luna_response(
        self,
        filter_result: FilterResult,
        legal_domain: Optional[LegalDomain],
        services: List[str],
    ) -> Optional[str]:
        """Construit la réponse appropriée pour Luna"""
        # Si le filtre a déjà une réponse suggérée, l'utiliser
        if filter_result.suggested_response:
            return filter_result.suggested_response

        # Sinon, construire selon le domaine légal
        if legal_domain:
            return LegalKnowledge.get_refusal_message(legal_domain)

        # Cas par défaut selon la catégorie
        if filter_result.category == ContentCategory.MANIPULATION:
            return (
                "Je comprends votre demande, mais je dois respecter certaines règles "
                "pour votre sécurité. Comment puis-je vous aider autrement ?"
            )

        return None

    async def process_and_respond(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
        auto_alert: bool = True,
    ) -> Tuple[SafetyCheck, bool]:
        """
        Traite un message et exécute les actions de sécurité si nécessaire.

        Args:
            text: Le texte à traiter
            context: Contexte optionnel
            auto_alert: Si True, envoie automatiquement les alertes

        Returns:
            Tuple (SafetyCheck, actions_executed)
        """
        check = self.check(text, context)

        actions_executed = False

        # Si une alerte est nécessaire et auto_alert est activé
        if check.alert_contacts and auto_alert and check.emergency_event:
            subscriber_name = "votre proche"
            if self.memory:
                # Essaie de récupérer le nom du souscripteur
                # (serait dans un profil utilisateur)
                pass

            results = await self.emergency_handler.execute_emergency_actions(
                check.emergency_event,
                subscriber_name=subscriber_name,
            )
            actions_executed = len(results) > 0

            logger.info(
                f"Safety actions executed for tenant {self.tenant_id}: "
                f"{len(results)} actions"
            )

        return check, actions_executed

    def can_proceed(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Vérifie rapidement si une action peut être effectuée.

        Args:
            text: Le texte/demande à vérifier

        Returns:
            Tuple (peut_procéder, message_si_bloqué)
        """
        check = self.check(text)

        if check.block_action:
            return False, check.luna_response

        return True, None

    def check_legal_compliance(self, text: str) -> Tuple[bool, List[str]]:
        """
        Verifie qu'un texte (reponse Luna) ne contient pas de promesses interdites.

        Returns:
            Tuple (is_compliant, list of violations found)
        """
        text_lower = text.lower()
        violations = [
            phrase for phrase in self.FORBIDDEN_PROMISES
            if phrase in text_lower
        ]
        if violations:
            logger.warning(
                f"Legal compliance violation for tenant {self.tenant_id}: {violations}"
            )
        return len(violations) == 0, violations

    def get_safety_context_for_luna(self) -> Dict[str, Any]:
        """
        Retourne un contexte de sécurité à inclure dans le prompt de Luna.

        Ce contexte rappelle à Luna ses limites et responsabilités.
        """
        return {
            "role": "safety_context",
            "content": f"""
MODE LEGAL: {self.legal_mode}
Luna est une aide contextuelle bienveillante, PAS un service de securite.
Elle ne promet JAMAIS de resultat, de protection ou de surveillance garantie.

RAPPEL DE SÉCURITÉ POUR LUNA:

1. JE NE SUIS PAS un professionnel de santé, juridique ou financier.
   → Je conseille de consulter les experts appropriés.

2. RESTRICTION LÉGALE IMPORTANTE:
   Je n'ai PAS LE DROIT d'appeler les services d'urgence moi-même.
   Je peux UNIQUEMENT:
   - Suggérer fortement au souscripteur d'appeler les secours
   - Alerter les contacts de confiance par SMS
   - Recommander aux contacts d'appeler les secours si nécessaire

3. NUMÉROS D'URGENCE (à suggérer, jamais appeler):
   - SAMU: 15 (urgences médicales)
   - Police: 17 (sécurité)
   - Pompiers: 18
   - Européen: 112
   - Suicide: 3114
   - Maltraitance: 3977

4. JE DOIS ALERTER les contacts de confiance si:
   - Risque pour la sécurité du souscripteur
   - Signes de détresse importante
   - Propos préoccupants (suicide, violence)
   - Absence de réponse prolongée anormale

5. JE NE DOIS JAMAIS:
   - Appeler les secours directement (interdit légalement)
   - Donner de conseils médicaux
   - Aider à des actions illégales
   - Ignorer des signes de danger
   - Promettre le secret sur une situation grave

6. JE DOIS TOUJOURS:
   - Écouter avec bienveillance
   - Suggérer d'appeler les services appropriés
   - Alerter les contacts de confiance (qui peuvent appeler les secours)
   - Demander confirmation avant d'alerter (sauf urgence vitale)
   - Respecter la dignité de la personne
""",
        }

    def get_emergency_numbers_prompt(self) -> str:
        """Retourne les numéros d'urgence formatés pour Luna"""
        return LegalKnowledge.format_emergency_info()

    def log_safety_event(
        self,
        event_type: str,
        details: Dict[str, Any],
    ) -> None:
        """
        Log un événement de sécurité pour audit.

        Args:
            event_type: Type d'événement (check, alert, block, etc.)
            details: Détails de l'événement
        """
        logger.info(
            f"Safety event [{event_type}] for tenant {self.tenant_id}: {details}"
        )

        # Si un memory manager est disponible, on pourrait aussi
        # stocker dans Redis pour historique
        if self.memory:
            try:
                self.memory.add_note(
                    content=f"Événement sécurité: {event_type}",
                    context="safety",
                    source="safety_guardian",
                    tags=["sécurité", event_type],
                )
            except Exception as e:
                logger.warning(f"Could not log safety event to memory: {e}")


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_safety_guardian(
    tenant_id: int,
    memory_manager=None,
    sms_service=None,
) -> SafetyGuardian:
    """
    Factory pour créer un SafetyGuardian configuré.

    Args:
        tenant_id: ID du tenant
        memory_manager: MemoryManager optionnel
        sms_service: Service SMS optionnel

    Returns:
        SafetyGuardian configuré
    """
    return SafetyGuardian(
        tenant_id=tenant_id,
        memory_manager=memory_manager,
        sms_service=sms_service,
    )
