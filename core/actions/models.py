"""
Luna Action Models - Modèles de données pour les actions

Définit les structures pour:
- Demandes d'action (avant confirmation)
- Résultats d'action (après exécution)
- Logs d'audit (traçabilité propriétaire)
"""
import uuid
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class ActionType(str, Enum):
    """Types d'actions possibles"""
    SEND_SMS = "send_sms"
    CALL = "call"
    ALERT_CONTACTS = "alert_contacts"
    START_VISIO = "start_visio"


class ActionStatus(str, Enum):
    """Cycle de vie d'une action"""
    PROPOSED = "proposed"  # Luna propose l'action
    AWAITING_CONFIRMATION = "awaiting_confirmation"  # En attente du souscripteur
    CONFIRMED = "confirmed"  # Souscripteur a confirmé
    REJECTED = "rejected"  # Souscripteur a refusé
    EXECUTING = "executing"  # En cours d'exécution
    COMPLETED = "completed"  # Terminée avec succès
    FAILED = "failed"  # Échec
    EXPIRED = "expired"  # Expirée sans réponse
    CANCELLED = "cancelled"  # Annulée


@dataclass
class ActionRequest:
    """
    Demande d'action soumise par Luna.

    Avant toute action consommatrice de quota, Luna crée une ActionRequest
    et attend la confirmation du souscripteur.
    """
    action_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: int = 0
    action_type: ActionType = ActionType.SEND_SMS
    target: str = ""  # Nom du contact ou numéro
    target_phone: Optional[str] = None  # Numéro résolu
    description: str = ""  # "Envoyer un SMS à Marie"
    message_body: Optional[str] = None  # Contenu du message si SMS
    status: ActionStatus = ActionStatus.PROPOSED
    estimated_cost: int = 1  # Coût estimé en unités (segments SMS, minutes, etc.)

    # Confirmation
    confirmed: bool = False
    confirmed_at: Optional[datetime] = None
    confirmation_method: Optional[str] = None  # "voice", "text", "button"
    rejection_reason: Optional[str] = None

    # Explicabilite
    reasoning_explanation: str = ""  # Explication humaine de pourquoi cette action

    # Contexte
    instruction_id: Optional[str] = None  # Lien vers l'instruction source
    conversation_id: Optional[str] = None
    source: str = "luna"  # Qui a initié: "luna", "instruction", "emergency"

    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None  # Expiration si pas de réponse
    executed_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        """Vérifie si la demande a expiré"""
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return True
        return False

    def is_pending(self) -> bool:
        """Vérifie si la demande est en attente"""
        return self.status in (
            ActionStatus.PROPOSED,
            ActionStatus.AWAITING_CONFIRMATION,
        )


@dataclass
class ActionResult:
    """Résultat de l'exécution d'une action"""
    action_id: str
    success: bool
    message: str  # Message pour Luna à communiquer au souscripteur
    reasoning_explanation: str = ""  # Explication humaine du resultat
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    executed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ActionLog:
    """
    Log d'audit pour la traçabilité.

    Chaque action est loggée pour que le propriétaire puisse
    consulter l'historique depuis son tableau de bord.
    """
    log_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: int = 0
    action_id: str = ""
    action_type: ActionType = ActionType.SEND_SMS
    event: str = ""  # "proposed", "confirmed", "executed", "failed"
    description: str = ""
    reasoning_explanation: str = ""  # Explication humaine
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = "luna"  # Qui a déclenché l'événement

    def to_dict(self) -> Dict[str, Any]:
        """Sérialise pour stockage Redis ou API"""
        return {
            "log_id": self.log_id,
            "tenant_id": self.tenant_id,
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "event": self.event,
            "description": self.description,
            "reasoning_explanation": self.reasoning_explanation,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
        }
