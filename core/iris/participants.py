"""
core/iris/participants.py
Modèle de données, enums et matrice de permission pour Iris Workspace.
"""
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Literal
from pydantic import BaseModel, Field


class IrisRole(str, Enum):
    OWNER = "owner"
    TRUSTED = "trusted"
    GUEST = "guest"
    OBSERVER = "observer"


class IrisInvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class IrisParticipant(BaseModel):
    id: str = Field(..., description="UUID du participant")
    session_id: str = Field(..., description="UUID de la session Iris")
    user_type: IrisRole = Field(..., description="Rôle dans la session")
    display_name: str = Field(..., description="Nom affiché")
    avatar_url: Optional[str] = None
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)
    scope_project: Optional[str] = Field(
        None, description="Projet isolé pour ce participant (filtrage données)"
    )
    can_speak: bool = True
    can_project: bool = True
    can_act: bool = False
    can_invite: bool = False

    class Config:
        use_enum_values = True


class IrisInvitation(BaseModel):
    id: str = Field(..., description="UUID de l'invitation")
    session_id: str
    invited_by: str = Field(..., description="Participant ID du owner")
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Literal["trusted", "guest", "observer"] = "guest"
    scope_project: Optional[str] = None
    expires_at: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(hours=24)
    )
    used_at: Optional[datetime] = None
    status: IrisInvitationStatus = IrisInvitationStatus.PENDING

    class Config:
        use_enum_values = True


# ───────────────────────────────────────────────────────────────
# MATRICE DE PERMISSION — source de vérité
# ───────────────────────────────────────────────────────────────

PERMISSION_MATRIX = {
    # Action: {role: bool ou "validation_required"}
    "speak": {
        IrisRole.OWNER: True,
        IrisRole.TRUSTED: True,
        IrisRole.GUEST: True,
        IrisRole.OBSERVER: False,
    },
    "view_screen": {
        IrisRole.OWNER: True,
        IrisRole.TRUSTED: True,
        IrisRole.GUEST: True,
        IrisRole.OBSERVER: True,
    },
    "request_info_all": {
        IrisRole.OWNER: True,
        IrisRole.TRUSTED: False,
        IrisRole.GUEST: False,
        IrisRole.OBSERVER: False,
    },
    "request_info_project": {
        IrisRole.OWNER: True,
        IrisRole.TRUSTED: True,
        IrisRole.GUEST: True,
        IrisRole.OBSERVER: False,
    },
    "create_task": {
        IrisRole.OWNER: True,
        IrisRole.TRUSTED: True,
        IrisRole.GUEST: False,
        IrisRole.OBSERVER: False,
    },
    "assign_task": {
        IrisRole.OWNER: True,
        IrisRole.TRUSTED: True,
        IrisRole.GUEST: False,
        IrisRole.OBSERVER: False,
    },
    "send_email": {
        IrisRole.OWNER: True,
        IrisRole.TRUSTED: "validation_required",
        IrisRole.GUEST: False,
        IrisRole.OBSERVER: False,
    },
    "send_sms": {
        IrisRole.OWNER: True,
        IrisRole.TRUSTED: "validation_required",
        IrisRole.GUEST: False,
        IrisRole.OBSERVER: False,
    },
    "make_call": {
        IrisRole.OWNER: True,
        IrisRole.TRUSTED: "validation_required",
        IrisRole.GUEST: False,
        IrisRole.OBSERVER: False,
    },
    "sign_document": {
        IrisRole.OWNER: True,
        IrisRole.TRUSTED: False,
        IrisRole.GUEST: False,
        IrisRole.OBSERVER: False,
    },
    "payment": {
        IrisRole.OWNER: True,
        IrisRole.TRUSTED: False,
        IrisRole.GUEST: False,
        IrisRole.OBSERVER: False,
    },
    "invite": {
        IrisRole.OWNER: True,
        IrisRole.TRUSTED: False,
        IrisRole.GUEST: False,
        IrisRole.OBSERVER: False,
    },
    "exclude": {
        IrisRole.OWNER: True,
        IrisRole.TRUSTED: False,
        IrisRole.GUEST: False,
        IrisRole.OBSERVER: False,
    },
    "view_other_projects": {
        IrisRole.OWNER: True,
        IrisRole.TRUSTED: False,
        IrisRole.GUEST: False,
        IrisRole.OBSERVER: False,
    },
    "edit_permissions": {
        IrisRole.OWNER: True,
        IrisRole.TRUSTED: False,
        IrisRole.GUEST: False,
        IrisRole.OBSERVER: False,
    },
}


def check_permission(action: str, participant: IrisParticipant) -> bool:
    """Retourne True si l'action est autorisée, False sinon.
    Si 'validation_required', retourne False (bloqué jusqu'à validation owner)."""
    role = participant.user_type
    matrix = PERMISSION_MATRIX.get(action, {})
    result = matrix.get(role, False)
    if result == "validation_required":
        return False
    return bool(result)


def requires_owner_validation(action: str, participant: IrisParticipant) -> bool:
    """Retourne True si l'action nécessite une validation explicite du owner."""
    if participant.user_type == IrisRole.OWNER:
        return False
    role = participant.user_type
    matrix = PERMISSION_MATRIX.get(action, {})
    return matrix.get(role) == "validation_required"


# ───────────────────────────────────────────────────────────────
# FACTORY — Création de participants avec les bons flags
# ───────────────────────────────────────────────────────────────

def make_owner(session_id: str, display_name: str, participant_id: str) -> IrisParticipant:
    return IrisParticipant(
        id=participant_id,
        session_id=session_id,
        user_type=IrisRole.OWNER,
        display_name=display_name,
        can_speak=True,
        can_project=True,
        can_act=True,
        can_invite=True,
    )


def make_trusted(
    session_id: str, display_name: str, participant_id: str, scope_project: Optional[str] = None
) -> IrisParticipant:
    return IrisParticipant(
        id=participant_id,
        session_id=session_id,
        user_type=IrisRole.TRUSTED,
        display_name=display_name,
        scope_project=scope_project,
        can_speak=True,
        can_project=True,
        can_act=False,
        can_invite=False,
    )


def make_guest(
    session_id: str, display_name: str, participant_id: str, scope_project: Optional[str] = None
) -> IrisParticipant:
    return IrisParticipant(
        id=participant_id,
        session_id=session_id,
        user_type=IrisRole.GUEST,
        display_name=display_name,
        scope_project=scope_project,
        can_speak=True,
        can_project=True,
        can_act=False,
        can_invite=False,
    )


def make_observer(session_id: str, display_name: str, participant_id: str) -> IrisParticipant:
    return IrisParticipant(
        id=participant_id,
        session_id=session_id,
        user_type=IrisRole.OBSERVER,
        display_name=display_name,
        can_speak=False,
        can_project=False,
        can_act=False,
        can_invite=False,
    )
