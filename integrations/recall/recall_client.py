"""
Recall.ai Client — Bot de réunion pour Zoom, Google Meet, Microsoft Teams, Webex.

Le bot rejoint la réunion, transcrit les échanges avec diarisation des locuteurs,
et renvoie les événements en temps réel via webhook.

Variables d'environnement :
    RECALL_API_KEY       — clé API Recall.ai (obligatoire)
    RECALL_REGION        — us-east-1 (défaut) ou eu-west-2
    RECALL_WEBHOOK_URL   — URL publique du serveur (défaut: VOICE_CALLBACK_URL)
    RECALL_TRANSCRIPTION — fournisseur ASR: deepgram (défaut), assembly_ai, meeting_captions
"""
import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

RECALL_REGIONS = {
    "us-east-1": "https://us-east-1.recall.ai/api/v1",
    "eu-west-2":  "https://eu-west-2.recall.ai/api/v1",
}

# Codes de statut Recall.ai (ordre chronologique)
STATUS_LABELS = {
    "ready":                        "En attente",
    "joining_call":                 "Connexion...",
    "in_waiting_room":              "Salle d'attente",
    "in_call_not_recording":        "Connecté (en attente d'autorisation)",
    "recording_permission_allowed": "Autorisation accordée",
    "in_call_recording":            "En réunion — transcription active",
    "call_ended":                   "Réunion terminée",
    "done":                         "Traitement terminé",
    "fatal":                        "Erreur fatale",
}

PLATFORM_NAMES = {
    "zoom":         "Zoom",
    "google_meet":  "Google Meet",
    "teams":        "Microsoft Teams",
    "webex":        "Webex",
    "gotomeeting":  "GoToMeeting",
    "ringcentral":  "RingCentral",
    "unknown":      "Visioconférence",
}


def detect_platform(url: str) -> str:
    u = url.lower()
    if "zoom.us" in u:                                      return "zoom"
    if "meet.google.com" in u:                              return "google_meet"
    if "teams.microsoft.com" in u or "teams.live.com" in u: return "teams"
    if "webex.com" in u:                                    return "webex"
    if "gotomeeting.com" in u:                              return "gotomeeting"
    if "ringcentral.com" in u:                              return "ringcentral"
    return "unknown"


def format_transcript(segments: List[Dict]) -> str:
    """
    Formate la transcription Recall.ai en texte lisible avec horodatage et locuteur.

    Ex: [02:34] Jean Dupont : On valide le budget Q3.
    """
    lines = []
    for seg in segments:
        speaker = seg.get("speaker") or "Locuteur inconnu"
        words = seg.get("words") or []
        if not words:
            continue
        start_s = words[0].get("start_time", 0) or 0
        minutes, seconds = divmod(int(start_s), 60)
        timestamp = f"{minutes:02d}:{seconds:02d}"
        text = " ".join(w.get("text", "") for w in words).strip()
        if text:
            lines.append(f"[{timestamp}] {speaker} : {text}")
    return "\n".join(lines)


class RecallClient:
    """Client REST synchrone pour l'API Recall.ai v1."""

    def __init__(
        self,
        api_key: str,
        webhook_url: str = "",
        region: str = "us-east-1",
        transcription_provider: str = "deepgram",
    ):
        self.api_key = api_key
        self.webhook_url = webhook_url.rstrip("/")
        self.base_url = RECALL_REGIONS.get(region, RECALL_REGIONS["us-east-1"])
        self.transcription_provider = transcription_provider

    @classmethod
    def from_env(cls) -> "RecallClient":
        api_key = os.getenv("RECALL_API_KEY", "")
        webhook_url = os.getenv("RECALL_WEBHOOK_URL") or os.getenv("VOICE_CALLBACK_URL", "")
        region = os.getenv("RECALL_REGION", "us-east-1")
        provider = os.getenv("RECALL_TRANSCRIPTION", "deepgram")
        if not api_key:
            logger.warning("RECALL_API_KEY manquant — fonctionnalité réunion désactivée")
        return cls(api_key=api_key, webhook_url=webhook_url, region=region, transcription_provider=provider)

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.webhook_url)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # API synchrone
    # ------------------------------------------------------------------

    def create_bot(
        self,
        meeting_url: str,
        bot_name: str = "Luna (YAWatch)",
        recording_mode: str = "audio_only",
    ) -> Tuple[bool, Dict[str, Any]]:
        """Crée un bot qui rejoint la réunion et transcrit les échanges."""
        payload: Dict[str, Any] = {
            "meeting_url": meeting_url,
            "bot_name": bot_name,
            "recording_mode": recording_mode,
            "transcription_options": {
                "provider": self.transcription_provider,
            },
            "webhook_url": f"{self.webhook_url}/api/webhooks/recall",
        }
        # Transcription temps réel vers le même webhook
        if self.webhook_url:
            payload["real_time_transcription"] = {
                "partial_results": False,
                "destination_url": f"{self.webhook_url}/api/webhooks/recall",
            }
        try:
            r = httpx.post(
                f"{self.base_url}/bot/",
                json=payload,
                headers=self._headers(),
                timeout=30.0,
            )
            r.raise_for_status()
            data = r.json()
            bot_id = data.get("id", "")
            logger.info(f"Recall bot créé : {bot_id} → {meeting_url}")
            return True, data
        except httpx.HTTPStatusError as e:
            detail = {}
            try:
                detail = e.response.json()
            except Exception:
                pass
            logger.error(f"Recall create_bot HTTP {e.response.status_code}: {detail}")
            return False, {"error": f"HTTP {e.response.status_code}", "detail": detail}
        except Exception as e:
            logger.error(f"Recall create_bot: {e}")
            return False, {"error": str(e)}

    def stop_bot(self, bot_id: str) -> bool:
        """Fait quitter la réunion au bot."""
        try:
            r = httpx.post(
                f"{self.base_url}/bot/{bot_id}/leave_call/",
                headers=self._headers(),
                timeout=15.0,
            )
            r.raise_for_status()
            logger.info(f"Recall bot {bot_id} arrêté")
            return True
        except Exception as e:
            logger.warning(f"Recall stop_bot {bot_id}: {e}")
            return False

    def get_bot(self, bot_id: str) -> Dict[str, Any]:
        """Retourne l'état actuel du bot."""
        try:
            r = httpx.get(
                f"{self.base_url}/bot/{bot_id}/",
                headers=self._headers(),
                timeout=10.0,
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"Recall get_bot {bot_id}: {e}")
            return {}

    def get_transcript(self, bot_id: str) -> List[Dict]:
        """Récupère la transcription complète après la réunion."""
        try:
            r = httpx.get(
                f"{self.base_url}/bot/{bot_id}/transcript/",
                headers=self._headers(),
                timeout=60.0,
            )
            r.raise_for_status()
            return r.json() or []
        except Exception as e:
            logger.error(f"Recall get_transcript {bot_id}: {e}")
            return []

    # ------------------------------------------------------------------
    # Wrappers async (run_in_executor)
    # ------------------------------------------------------------------

    async def create_bot_async(
        self,
        meeting_url: str,
        bot_name: str = "Luna (YAWatch)",
        recording_mode: str = "audio_only",
    ) -> Tuple[bool, Dict[str, Any]]:
        loop = asyncio.get_event_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, lambda: self.create_bot(meeting_url, bot_name, recording_mode)),
            timeout=30.0,
        )

    async def stop_bot_async(self, bot_id: str) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.stop_bot, bot_id)

    async def get_bot_async(self, bot_id: str) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_bot, bot_id)

    async def get_transcript_async(self, bot_id: str) -> List[Dict]:
        loop = asyncio.get_event_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, self.get_transcript, bot_id),
            timeout=60.0,
        )
