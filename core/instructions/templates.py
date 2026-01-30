"""
Luna Instruction Templates - Modèles d'instructions courantes

Fournit des templates prédéfinis pour les instructions les plus courantes:
- Vérifications de bien-être
- Rappels quotidiens (repas, hydratation, activités)
- Alertes programmées
- Messages récurrents aux proches

Ces templates simplifient la création d'instructions pour les utilisateurs.

NOTE: Luna n'intervient PAS dans le domaine médical.
Aucun rappel de médicaments, aucun conseil médical, aucun suivi de traitement.
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import time

from .parser import RecurrenceType, ActionType, ConditionType


class TemplateCategory(str, Enum):
    """Catégories de templates"""
    WELLBEING = "wellbeing"  # Bien-être (hydratation, repas, sommeil)
    SAFETY = "safety"  # Sécurité
    SOCIAL = "social"  # Social/Communication
    DAILY = "daily"  # Quotidien
    CUSTOM = "custom"  # Personnalisé


@dataclass
class InstructionTemplate:
    """
    Template d'instruction prédéfini.

    Un template facilite la création d'instructions courantes
    en fournissant des valeurs par défaut et des exemples.
    """
    id: str
    name: str
    description: str
    category: TemplateCategory
    action_type: ActionType
    default_recurrence: RecurrenceType
    default_time: Optional[time] = None
    default_message: Optional[str] = None
    condition: ConditionType = ConditionType.NONE
    example_phrases: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    icon: str = ""  # Emoji pour l'interface

    def generate_instruction_text(
        self,
        custom_time: Optional[str] = None,
        custom_message: Optional[str] = None,
        target_contact: Optional[str] = None,
    ) -> str:
        """
        Génère le texte d'instruction à partir du template.

        Args:
            custom_time: Heure personnalisée (ex: "8h30")
            custom_message: Message personnalisé
            target_contact: Contact cible (si applicable)

        Returns:
            Texte d'instruction formaté
        """
        time_str = custom_time or (
            f"{self.default_time.hour}h{self.default_time.minute:02d}"
            if self.default_time else ""
        )
        message = custom_message or self.default_message or ""

        # Construction selon le type d'action
        if self.action_type == ActionType.REMINDER:
            if time_str:
                return f"Rappelle-moi {message} à {time_str}"
            return f"Rappelle-moi {message}"

        elif self.action_type == ActionType.SMS_CONTACT:
            if target_contact and time_str:
                return f"Envoie un SMS à {target_contact} à {time_str}: {message}"
            elif target_contact:
                return f"Envoie un SMS à {target_contact}: {message}"
            return f"Envoie un SMS: {message}"

        elif self.action_type == ActionType.CHECK_IN:
            if time_str:
                return f"Vérifie que je vais bien à {time_str}"
            return "Vérifie que je vais bien"

        elif self.action_type == ActionType.SURVEILLANCE:
            return f"Si je ne réponds pas, {message}"

        elif self.action_type == ActionType.INFORMATION:
            if time_str:
                return f"Informe-moi à {time_str}: {message}"
            return f"Informe-moi: {message}"

        return message or self.description


# =============================================================================
# TEMPLATES PRÉDÉFINIS
# =============================================================================

# --- Bien-être (NON médical) ---

TEMPLATE_HYDRATION = InstructionTemplate(
    id="hydration",
    name="Rappel hydratation",
    description="Rappel régulier de boire de l'eau",
    category=TemplateCategory.WELLBEING,
    action_type=ActionType.REMINDER,
    default_recurrence=RecurrenceType.DAILY,
    default_time=time(10, 0),
    default_message="de boire un verre d'eau",
    parameters={"repeat_interval_hours": 2},
    example_phrases=[
        "Rappelle-moi de boire régulièrement",
        "Pense à me dire de boire de l'eau",
    ],
    icon="💧",
)

TEMPLATE_WALK_REMINDER = InstructionTemplate(
    id="walk_reminder",
    name="Rappel promenade",
    description="Rappel pour faire une promenade",
    category=TemplateCategory.WELLBEING,
    action_type=ActionType.REMINDER,
    default_recurrence=RecurrenceType.DAILY,
    default_time=time(10, 30),
    default_message="de faire une petite promenade",
    example_phrases=[
        "Rappelle-moi de marcher un peu chaque matin",
        "Propose-moi une promenade à 10h30",
    ],
    icon="🚶",
)

TEMPLATE_STRETCHING = InstructionTemplate(
    id="stretching",
    name="Rappel étirements",
    description="Rappel pour faire des étirements",
    category=TemplateCategory.WELLBEING,
    action_type=ActionType.REMINDER,
    default_recurrence=RecurrenceType.DAILY,
    default_time=time(9, 0),
    default_message="de faire quelques étirements",
    example_phrases=[
        "Rappelle-moi de m'étirer chaque matin",
        "Propose-moi des étirements à 9h",
    ],
    icon="🧘",
)

# --- Sécurité ---

TEMPLATE_CHECK_IN_MORNING = InstructionTemplate(
    id="check_in_morning",
    name="Vérification matinale",
    description="Vérification quotidienne le matin",
    category=TemplateCategory.SAFETY,
    action_type=ActionType.CHECK_IN,
    default_recurrence=RecurrenceType.DAILY,
    default_time=time(9, 0),
    default_message="Bonjour ! Comment allez-vous ce matin ?",
    example_phrases=[
        "Vérifie que je vais bien tous les matins",
        "Passe me voir chaque matin à 9h",
    ],
    icon="☀️",
)

TEMPLATE_CHECK_IN_EVENING = InstructionTemplate(
    id="check_in_evening",
    name="Vérification du soir",
    description="Vérification quotidienne le soir",
    category=TemplateCategory.SAFETY,
    action_type=ActionType.CHECK_IN,
    default_recurrence=RecurrenceType.DAILY,
    default_time=time(20, 0),
    default_message="Bonsoir ! Comment s'est passée votre journée ?",
    example_phrases=[
        "Vérifie que je vais bien tous les soirs",
        "Passe me voir chaque soir à 20h",
    ],
    icon="🌙",
)

TEMPLATE_NO_RESPONSE_ALERT = InstructionTemplate(
    id="no_response_alert",
    name="Alerte sans réponse",
    description="Alerte les contacts si pas de réponse",
    category=TemplateCategory.SAFETY,
    action_type=ActionType.SURVEILLANCE,
    default_recurrence=RecurrenceType.DAILY,
    condition=ConditionType.IF_NO_RESPONSE,
    default_message="préviens mes contacts de confiance",
    parameters={"no_response_threshold_minutes": 120},
    example_phrases=[
        "Préviens ma fille si je ne réponds pas",
        "Alerte mes contacts si tu n'as pas de nouvelles",
    ],
    icon="🚨",
)

# --- Social ---

TEMPLATE_WEEKLY_CALL_REMINDER = InstructionTemplate(
    id="weekly_call_reminder",
    name="Rappel appel hebdomadaire",
    description="Rappel d'appeler un proche chaque semaine",
    category=TemplateCategory.SOCIAL,
    action_type=ActionType.REMINDER,
    default_recurrence=RecurrenceType.WEEKLY,
    default_time=time(14, 0),
    default_message="d'appeler votre famille",
    example_phrases=[
        "Rappelle-moi d'appeler mes enfants le dimanche",
        "Pense à me rappeler d'appeler Marie chaque samedi",
    ],
    icon="📞",
)

TEMPLATE_SMS_TO_FAMILY = InstructionTemplate(
    id="sms_to_family",
    name="SMS à la famille",
    description="Envoyer un SMS récurrent à la famille",
    category=TemplateCategory.SOCIAL,
    action_type=ActionType.SMS_CONTACT,
    default_recurrence=RecurrenceType.WEEKLY,
    default_time=time(10, 0),
    default_message="Je vais bien, je pense à vous. Bises.",
    example_phrases=[
        "Envoie un SMS à ma fille tous les dimanches",
        "Dis bonjour à Pierre par SMS chaque semaine",
    ],
    icon="💬",
)

TEMPLATE_BIRTHDAY_REMINDER = InstructionTemplate(
    id="birthday_reminder",
    name="Rappel anniversaire",
    description="Rappel pour un anniversaire",
    category=TemplateCategory.SOCIAL,
    action_type=ActionType.REMINDER,
    default_recurrence=RecurrenceType.ONCE,
    default_message="de souhaiter l'anniversaire",
    example_phrases=[
        "Rappelle-moi l'anniversaire de Marie le 15 juin",
        "N'oublie pas l'anniversaire de mon petit-fils le 3 mars",
    ],
    icon="🎂",
)

# --- Quotidien ---

TEMPLATE_MEAL_REMINDER = InstructionTemplate(
    id="meal_reminder",
    name="Rappel repas",
    description="Rappel pour les repas",
    category=TemplateCategory.DAILY,
    action_type=ActionType.DAILY_ROUTINE,
    default_recurrence=RecurrenceType.DAILY,
    default_time=time(12, 0),
    default_message="C'est l'heure du déjeuner",
    example_phrases=[
        "Rappelle-moi de manger à midi",
        "Préviens-moi pour le déjeuner",
    ],
    icon="🍽️",
)

TEMPLATE_ACTIVITY_REMINDER = InstructionTemplate(
    id="activity_reminder",
    name="Rappel activité",
    description="Rappel pour une activité régulière",
    category=TemplateCategory.DAILY,
    action_type=ActionType.REMINDER,
    default_recurrence=RecurrenceType.WEEKLY,
    default_message="de votre activité",
    example_phrases=[
        "Rappelle-moi la gym le mardi à 10h",
        "N'oublie pas le club de lecture jeudi après-midi",
    ],
    icon="🎯",
)

TEMPLATE_TV_PROGRAM = InstructionTemplate(
    id="tv_program",
    name="Rappel programme TV",
    description="Rappel pour un programme TV",
    category=TemplateCategory.DAILY,
    action_type=ActionType.REMINDER,
    default_recurrence=RecurrenceType.WEEKLY,
    default_message="votre émission préférée commence",
    example_phrases=[
        "Rappelle-moi pour le journal de 20h",
        "N'oublie pas de me prévenir pour mon feuilleton",
    ],
    icon="📺",
)

TEMPLATE_WEATHER_INFO = InstructionTemplate(
    id="weather_info",
    name="Info météo quotidienne",
    description="Information météo chaque matin",
    category=TemplateCategory.DAILY,
    action_type=ActionType.INFORMATION,
    default_recurrence=RecurrenceType.DAILY,
    default_time=time(8, 30),
    default_message="Voici la météo d'aujourd'hui",
    parameters={"include_weather": True},
    example_phrases=[
        "Dis-moi la météo chaque matin",
        "Informe-moi du temps qu'il fait à 8h30",
    ],
    icon="🌤️",
)

TEMPLATE_SLEEP_REMINDER = InstructionTemplate(
    id="sleep_reminder",
    name="Rappel coucher",
    description="Rappel pour aller se coucher",
    category=TemplateCategory.DAILY,
    action_type=ActionType.DAILY_ROUTINE,
    default_recurrence=RecurrenceType.DAILY,
    default_time=time(22, 0),
    default_message="Il est l'heure de vous préparer pour dormir",
    example_phrases=[
        "Rappelle-moi d'aller me coucher à 22h",
        "Dis-moi quand c'est l'heure de dormir",
    ],
    icon="😴",
)


# =============================================================================
# CATALOGUE DES TEMPLATES
# =============================================================================

COMMON_TEMPLATES: Dict[str, InstructionTemplate] = {
    # Bien-être
    "hydration": TEMPLATE_HYDRATION,
    "walk_reminder": TEMPLATE_WALK_REMINDER,
    "stretching": TEMPLATE_STRETCHING,
    # Sécurité
    "check_in_morning": TEMPLATE_CHECK_IN_MORNING,
    "check_in_evening": TEMPLATE_CHECK_IN_EVENING,
    "no_response_alert": TEMPLATE_NO_RESPONSE_ALERT,
    # Social
    "weekly_call_reminder": TEMPLATE_WEEKLY_CALL_REMINDER,
    "sms_to_family": TEMPLATE_SMS_TO_FAMILY,
    "birthday_reminder": TEMPLATE_BIRTHDAY_REMINDER,
    # Quotidien
    "meal_reminder": TEMPLATE_MEAL_REMINDER,
    "activity_reminder": TEMPLATE_ACTIVITY_REMINDER,
    "tv_program": TEMPLATE_TV_PROGRAM,
    "weather_info": TEMPLATE_WEATHER_INFO,
    "sleep_reminder": TEMPLATE_SLEEP_REMINDER,
}


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def get_templates_by_category(category: TemplateCategory) -> List[InstructionTemplate]:
    """
    Récupère tous les templates d'une catégorie.

    Args:
        category: La catégorie recherchée

    Returns:
        Liste des templates de cette catégorie
    """
    return [t for t in COMMON_TEMPLATES.values() if t.category == category]


def get_template_by_id(template_id: str) -> Optional[InstructionTemplate]:
    """
    Récupère un template par son ID.

    Args:
        template_id: L'ID du template

    Returns:
        Le template ou None si non trouvé
    """
    return COMMON_TEMPLATES.get(template_id)


def find_matching_template(text: str) -> Optional[InstructionTemplate]:
    """
    Trouve le template qui correspond le mieux à un texte d'instruction.

    Analyse le texte et retourne le template le plus approprié.

    Args:
        text: Le texte de l'instruction

    Returns:
        Le template correspondant ou None
    """
    text_lower = text.lower()

    # Mapping de mots-clés vers templates
    keyword_mapping = {
        ("boire", "eau", "hydrat"): "hydration",
        ("promenade", "marcher", "marche", "balade"): "walk_reminder",
        ("étirement", "étirer", "stretching"): "stretching",
        ("vérifie", "vérifier", "comment vas", "bien-être"): "check_in_morning",
        ("alerte", "préviens", "alerter", "pas de réponse"): "no_response_alert",
        ("appeler", "téléphone", "appel"): "weekly_call_reminder",
        ("sms", "message", "texto"): "sms_to_family",
        ("anniversaire", "fête"): "birthday_reminder",
        ("manger", "repas", "déjeuner", "dîner"): "meal_reminder",
        ("gym", "sport", "activité", "club"): "activity_reminder",
        ("émission", "programme", "télé", "journal"): "tv_program",
        ("météo", "temps", "température"): "weather_info",
        ("coucher", "dormir", "sommeil"): "sleep_reminder",
    }

    for keywords, template_id in keyword_mapping.items():
        if any(kw in text_lower for kw in keywords):
            return COMMON_TEMPLATES.get(template_id)

    return None


def get_suggested_templates_for_new_user() -> List[InstructionTemplate]:
    """
    Retourne les templates suggérés pour un nouvel utilisateur.

    Ces templates représentent les instructions les plus courantes
    et utiles pour commencer.

    Returns:
        Liste de templates suggérés
    """
    suggested_ids = [
        "hydration",
        "check_in_morning",
        "check_in_evening",
        "no_response_alert",
        "weather_info",
    ]
    return [COMMON_TEMPLATES[tid] for tid in suggested_ids if tid in COMMON_TEMPLATES]


def format_template_for_display(template: InstructionTemplate) -> Dict[str, Any]:
    """
    Formate un template pour l'affichage dans l'interface.

    Args:
        template: Le template à formater

    Returns:
        Dict avec les informations formatées pour l'UI
    """
    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "icon": template.icon,
        "category": template.category.value,
        "default_time": (
            f"{template.default_time.hour:02d}:{template.default_time.minute:02d}"
            if template.default_time else None
        ),
        "recurrence": template.default_recurrence.value,
        "examples": template.example_phrases[:2],  # Limite à 2 exemples
        "action_type": template.action_type.value,
    }


def get_all_templates_formatted() -> List[Dict[str, Any]]:
    """
    Récupère tous les templates formatés pour l'interface.

    Returns:
        Liste de templates formatés par catégorie
    """
    result = []
    for category in TemplateCategory:
        templates = get_templates_by_category(category)
        if templates:
            result.append({
                "category": category.value,
                "category_name": {
                    TemplateCategory.WELLBEING: "Bien-être",
                    TemplateCategory.SAFETY: "Sécurité",
                    TemplateCategory.SOCIAL: "Social",
                    TemplateCategory.DAILY: "Quotidien",
                    TemplateCategory.CUSTOM: "Personnalisé",
                }.get(category, category.value),
                "templates": [format_template_for_display(t) for t in templates],
            })
    return result
