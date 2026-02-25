"""
Luna Perception Detector - Analyse de scene via OpenAI Vision

Recoit des frames base64 depuis le navigateur du device (getUserMedia)
et analyse la scene via GPT-4o-mini vision.
Aucune image n'est stockee - seules les metadonnees de detection sont conservees.
"""
import json
import logging
import os
import time
from typing import Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class PersonPosture(str, Enum):
    """Posture estimee basee sur l'analyse visuelle."""
    STANDING = "standing"
    SITTING = "sitting"
    LYING_FLOOR = "lying_floor"
    LYING_BED = "lying_bed"
    UNKNOWN = "unknown"


@dataclass
class Detection:
    """Resultat de detection pour un objet."""
    class_name: str
    confidence: float
    bbox: Tuple[float, float, float, float]  # (x1, y1, x2, y2) normalise 0-1
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class FrameAnalysis:
    """Analyse complete d'une frame (aucune image conservee)."""
    timestamp: datetime
    persons_count: int
    person_postures: List[PersonPosture]
    objects: List[str]
    detections: List[Detection]
    capture_time_ms: float
    inference_time_ms: float


# Prompt systeme pour l'analyse de scene
_VISION_SYSTEM_PROMPT = """Tu es un module de perception contextuelle pour Luna, un compagnon de lien social.
Analyse cette image de camera pour decrire la scene de facon factuelle.

Reponds UNIQUEMENT en JSON avec cette structure exacte:
{
  "persons_count": <int>,
  "persons": [
    {"posture": "standing|sitting|lying_floor|lying_bed|unknown", "confidence": <0.0-1.0>}
  ],
  "objects": ["<nom objet en francais>", ...],
  "scene_summary": "<description courte en francais de la scene>"
}

Regles:
- Compte uniquement les personnes clairement visibles
- Objets pertinents: meubles, animaux, electromenager, nourriture, medicaments
- Ne mentionne JAMAIS les mots: surveillance, diagnostic, chute, urgence, alerte
- Sois factuel et concis
- Si l'image est floue/sombre, indique "persons_count": 0 et "scene_summary": "Image peu lisible"
"""


class PerceptionDetector:
    """
    Detecteur de scene pour Luna via OpenAI Vision API.

    Recoit des frames base64 depuis le navigateur et les analyse
    via GPT-4o-mini vision. Ne stocke JAMAIS les images.
    """

    def __init__(self):
        self._initialized = False
        self._openai_client = None
        self._last_frame_time: Optional[float] = None
        self._remote_camera_active = False

    def initialize(self) -> bool:
        """Initialise le client OpenAI pour l'analyse vision."""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY non disponible pour perception vision")
            return False
        try:
            from openai import OpenAI
            self._openai_client = OpenAI(api_key=api_key)
            self._initialized = True
            logger.info("Perception detector initialized (OpenAI Vision)")
            return True
        except Exception as e:
            logger.error(f"Failed to init OpenAI client for perception: {e}")
            return False

    def analyze_frame_b64(self, image_b64: str) -> Optional[FrameAnalysis]:
        """
        Analyse une frame encodee en base64 via OpenAI Vision.
        L'image n'est PAS stockee - seules les metadonnees sont conservees.
        """
        if not self._initialized or not self._openai_client:
            return None

        t0 = time.time()

        try:
            response = self._openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": _VISION_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_b64}",
                                    "detail": "low",  # 85 tokens, rapide et pas cher
                                },
                            },
                        ],
                    },
                ],
                max_tokens=300,
                temperature=0.1,
            )
        except Exception as e:
            logger.error(f"OpenAI Vision API error: {e}")
            return None

        inference_ms = (time.time() - t0) * 1000
        now = datetime.utcnow()
        self._last_frame_time = time.time()

        # Parse la reponse JSON
        raw = response.choices[0].message.content.strip()
        # Enlever les balises markdown si presentes
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(f"Vision API returned non-JSON: {raw[:200]}")
            return FrameAnalysis(
                timestamp=now,
                persons_count=0,
                person_postures=[],
                objects=[],
                detections=[],
                capture_time_ms=0,
                inference_time_ms=inference_ms,
            )

        # Construire les detections et postures
        persons_count = data.get("persons_count", 0)
        persons_data = data.get("persons", [])
        objects = data.get("objects", [])

        postures = []
        detections = []
        for p in persons_data:
            posture_str = p.get("posture", "unknown")
            try:
                posture = PersonPosture(posture_str)
            except ValueError:
                posture = PersonPosture.UNKNOWN
            postures.append(posture)
            conf = p.get("confidence", 0.5)
            detections.append(Detection(
                class_name="person",
                confidence=conf,
                bbox=(0.0, 0.0, 1.0, 1.0),  # pas de bbox precise en vision
                timestamp=now,
            ))

        # Ajouter les objets comme detections
        for obj in objects:
            detections.append(Detection(
                class_name=obj,
                confidence=0.7,
                bbox=(0.0, 0.0, 1.0, 1.0),
                timestamp=now,
            ))

        return FrameAnalysis(
            timestamp=now,
            persons_count=persons_count,
            person_postures=postures,
            objects=objects,
            detections=detections,
            capture_time_ms=0,
            inference_time_ms=inference_ms,
        )

    def set_remote_camera_active(self, active: bool):
        """Indique si un navigateur envoie activement des frames."""
        self._remote_camera_active = active
        if active:
            self._last_frame_time = time.time()

    def is_camera_available(self) -> bool:
        """La camera est disponible si un navigateur envoie des frames recemment."""
        if not self._remote_camera_active:
            return False
        if self._last_frame_time is None:
            return False
        # Considere la camera active si on a recu une frame dans les 30 dernieres secondes
        return (time.time() - self._last_frame_time) < 30

    def release(self):
        """Libere les ressources."""
        self._remote_camera_active = False
        self._last_frame_time = None
        self._initialized = False
        logger.info("Perception detector released")
