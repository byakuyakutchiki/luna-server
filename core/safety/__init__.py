"""
Luna Safety Module - Limites légales et éthiques

Ce module gère:
- Détection des situations dangereuses ou illégales
- Refus des demandes inappropriées
- Conseil vers services publics appropriés
- Alerte des contacts de confiance en cas d'urgence
- Conformité légale (RGPD, code civil, code pénal)
"""

from .guardian import SafetyGuardian, SafetyCheck, SafetyLevel
from .legal_knowledge import LegalKnowledge, LegalDomain
from .emergency_handler import EmergencyHandler, EmergencyType, EmergencyAction, EmergencyLevel
from .content_filter import ContentFilter, ContentCategory, FilterResult, RiskLevel

__all__ = [
    "SafetyGuardian",
    "SafetyCheck",
    "SafetyLevel",
    "LegalKnowledge",
    "LegalDomain",
    "EmergencyHandler",
    "EmergencyType",
    "EmergencyLevel",
    "EmergencyAction",
    "ContentFilter",
    "ContentCategory",
    "FilterResult",
    "RiskLevel",
]
