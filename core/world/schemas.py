"""Schémas Pydantic pour le Monde de Luna — couche sociale."""

from typing import Optional, Literal
from pydantic import BaseModel, Field


class PrivacySettings(BaseModel):
    """Paramètres de confidentialité utilisateur."""
    visible_on_map: bool = Field(default=True, description="Visible sur la carte mondiale")
    visible_in_world: bool = Field(default=True, description="Visible dans le Monde de Luna")
    accept_friend_requests: bool = Field(default=True, description="Accepter les demandes d'amis")
    accept_world_invites: bool = Field(default=True, description="Accepter les invitations monde")
    approximate_location_only: bool = Field(default=True, description="Localisation approximative uniquement")
    total_invisible: bool = Field(default=False, description="Mode invisible total")


class AvatarConfig(BaseModel):
    """Configuration avatar utilisateur."""
    gender: Literal["male", "female", "neutral"] = Field(default="neutral")
    body_style: str = Field(default="standard", description="Style de corps (standard, slim, chibi...)")
    hair: str = Field(default="default", description="Style de cheveux")
    outfit: str = Field(default="default", description="Tenue équipée")
    aura: str = Field(default="none", description="Aura visuelle")
    frame: str = Field(default="none", description="Cadre profil")
    primary_color: str = Field(default="#a78bfa", description="Couleur principale hex")
    badge_featured: str = Field(default="", description="ID du badge principal affiché")
    face_expression: str = Field(default="smile", description="Expression faciale")


class WorldInvitationCreate(BaseModel):
    """Création d'une invitation dans le monde."""
    target_tid: int = Field(..., description="ID du destinataire")
    message: Optional[str] = Field(default=None, max_length=200, description="Message personnalisé")


class WorldInvitationResponse(BaseModel):
    """Réponse à une invitation (accepter/refuser)."""
    invitation_id: str = Field(..., description="ID de l'invitation")
    action: Literal["accept", "decline"] = Field(..., description="accept ou decline")


class WorldChatMessage(BaseModel):
    """Message dans le chat du monde."""
    text: str = Field(..., min_length=1, max_length=300, description="Contenu du message")


class WorldPresenceUpdate(BaseModel):
    """Mise à jour de la présence dans le monde."""
    world_id: str = Field(default="world1", description="Identifiant du monde")
    x: Optional[float] = Field(default=None, description="Position X approximative")
    y: Optional[float] = Field(default=None, description="Position Y approximative")
    status: Literal["online", "away", "playing"] = Field(default="online")
