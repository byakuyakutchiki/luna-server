"""
Luna Perception Detector - YOLOv8 wrapper + capture webcam

Capture des images depuis la webcam du device et detection d'objets/personnes.
Aucune image n'est stockee - seules les metadonnees de detection sont conservees.
"""
import logging
import time
from typing import Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class PersonPosture(str, Enum):
    """Posture estimee basee sur la geometrie du bounding box."""
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


class PerceptionDetector:
    """
    Detecteur YOLO pour Luna.

    Capture des frames depuis la webcam et execute YOLOv8n.
    Ne stocke JAMAIS les images - seulement les metadonnees.
    """

    # Classes COCO pertinentes pour un environnement domestique
    RELEVANT_CLASSES = {
        0: "person",
        15: "cat",
        16: "dog",
        39: "bottle",
        41: "cup",
        56: "chair",
        57: "couch",
        59: "bed",
        60: "dining table",
        62: "tv",
        63: "laptop",
        66: "keyboard",
        67: "cell phone",
        73: "book",
    }

    CONFIDENCE_THRESHOLD = 0.35

    def __init__(self, camera_index: int = 0, model_name: str = "yolov8n.pt"):
        self.camera_index = camera_index
        self.model_name = model_name
        self._model = None
        self._cap = None
        self._initialized = False

    def initialize(self) -> bool:
        """
        Charge le modele YOLO et ouvre la webcam.
        Le modele est telecharge automatiquement au premier appel (~6 MB).
        """
        try:
            from ultralytics import YOLO
            self._model = YOLO(self.model_name)
            logger.info(f"YOLOv8 model loaded: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            return False

        try:
            import cv2
            self._cap = cv2.VideoCapture(self.camera_index)
            if not self._cap.isOpened():
                logger.error(f"Cannot open camera {self.camera_index}")
                return False
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            logger.info(f"Camera {self.camera_index} opened (640x480)")
        except Exception as e:
            logger.error(f"Failed to open camera: {e}")
            return False

        self._initialized = True
        return True

    def capture_and_detect(self) -> Optional[FrameAnalysis]:
        """
        Capture une frame et execute la detection.
        La frame est supprimee immediatement apres l'inference.
        """
        if not self._initialized or not self._cap:
            return None

        # Capture
        t0 = time.time()
        ret, frame = self._cap.read()
        if not ret or frame is None:
            logger.warning("Frame capture failed")
            return None
        capture_ms = (time.time() - t0) * 1000

        # Inference
        t1 = time.time()
        results = self._model(frame, verbose=False, conf=self.CONFIDENCE_THRESHOLD)
        inference_ms = (time.time() - t1) * 1000

        # Parse
        now = datetime.utcnow()
        detections = []
        h, w = frame.shape[:2]

        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                if cls_id not in self.RELEVANT_CLASSES:
                    continue
                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                detections.append(Detection(
                    class_name=self.RELEVANT_CLASSES[cls_id],
                    confidence=conf,
                    bbox=(x1 / w, y1 / h, x2 / w, y2 / h),
                    timestamp=now,
                ))

        # Frame supprimee - jamais stockee
        del frame

        # Analyse personnes
        persons = [d for d in detections if d.class_name == "person"]
        bed_detected = any(d.class_name == "bed" for d in detections)
        postures = [self._estimate_posture(d, bed_detected) for d in persons]
        objects = list(set(d.class_name for d in detections if d.class_name != "person"))

        return FrameAnalysis(
            timestamp=now,
            persons_count=len(persons),
            person_postures=postures,
            objects=objects,
            detections=detections,
            capture_time_ms=capture_ms,
            inference_time_ms=inference_ms,
        )

    def _estimate_posture(self, detection: Detection, bed_nearby: bool) -> PersonPosture:
        """
        Estime la posture depuis la geometrie du bounding box.
        Heuristique simple - aucune garantie de fiabilite.
        """
        x1, y1, x2, y2 = detection.bbox
        width = x2 - x1
        height = y2 - y1
        center_y = (y1 + y2) / 2

        if width == 0:
            return PersonPosture.UNKNOWN

        aspect_ratio = height / width

        if aspect_ratio > 1.5:
            return PersonPosture.STANDING
        elif aspect_ratio > 0.9:
            return PersonPosture.SITTING
        else:
            # Personne horizontale
            if bed_nearby:
                return PersonPosture.LYING_BED
            elif center_y > 0.6:
                return PersonPosture.LYING_FLOOR
            return PersonPosture.UNKNOWN

    def is_camera_available(self) -> bool:
        if not self._cap:
            return False
        return self._cap.isOpened()

    def release(self):
        """Libere les ressources camera."""
        if self._cap:
            self._cap.release()
            self._cap = None
        self._initialized = False
        logger.info("Perception detector released")
