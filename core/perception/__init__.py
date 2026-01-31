"""
Luna Perception - Aide contextuelle visuelle

IMPORTANT LEGAL:
Ce module enrichit la comprehension contextuelle de Luna.
Il ne constitue PAS un systeme de videosurveillance ni un dispositif
de detection de chutes. Aucune garantie de detection n'est offerte.
Luna utilise ces informations comme aide contextuelle, comme une
compagne qui observe naturellement l'environnement.

Aucune image n'est stockee. Seules les metadonnees de detection
(labels, positions, timestamps) sont conservees.
"""
from .detector import PerceptionDetector, FrameAnalysis, PersonPosture, Detection
from .analyzer import SceneAnalyzer, SceneState, AbnormalityType, SceneSeverity

__all__ = [
    "PerceptionDetector",
    "FrameAnalysis",
    "PersonPosture",
    "Detection",
    "SceneAnalyzer",
    "SceneState",
    "AbnormalityType",
    "SceneSeverity",
]
