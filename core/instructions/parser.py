"""
Luna Instruction Parser - Analyse des instructions en langage naturel

Parse les instructions du souscripteur pour extraire:
- Le type d'action (rappel, SMS, appel, surveillance...)
- La cible (moi-même, contact de confiance, Luna)
- Le timing (heure, récurrence, condition)
- Le contenu du message si applicable
"""
import re
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, time, timedelta
from dataclasses import dataclass, field
from enum import Enum


class ActionType(str, Enum):
    """Types d'actions possibles"""
    REMINDER = "reminder"  # Rappel au souscripteur
    SMS_CONTACT = "sms_contact"  # SMS à un contact de confiance
    CALL_CONTACT = "call_contact"  # Appeler un contact
    VISIO_CONTACT = "visio_contact"  # Visio avec un contact
    WAKE_UP = "wake_up"  # Réveil (appel téléphonique)
    CHECK_IN = "check_in"  # Luna vérifie que tout va bien
    DAILY_ROUTINE = "daily_routine"  # Routine quotidienne
    SURVEILLANCE = "surveillance"  # Surveillance (inactivité, etc.)
    NOTE = "note"  # Prendre une note
    INFORMATION = "information"  # Donner une information
    READING = "reading"  # Lecture d'un texte/histoire/poème
    GAME = "game"  # Jeu (quiz, devinette, culture générale)
    MUSIC = "music"  # Suggestion/ambiance musicale
    GRATITUDE = "gratitude"  # Exercice de gratitude


class RecurrenceType(str, Enum):
    """Types de récurrence"""
    ONCE = "once"  # Une seule fois
    DAILY = "daily"  # Tous les jours
    WEEKLY = "weekly"  # Chaque semaine
    WEEKDAYS = "weekdays"  # Lundi-Vendredi
    WEEKEND = "weekend"  # Samedi-Dimanche
    MONTHLY = "monthly"  # Chaque mois
    CUSTOM = "custom"  # Personnalisé (cron)


class ConditionType(str, Enum):
    """Types de conditions"""
    NONE = "none"  # Pas de condition
    IF_NO_RESPONSE = "if_no_response"  # Si pas de réponse
    IF_CONFIRMED = "if_confirmed"  # Si confirmé
    IF_WEATHER = "if_weather"  # Selon météo
    IF_TIME_PASSED = "if_time_passed"  # Si X temps passé


@dataclass
class ParsedTime:
    """Heure parsée"""
    hour: int
    minute: int = 0

    def to_time(self) -> time:
        return time(hour=self.hour, minute=self.minute)

    def to_cron_time(self) -> str:
        return f"{self.minute} {self.hour}"


@dataclass
class ParsedInstruction:
    """Instruction parsée"""
    original_text: str
    action_type: ActionType
    target: str = "self"  # "self", nom du contact, ou numéro
    recurrence: RecurrenceType = RecurrenceType.ONCE
    scheduled_time: Optional[ParsedTime] = None
    scheduled_days: List[int] = field(default_factory=list)  # 0=Lundi, 6=Dimanche
    message_template: Optional[str] = None
    condition: ConditionType = ConditionType.NONE
    condition_params: Dict[str, Any] = field(default_factory=dict)
    priority: int = 5  # 1-10
    confidence: float = 1.0  # Confiance dans le parsing (0-1)
    needs_clarification: bool = False
    clarification_question: Optional[str] = None

    def to_cron(self) -> Optional[str]:
        """Convertit en expression cron"""
        if not self.scheduled_time:
            return None

        time_part = self.scheduled_time.to_cron_time()

        if self.recurrence == RecurrenceType.DAILY:
            return f"{time_part} * * *"
        elif self.recurrence == RecurrenceType.WEEKDAYS:
            return f"{time_part} * * 1-5"
        elif self.recurrence == RecurrenceType.WEEKEND:
            return f"{time_part} * * 0,6"
        elif self.recurrence == RecurrenceType.WEEKLY and self.scheduled_days:
            days = ",".join(str(d) for d in self.scheduled_days)
            return f"{time_part} * * {days}"
        elif self.recurrence == RecurrenceType.MONTHLY:
            return f"{time_part} 1 * *"  # Premier du mois
        else:
            return None


class InstructionParser:
    """
    Parser d'instructions en langage naturel.

    Exemples d'instructions supportées:
    - "Rappelle-moi de boire de l'eau à 10h"
    - "Envoie un SMS à Marie tous les dimanches à 10h pour prendre des nouvelles"
    - "Si je ne réponds pas pendant 2 heures, préviens mon fils"
    - "Tous les matins à 7h, demande-moi comment je vais"
    """

    # Patterns pour détecter les heures (avec et sans accent sur "a")
    TIME_PATTERNS = [
        r"[àa] (\d{1,2})h(\d{2})?",
        r"[àa] (\d{1,2}):(\d{2})",
        r"[àa] (\d{1,2}) heures?(?: (\d{2}))?",
        r"vers (\d{1,2})h(\d{2})?",
    ]

    # Mots-clés pour les types d'actions
    ACTION_KEYWORDS = {
        ActionType.WAKE_UP: [
            "réveille-moi", "reveille-moi", "réveille moi", "reveille moi",
            "réveil à", "reveil a", "sonne à", "fais sonner",
            "réveiller", "comme un réveil", "alarm",
        ],
        ActionType.VISIO_CONTACT: [
            "visio avec", "visioconférence avec", "visioconference avec",
            "appel vidéo avec", "appel video avec", "visio à", "lance une visio",
        ],
        ActionType.SMS_CONTACT: [
            "envoie un sms", "envoyer un sms", "sms à", "texto à", "message à"
        ],
        ActionType.CALL_CONTACT: [
            "appelle", "appeler", "téléphone à", "passe un coup de fil"
        ],
        ActionType.CHECK_IN: [
            "demande-moi", "demande moi", "vérifie", "comment je vais",
            "prends de mes nouvelles", "comment ça va"
        ],
        ActionType.SURVEILLANCE: [
            "si je ne réponds pas", "si pas de réponse", "si je ne donne pas",
            "surveille", "vérifie que"
        ],
        ActionType.READING: [
            "lis-moi", "lis moi", "raconte-moi", "raconte moi",
            "lecture de", "poème", "poeme", "histoire",
        ],
        ActionType.GAME: [
            "quiz", "devinette", "jeu de", "culture générale",
            "joue avec moi", "enigme", "énigme",
        ],
        ActionType.MUSIC: [
            "musique", "chanson", "mélodie", "chante",
        ],
        ActionType.GRATITUDE: [
            "gratitude", "reconnaissant", "remerci",
            "3 choses positives", "moment positif",
        ],
        ActionType.REMINDER: [
            "rappelle", "rappeler", "rappel", "n'oublie pas", "pense à", "souviens"
        ],
    }

    # Mots-clés pour la récurrence
    RECURRENCE_KEYWORDS = {
        RecurrenceType.DAILY: [
            "tous les jours", "chaque jour", "quotidien", "quotidiennement",
            "tous les matins", "tous les soirs", "chaque matin", "chaque soir"
        ],
        RecurrenceType.WEEKLY: [
            "chaque semaine", "toutes les semaines", "hebdomadaire"
        ],
        RecurrenceType.WEEKDAYS: [
            "en semaine", "jours ouvrés", "lundi au vendredi"
        ],
        RecurrenceType.WEEKEND: [
            "le week-end", "weekend", "samedi et dimanche"
        ],
    }

    # Jours de la semaine
    DAYS_OF_WEEK = {
        "lundi": 0, "lundis": 0,
        "mardi": 1, "mardis": 1,
        "mercredi": 2, "mercredis": 2,
        "jeudi": 3, "jeudis": 3,
        "vendredi": 4, "vendredis": 4,
        "samedi": 5, "samedis": 5,
        "dimanche": 6, "dimanches": 6,
    }

    # Moments de la journée (heures par défaut)
    TIME_OF_DAY = {
        "matin": 8,
        "matins": 8,
        "midi": 12,
        "après-midi": 14,
        "apres-midi": 14,
        "soir": 19,
        "soirs": 19,
        "nuit": 21,
    }

    @classmethod
    def parse(cls, text: str) -> ParsedInstruction:
        """
        Parse une instruction en langage naturel.

        Args:
            text: L'instruction en français

        Returns:
            ParsedInstruction avec les détails extraits
        """
        text_lower = text.lower().strip()

        # 1. Détecter le type d'action
        action_type, action_confidence = cls._detect_action_type(text_lower)

        # 2. Détecter l'heure
        scheduled_time = cls._extract_time(text_lower)

        # 3. Détecter la récurrence
        recurrence, scheduled_days = cls._detect_recurrence(text_lower)

        # 4. Détecter la cible
        target = cls._extract_target(text_lower)

        # 5. Détecter les conditions
        condition, condition_params = cls._detect_condition(text_lower)

        # 6. Extraire le message template si applicable
        message_template = cls._extract_message(text_lower, action_type)

        # 7. Calculer la priorité
        priority = cls._calculate_priority(action_type, condition)

        # 8. Vérifier si clarification nécessaire
        needs_clarification, clarification_q = cls._check_clarification_needed(
            action_type, scheduled_time, target, recurrence
        )

        return ParsedInstruction(
            original_text=text,
            action_type=action_type,
            target=target,
            recurrence=recurrence,
            scheduled_time=scheduled_time,
            scheduled_days=scheduled_days,
            message_template=message_template,
            condition=condition,
            condition_params=condition_params,
            priority=priority,
            confidence=action_confidence,
            needs_clarification=needs_clarification,
            clarification_question=clarification_q,
        )

    @classmethod
    def _detect_action_type(cls, text: str) -> Tuple[ActionType, float]:
        """Détecte le type d'action"""
        for action_type, keywords in cls.ACTION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    return action_type, 0.9

        # Défaut: rappel général
        return ActionType.REMINDER, 0.5

    @classmethod
    def _extract_time(cls, text: str) -> Optional[ParsedTime]:
        """Extrait l'heure de l'instruction"""
        # Essayer les patterns d'heure
        for pattern in cls.TIME_PATTERNS:
            match = re.search(pattern, text)
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2)) if match.group(2) else 0
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    return ParsedTime(hour=hour, minute=minute)

        # Essayer les moments de la journée
        for moment, hour in cls.TIME_OF_DAY.items():
            if moment in text:
                return ParsedTime(hour=hour, minute=0)

        return None

    @classmethod
    def _detect_recurrence(cls, text: str) -> Tuple[RecurrenceType, List[int]]:
        """Détecte la récurrence"""
        days = []

        # Vérifier les mots-clés de récurrence
        for recurrence_type, keywords in cls.RECURRENCE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    return recurrence_type, days

        # Vérifier les jours spécifiques
        for day_name, day_num in cls.DAYS_OF_WEEK.items():
            if day_name in text:
                days.append(day_num)

        if days:
            if len(days) == 7:
                return RecurrenceType.DAILY, []
            elif days == [5, 6] or days == [6, 5]:
                return RecurrenceType.WEEKEND, []
            else:
                return RecurrenceType.WEEKLY, days

        # Vérifier "tous les" + jour
        match = re.search(r"tous les (\w+)", text)
        if match:
            day = match.group(1).lower()
            if day in cls.DAYS_OF_WEEK:
                return RecurrenceType.WEEKLY, [cls.DAYS_OF_WEEK[day]]

        return RecurrenceType.ONCE, []

    @classmethod
    def _extract_target(cls, text: str) -> str:
        """Extrait la cible de l'action"""
        # Patterns pour extraire le nom du contact
        patterns = [
            r"(?:à|a) ([A-Z][a-zéèêë]+)",  # "à Marie"
            r"(?:préviens?|contacte?|appelle?) ([A-Z][a-zéèêë]+)",  # "préviens Jean"
            r"(?:mon|ma) (fils|fille|mari|femme|frère|soeur|père|mère|voisin|voisine)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # Si SMS ou appel mentionné mais pas de cible, on note
        if any(kw in text for kw in ["sms", "appel", "prévien", "contact"]):
            return "contact_unknown"

        return "self"

    @classmethod
    def _detect_condition(cls, text: str) -> Tuple[ConditionType, Dict[str, Any]]:
        """Détecte les conditions"""
        params = {}

        # Si pas de réponse pendant X temps
        match = re.search(r"si (?:je )?(?:ne )?répond(?:s)? pas (?:pendant )?(\d+) (heure|minute|jour)", text)
        if match:
            duration = int(match.group(1))
            unit = match.group(2)
            params["duration"] = duration
            params["unit"] = unit
            return ConditionType.IF_NO_RESPONSE, params

        # Si pas de nouvelles
        if "si pas de nouvelle" in text or "si je ne donne pas de nouvelle" in text:
            params["duration"] = 24
            params["unit"] = "heure"
            return ConditionType.IF_NO_RESPONSE, params

        return ConditionType.NONE, params

    @classmethod
    def _extract_message(cls, text: str, action_type: ActionType) -> Optional[str]:
        """Extrait le template de message"""
        if action_type == ActionType.WAKE_UP:
            return "C'est l'heure de se réveiller ! Bonjour, Luna est là pour bien démarrer votre journée."
        if action_type == ActionType.READING:
            return "Lecture du jour"
        if action_type == ActionType.GAME:
            return "C'est l'heure du jeu !"
        if action_type == ActionType.MUSIC:
            return "Un moment musical pour vous"
        if action_type == ActionType.GRATITUDE:
            return "Prenons un moment pour la gratitude. Quelles sont les 3 choses positives de votre journée ?"
        if action_type not in (ActionType.SMS_CONTACT, ActionType.REMINDER):
            return None

        # Chercher un message entre guillemets
        match = re.search(r'["\'](.+?)["\']', text)
        if match:
            return match.group(1)

        # Chercher après "pour dire", "pour demander"
        match = re.search(r"pour (?:dire|demander|savoir|vérifier) (.+?)(?:\.|$)", text)
        if match:
            return match.group(1).strip()

        # Chercher après "que"
        match = re.search(r"(?:dis|demande|vérifie) que (.+?)(?:\.|$)", text)
        if match:
            return match.group(1).strip()

        return None

    @classmethod
    def _calculate_priority(cls, action_type: ActionType, condition: ConditionType) -> int:
        """Calcule la priorité de l'instruction"""
        base_priority = {
            ActionType.SURVEILLANCE: 9,
            ActionType.WAKE_UP: 8,
            ActionType.CHECK_IN: 7,
            ActionType.SMS_CONTACT: 6,
            ActionType.CALL_CONTACT: 6,
            ActionType.VISIO_CONTACT: 6,
            ActionType.REMINDER: 5,
            ActionType.DAILY_ROUTINE: 4,
            ActionType.READING: 3,
            ActionType.GAME: 3,
            ActionType.GRATITUDE: 3,
            ActionType.MUSIC: 3,
            ActionType.NOTE: 2,
            ActionType.INFORMATION: 1,
        }

        priority = base_priority.get(action_type, 5)

        # Les conditions augmentent la priorité
        if condition == ConditionType.IF_NO_RESPONSE:
            priority = min(10, priority + 2)

        return priority

    @classmethod
    def _check_clarification_needed(
        cls,
        action_type: ActionType,
        scheduled_time: Optional[ParsedTime],
        target: str,
        recurrence: RecurrenceType,
    ) -> Tuple[bool, Optional[str]]:
        """Vérifie si une clarification est nécessaire"""

        # Besoin d'une heure pour les rappels récurrents
        if recurrence != RecurrenceType.ONCE and not scheduled_time:
            return True, "À quelle heure souhaitez-vous ce rappel ?"

        # Besoin du contact pour SMS/appel
        if action_type in (ActionType.SMS_CONTACT, ActionType.CALL_CONTACT):
            if target in ("self", "contact_unknown"):
                return True, "À quel contact souhaitez-vous que j'envoie ce message ?"

        return False, None

    @classmethod
    def format_confirmation(cls, parsed: ParsedInstruction) -> str:
        """Formate une confirmation de l'instruction parsée"""
        parts = []

        # Action
        action_names = {
            ActionType.REMINDER: "vous rappeler",
            ActionType.SMS_CONTACT: f"envoyer un SMS à {parsed.target}",
            ActionType.CALL_CONTACT: f"appeler {parsed.target}",
            ActionType.VISIO_CONTACT: f"lancer une visio avec {parsed.target}",
            ActionType.WAKE_UP: "vous réveiller par un appel",
            ActionType.CHECK_IN: "vous demander comment vous allez",
            ActionType.DAILY_ROUTINE: "vous rappeler votre routine",
            ActionType.SURVEILLANCE: "surveiller votre activité",
            ActionType.READING: "vous faire une lecture",
            ActionType.GAME: "vous proposer un jeu",
            ActionType.MUSIC: "vous proposer un moment musical",
            ActionType.GRATITUDE: "faire un exercice de gratitude avec vous",
        }
        parts.append(f"Je vais {action_names.get(parsed.action_type, 'exécuter cette action')}")

        # Récurrence
        if parsed.recurrence == RecurrenceType.DAILY:
            parts.append("tous les jours")
        elif parsed.recurrence == RecurrenceType.WEEKDAYS:
            parts.append("en semaine")
        elif parsed.recurrence == RecurrenceType.WEEKEND:
            parts.append("le week-end")
        elif parsed.recurrence == RecurrenceType.WEEKLY and parsed.scheduled_days:
            day_names = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
            days = [day_names[d] for d in parsed.scheduled_days]
            parts.append(f"chaque {', '.join(days)}")

        # Heure
        if parsed.scheduled_time:
            parts.append(f"à {parsed.scheduled_time.hour}h{parsed.scheduled_time.minute:02d}")

        # Condition
        if parsed.condition == ConditionType.IF_NO_RESPONSE:
            duration = parsed.condition_params.get("duration", "?")
            unit = parsed.condition_params.get("unit", "heure")
            parts.append(f"si vous ne répondez pas pendant {duration} {unit}(s)")

        return " ".join(parts) + ". C'est bien cela ?"
