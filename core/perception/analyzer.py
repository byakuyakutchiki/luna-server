"""
Luna Scene Analyzer - Analyse temporelle et detection d'anomalies

Analyse les resultats de detection sur le temps pour suivre la
presence/absence, detecter les changements de posture, et identifier
les situations inhabituelles.

IMPORTANT LEGAL: Ce module fournit une aide contextuelle.
Il ne constitue PAS un dispositif medical ou de securite.
"""
import json
import re
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import deque

from .detector import FrameAnalysis, PersonPosture

logger = logging.getLogger(__name__)


class AbnormalityType(str, Enum):
    PERSON_ON_FLOOR = "person_on_floor"
    EXTENDED_ABSENCE = "extended_absence"
    UNUSUAL_INACTIVITY = "unusual_inactivity"
    PERSON_APPEARED = "person_appeared"
    PERSON_LEFT = "person_left"


class SceneSeverity(str, Enum):
    INFO = "info"
    ATTENTION = "attention"
    CONCERN = "concern"


@dataclass
class SceneState:
    """Etat courant de la scene percue."""
    timestamp: datetime
    persons_present: int
    primary_posture: str
    objects_visible: List[str]
    abnormalities: List[Dict[str, Any]]
    scene_description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "persons_present": self.persons_present,
            "primary_posture": self.primary_posture,
            "objects_visible": self.objects_visible,
            "abnormalities": self.abnormalities,
            "scene_description": self.scene_description,
        }

    def to_redis(self) -> Dict[str, str]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "persons_present": str(self.persons_present),
            "primary_posture": self.primary_posture,
            "objects_visible": json.dumps(self.objects_visible),
            "abnormalities": json.dumps(self.abnormalities),
            "scene_description": self.scene_description,
        }

    @classmethod
    def from_redis(cls, data: Dict[str, str]) -> "SceneState":
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            persons_present=int(data.get("persons_present", "0")),
            primary_posture=data.get("primary_posture", "unknown"),
            objects_visible=json.loads(data.get("objects_visible", "[]")),
            abnormalities=json.loads(data.get("abnormalities", "[]")),
            scene_description=data.get("scene_description", ""),
        )


class SceneAnalyzer:
    """
    Analyse la scene sur le temps.

    Maintient un historique court des detections pour determiner
    les tendances et generer un resume lisible pour Luna.

    Pas de promesse de fiabilite - aide contextuelle uniquement.
    """

    # Seuils conservateurs pour minimiser les faux positifs
    FLOOR_DURATION_ATTENTION = 120   # 2 min au sol = attention
    FLOOR_DURATION_CONCERN = 300     # 5 min au sol = concern
    ABSENCE_DURATION_ATTENTION = 3600  # 1h sans personne = attention
    HISTORY_SIZE = 60                # ~10 min a 10s d'intervalle

    # Prudence verbale : mots interdits dans les descriptions de perception
    BANNED_WORDS = [
        "surveillance", "diagnostic", "chute", "urgence medicale",
        "surveille", "diagnostique", "monitore", "alerte medicale",
    ]
    SOFT_REPLACEMENTS = {
        "chute": "situation au sol",
        "surveillance": "observation",
        "urgence medicale": "situation preoccupante",
        "diagnostic": "impression",
        "surveille": "observe",
        "diagnostique": "remarque",
        "monitore": "observe",
        "alerte medicale": "situation inhabituelle",
    }

    POSTURE_LABELS = {
        PersonPosture.STANDING: "debout",
        PersonPosture.SITTING: "assis(e)",
        PersonPosture.LYING_FLOOR: "allonge(e) au sol",
        PersonPosture.LYING_BED: "allonge(e) (lit)",
        PersonPosture.UNKNOWN: "posture indeterminee",
    }

    def __init__(self):
        self._history: deque = deque(maxlen=self.HISTORY_SIZE)
        self._floor_start: Optional[datetime] = None
        self._last_person_seen: Optional[datetime] = None
        self._person_was_present: bool = False

    def analyze(self, frame_analysis: FrameAnalysis) -> SceneState:
        """Analyse une FrameAnalysis et produit un SceneState."""
        now = frame_analysis.timestamp
        self._history.append(frame_analysis)

        abnormalities: List[Dict[str, Any]] = []
        persons = frame_analysis.persons_count
        postures = frame_analysis.person_postures

        primary = postures[0].value if postures else "absent"

        # --- Personne au sol ---
        person_on_floor = any(p == PersonPosture.LYING_FLOOR for p in postures)

        if person_on_floor:
            if self._floor_start is None:
                self._floor_start = now
            floor_duration = (now - self._floor_start).total_seconds()

            if floor_duration >= self.FLOOR_DURATION_CONCERN:
                abnormalities.append({
                    "type": AbnormalityType.PERSON_ON_FLOOR.value,
                    "severity": SceneSeverity.CONCERN.value,
                    "description": f"Il semble qu'une personne soit au sol depuis {int(floor_duration)}s",
                    "duration_seconds": int(floor_duration),
                })
            elif floor_duration >= self.FLOOR_DURATION_ATTENTION:
                abnormalities.append({
                    "type": AbnormalityType.PERSON_ON_FLOOR.value,
                    "severity": SceneSeverity.ATTENTION.value,
                    "description": f"Il semble qu'une personne soit au sol depuis {int(floor_duration)}s",
                    "duration_seconds": int(floor_duration),
                })
        else:
            self._floor_start = None

        # --- Presence / absence ---
        if persons > 0:
            self._last_person_seen = now
            if not self._person_was_present:
                abnormalities.append({
                    "type": AbnormalityType.PERSON_APPEARED.value,
                    "severity": SceneSeverity.INFO.value,
                    "description": "Personne detectee dans le champ",
                    "duration_seconds": 0,
                })
            self._person_was_present = True
        else:
            if self._person_was_present:
                abnormalities.append({
                    "type": AbnormalityType.PERSON_LEFT.value,
                    "severity": SceneSeverity.INFO.value,
                    "description": "Personne sortie du champ",
                    "duration_seconds": 0,
                })
                self._person_was_present = False

            if self._last_person_seen:
                absence = (now - self._last_person_seen).total_seconds()
                if absence >= self.ABSENCE_DURATION_ATTENTION:
                    abnormalities.append({
                        "type": AbnormalityType.EXTENDED_ABSENCE.value,
                        "severity": SceneSeverity.ATTENTION.value,
                        "description": f"Il semble que personne ne soit visible depuis {int(absence / 60)} min",
                        "duration_seconds": int(absence),
                    })

        description = self._build_description(
            persons, postures, frame_analysis.objects, abnormalities
        )

        return SceneState(
            timestamp=now,
            persons_present=persons,
            primary_posture=primary,
            objects_visible=frame_analysis.objects,
            abnormalities=abnormalities,
            scene_description=description,
        )

    def _sanitize_description(self, text: str) -> str:
        """Remplace les mots bannis par des formulations prudentes."""
        result = text
        for banned, replacement in self.SOFT_REPLACEMENTS.items():
            result = re.sub(re.escape(banned), replacement, result, flags=re.IGNORECASE)
        return result

    def _build_description(
        self,
        persons: int,
        postures: List[PersonPosture],
        objects: List[str],
        abnormalities: List[Dict[str, Any]],
    ) -> str:
        """Description concise en francais pour le contexte Luna."""
        parts = []

        if persons == 0:
            parts.append("Personne n'est visible dans le champ de la camera.")
        elif persons == 1:
            label = self.POSTURE_LABELS.get(postures[0], "posture indeterminee") if postures else ""
            parts.append(f"1 personne presente, {label}.")
        else:
            parts.append(f"{persons} personnes presentes.")

        if objects:
            parts.append(f"Objets: {', '.join(objects[:5])}.")

        for abn in abnormalities:
            if abn["severity"] in ("attention", "concern"):
                parts.append(f"[{abn['severity'].upper()}] {abn['description']}.")

        return self._sanitize_description(" ".join(parts))

    def get_context_for_luna(self, caution_mode: str = "assistif") -> str:
        """
        Contexte court a injecter dans la conversation Luna.
        Filtre selon le caution_mode du profil.
        """
        if not self._history:
            return ""

        last = self._history[-1]
        state = self.analyze(last)
        if not state.scene_description:
            return ""

        # Filtrer les anomalies selon le mode prudence
        if caution_mode == "passif":
            # Seulement les CONCERN
            if not any(a["severity"] == "concern" for a in state.abnormalities):
                return ""
        elif caution_mode == "urgence_only":
            # Seulement les CONCERN
            if not any(a["severity"] == "concern" for a in state.abnormalities):
                return ""
        elif caution_mode == "assistif":
            # ATTENTION + CONCERN (defaut)
            pass
        elif caution_mode == "proactif":
            # Tout remonter (INFO inclus)
            pass

        return (
            f"\n[Perception contextuelle - camera du domicile] "
            f"{state.scene_description}"
        )

    def has_concern(self) -> bool:
        """Verifie s'il y a une anomalie niveau concern."""
        if not self._history:
            return False
        state = self.analyze(self._history[-1])
        return any(a["severity"] == "concern" for a in state.abnormalities)

    def reset(self):
        """Reset complet du tracking."""
        self._history.clear()
        self._floor_start = None
        self._last_person_seen = None
        self._person_was_present = False
