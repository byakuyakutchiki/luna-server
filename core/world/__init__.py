"""Monde de Luna — Couche sociale interactive.

Module dédié à la socialisation dans le Monde de Luna :
- Privacy / Présence visible-invisible
- Amis et invitations dans le monde
- Avatars personnalisables
- Chat temps réel entre utilisateurs dans le même monde
- Notifications in-world
"""

from .routes import world_router

__all__ = ["world_router"]
