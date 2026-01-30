"""
Luna Actions Module - Gestion du cycle de vie des actions

Ce module gère:
- Demande de confirmation avant toute action consommatrice
- Exécution des actions confirmées
- Suivi et historique pour le propriétaire
- Gestion des quotas et limites

PRINCIPE FONDAMENTAL:
Luna ne fait JAMAIS d'action consommatrice (SMS, appel, etc.)
sans confirmation explicite du souscripteur.
Zéro surprise, zéro facture inattendue.
"""

from .models import (
    ActionRequest,
    ActionStatus,
    ActionType,
    ActionResult,
    ActionLog,
)
from .confirmation import ConfirmationManager
from .dispatcher import ActionDispatcher
from .quota_guard import (
    QuotaGuard,
    QuotaStatus,
    PlanType,
    PLAN_SMS_LIMITS,
    PLAN_VISIO_LIMITS,
    PLAN_MESSAGE_LIMITS,
    OVERAGE_PRICES,
)

__all__ = [
    # Models
    "ActionRequest",
    "ActionStatus",
    "ActionType",
    "ActionResult",
    "ActionLog",
    # Confirmation
    "ConfirmationManager",
    # Dispatch
    "ActionDispatcher",
    # Quotas
    "QuotaGuard",
    "QuotaStatus",
    "PlanType",
    "PLAN_SMS_LIMITS",
    "PLAN_VISIO_LIMITS",
    "PLAN_MESSAGE_LIMITS",
    "OVERAGE_PRICES",
]
