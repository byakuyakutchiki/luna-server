"""
Luna Memory Module - Gestion mémoire Redis

Ce module gère la mémoire persistante de Luna:
- Conversations avec les contacts de confiance
- Instructions quotidiennes du souscripteur
- État des tâches en cours
- Historique des actions
"""

from .redis_client import RedisClient, get_redis_client
from .memory_manager import MemoryManager
from .schemas import (
    Conversation,
    Message,
    Instruction,
    TaskState,
    MemoryQuota,
    SubscriberProfile,
)

__all__ = [
    "RedisClient",
    "get_redis_client",
    "MemoryManager",
    "Conversation",
    "Message",
    "Instruction",
    "TaskState",
    "MemoryQuota",
    "SubscriberProfile",
]
