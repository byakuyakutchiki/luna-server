"""
Simli AI — Avatar cinematique avec lip-sync WebRTC.
Alternative a Tavus pour les conversations video.
"""
from .ws_handler import handle_simli_session
from .luna_schedule import get_current_scene, get_enriched_system_prompt, get_current_emotion_id

__all__ = [
    "handle_simli_session",
    "get_current_scene",
    "get_enriched_system_prompt",
    "get_current_emotion_id",
]
