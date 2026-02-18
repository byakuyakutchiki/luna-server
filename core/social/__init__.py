"""Module social : interactions entre souscripteurs (amis, DMs, profils publics)."""

from .redis_ops import SocialRedisOps

__all__ = ["SocialRedisOps"]
