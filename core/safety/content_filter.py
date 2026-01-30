"""
Luna Content Filter - Détection de contenu inapproprié ou dangereux

Filtre les demandes pour détecter:
- Demandes illégales
- Situations dangereuses
- Contenu inapproprié
- Signes de détresse
"""
import re
from typing import List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass


class ContentCategory(str, Enum):
    """Catégories de contenu détecté"""
    SAFE = "safe"  # Contenu normal
    MEDICAL_ADVICE = "medical_advice"  # Demande de conseil médical
    LEGAL_ADVICE = "legal_advice"  # Demande de conseil juridique
    FINANCIAL_ADVICE = "financial_advice"  # Demande de conseil financier
    DISTRESS = "distress"  # Signes de détresse
    SUICIDE_RISK = "suicide_risk"  # Risque suicidaire
    ABUSE = "abuse"  # Signes d'abus/maltraitance
    EMERGENCY = "emergency"  # Urgence vitale
    ILLEGAL_REQUEST = "illegal_request"  # Demande illégale
    VIOLENCE = "violence"  # Contenu violent
    PERSONAL_DATA = "personal_data"  # Demande de données personnelles
    MANIPULATION = "manipulation"  # Tentative de manipulation


class RiskLevel(str, Enum):
    """Niveau de risque"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FilterResult:
    """Résultat du filtrage"""
    category: ContentCategory
    risk_level: RiskLevel
    matched_patterns: List[str]
    requires_action: bool
    suggested_response: Optional[str] = None
    alert_contacts: bool = False
    block_request: bool = False


class ContentFilter:
    """
    Filtre de contenu pour Luna.
    Détecte les situations nécessitant une attention particulière.
    """

    # ========================================================================
    # PATTERNS DE DÉTECTION
    # ========================================================================

    # Patterns pour détecter les urgences vitales (non-medical, focus sécurité)
    EMERGENCY_PATTERNS = [
        r"\b(inconscient|évanoui|ne bouge plus|ne répond plus)\b",
        r"\b(chute|tombé|accident)\b.*\b(grave|tête|escalier)\b",
        r"\bappel(er|ez)?\s*(le)?\s*(15|samu|urgences?|pompiers?)\b",
    ]

    # Patterns pour détecter les signes de détresse
    DISTRESS_PATTERNS = [
        r"\b(triste|déprimé|malheureux|désespéré)\b",
        r"\b(seul|isolé|personne ne m'aime|abandonné)\b",
        r"\b(peur|angoisse|anxiété|panique)\b",
        r"\b(ne vais pas bien|ça ne va pas|mal dans ma peau)\b",
        r"\b(fatigué de vivre|ras le bol de tout|plus envie)\b",
        r"\b(pleure|pleurer|larmes)\b",
    ]

    # Patterns pour détecter les risques suicidaires (CRITIQUE)
    SUICIDE_PATTERNS = [
        r"\b(envie de mourir|veux mourir|vouloir mourir)\b",
        r"\b(me suicider|suicide|en finir)\b",
        r"\b(plus la peine|plus de raison de vivre)\b",
        r"\b(mieux sans moi|seraient mieux sans moi)\b",
        r"\b(dernière fois|derniers jours|adieu)\b",
        r"\b(médicaments|pilules|avaler)\b.*\b(tous|trop|beaucoup)\b",
    ]

    # Patterns pour détecter les abus/maltraitance
    ABUSE_PATTERNS = [
        r"\b(frappe|frappé|tape|tapé|bat|battu|violente|violenté|blesse|blessé)\b",
        r"\b(insulte|humilie|rabaisse|menace)\b",
        r"\b(enfermé|séquestré|empêche de sortir)\b",
        r"\b(vole|prend|argent|carte bancaire)\b",
        r"\b(peur de|fait peur|menacé par)\b",
        r"\b(maltraité|maltraitance|négligé|négligence)\b",
        r"\b(force|oblige|contraint)\b.*\bà\b",
        r"\bme\b.*(frappe|tape|vole|menace|insulte)\b",
    ]

    # Patterns médicaux désactivés (risque juridique trop élevé)
    # Luna redirige vers un professionnel sans analyser
    MEDICAL_ADVICE_PATTERNS = []

    # Patterns pour détecter les demandes illégales
    ILLEGAL_PATTERNS = [
        r"\b(voler|cambrioler|arnaquer|escroquer)\b",
        r"\b(faux|falsifier|contrefaire)\b.*\b(papiers?|documents?|signature)\b",
        r"\b(drogue|stupéfiant|cannabis|cocaïne)\b",
        r"\b(contourner|éviter)\b.*\b(impôts?|taxes?|loi)\b",
        r"\b(pirater|hacker|mot de passe)\b",
    ]

    # Patterns pour détecter les tentatives de manipulation de Luna
    MANIPULATION_PATTERNS = [
        r"\b(oublie|ignore)\b.*\b(règles?|limites?|instructions?)\b",
        r"\b(fais semblant|prétends?|comme si)\b",
        r"\b(personne ne saura|entre nous|secret)\b",
        r"\b(tu (dois|peux)|il faut que tu)\b.*\b(dire|faire|donner)\b",
        r"\b(accès|mot de passe|identifiants?)\b",
    ]

    # ========================================================================
    # MÉTHODES DE FILTRAGE
    # ========================================================================

    @classmethod
    def _check_patterns(cls, text: str, patterns: List[str]) -> List[str]:
        """Vérifie si le texte correspond à des patterns"""
        text_lower = text.lower()
        matched = []
        for pattern in patterns:
            if re.search(pattern, text_lower):
                matched.append(pattern)
        return matched

    @classmethod
    def analyze(cls, text: str) -> FilterResult:
        """
        Analyse un texte et retourne le résultat du filtrage.

        Args:
            text: Le texte à analyser

        Returns:
            FilterResult avec la catégorie, le niveau de risque et les actions suggérées
        """
        text_lower = text.lower()

        # 1. Vérifier les risques suicidaires (PRIORITÉ MAXIMALE)
        suicide_matches = cls._check_patterns(text, cls.SUICIDE_PATTERNS)
        if suicide_matches:
            return FilterResult(
                category=ContentCategory.SUICIDE_RISK,
                risk_level=RiskLevel.CRITICAL,
                matched_patterns=suicide_matches,
                requires_action=True,
                suggested_response=(
                    "Je sens que vous traversez un moment très difficile. "
                    "Votre vie a de la valeur. "
                    "Je vous encourage vraiment à appeler le 3114, "
                    "le numéro national de prévention du suicide, disponible 24h/24. "
                    "Des personnes formées peuvent vous écouter et vous aider. "
                    "Voulez-vous que je prévienne quelqu'un de confiance ?"
                ),
                alert_contacts=True,
                block_request=False,  # On ne bloque pas, on accompagne
            )

        # 2. Vérifier les urgences vitales (sécurité, pas diagnostic médical)
        emergency_matches = cls._check_patterns(text, cls.EMERGENCY_PATTERNS)
        if emergency_matches:
            return FilterResult(
                category=ContentCategory.EMERGENCY,
                risk_level=RiskLevel.CRITICAL,
                matched_patterns=emergency_matches,
                requires_action=True,
                suggested_response=(
                    "Ca a l'air serieux. "
                    "Je te recommande d'appeler le 15 (SAMU) ou le 112. "
                    "Tu veux que je previenne tes contacts de confiance ?"
                ),
                alert_contacts=True,
                block_request=False,
            )

        # 3. Vérifier les signes d'abus/maltraitance
        abuse_matches = cls._check_patterns(text, cls.ABUSE_PATTERNS)
        if abuse_matches:
            return FilterResult(
                category=ContentCategory.ABUSE,
                risk_level=RiskLevel.HIGH,
                matched_patterns=abuse_matches,
                requires_action=True,
                suggested_response=(
                    "Ce que vous décrivez me préoccupe. "
                    "Personne ne mérite d'être traité ainsi. "
                    "Le 3977 est le numéro pour signaler les situations de maltraitance. "
                    "Voulez-vous en parler ? Je suis là pour vous écouter."
                ),
                alert_contacts=True,
                block_request=False,
            )

        # 4. Vérifier les demandes illégales
        illegal_matches = cls._check_patterns(text, cls.ILLEGAL_PATTERNS)
        if illegal_matches:
            return FilterResult(
                category=ContentCategory.ILLEGAL_REQUEST,
                risk_level=RiskLevel.HIGH,
                matched_patterns=illegal_matches,
                requires_action=True,
                suggested_response=(
                    "Je ne peux pas vous aider avec cette demande. "
                    "Cela ne fait pas partie de ce que je suis autorisée à faire."
                ),
                alert_contacts=False,
                block_request=True,
            )

        # 5. Vérifier les tentatives de manipulation
        manipulation_matches = cls._check_patterns(text, cls.MANIPULATION_PATTERNS)
        if manipulation_matches:
            return FilterResult(
                category=ContentCategory.MANIPULATION,
                risk_level=RiskLevel.MEDIUM,
                matched_patterns=manipulation_matches,
                requires_action=True,
                suggested_response=(
                    "Je comprends votre demande, mais je dois respecter "
                    "certaines règles pour votre sécurité et la mienne. "
                    "Comment puis-je vous aider autrement ?"
                ),
                alert_contacts=False,
                block_request=True,
            )

        # 6. Vérifier les signes de détresse
        distress_matches = cls._check_patterns(text, cls.DISTRESS_PATTERNS)
        if distress_matches:
            return FilterResult(
                category=ContentCategory.DISTRESS,
                risk_level=RiskLevel.MEDIUM,
                matched_patterns=distress_matches,
                requires_action=True,
                suggested_response=(
                    "Je vous entends, et je suis là pour vous. "
                    "Voulez-vous m'en dire plus sur ce que vous ressentez ? "
                    "Ou préférez-vous que je contacte quelqu'un pour vous ?"
                ),
                alert_contacts=False,  # Pas automatique, on propose
                block_request=False,
            )

        # 7. Contenu normal (partie médicale retirée - trop de risque juridique)
        return FilterResult(
            category=ContentCategory.SAFE,
            risk_level=RiskLevel.NONE,
            matched_patterns=[],
            requires_action=False,
            suggested_response=None,
            alert_contacts=False,
            block_request=False,
        )

    @classmethod
    def is_safe(cls, text: str) -> bool:
        """Vérifie rapidement si un texte est sûr"""
        result = cls.analyze(text)
        return result.category == ContentCategory.SAFE

    @classmethod
    def requires_alert(cls, text: str) -> bool:
        """Vérifie si le texte nécessite d'alerter les contacts"""
        result = cls.analyze(text)
        return result.alert_contacts

    @classmethod
    def should_block(cls, text: str) -> bool:
        """Vérifie si la demande doit être bloquée"""
        result = cls.analyze(text)
        return result.block_request

    @classmethod
    def get_risk_level(cls, text: str) -> RiskLevel:
        """Retourne le niveau de risque d'un texte"""
        result = cls.analyze(text)
        return result.risk_level
