"""
MeetingBaas Client — Bot de réunion pour Zoom, Google Meet, Microsoft Teams.

Alternative à Recall.ai, plus accessible aux développeurs indépendants.
Inscriptions sur meetingbaas.com (accepte les emails personnels).

Variables d'environnement :
    MEETINGBAAS_API_KEY   — clé API MeetingBaas (obligatoire)
    MEETINGBAAS_WEBHOOK_URL — URL publique du serveur (défaut: VOICE_CALLBACK_URL)
    MEETINGBAAS_BOT_NAME  — nom affiché dans la réunion (défaut: "Luna (YAWatch)")
"""
import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

MEETINGBAAS_API_URL = "https://api.meetingbaas.com/v2"

STATUS_LABELS = {
    "waiting":          "En attente",
    "joining":          "Connexion...",
    "joined":           "Connecté — transcription active",
    "recording":        "En réunion — enregistrement actif",
    "leaving":          "Déconnexion...",
    "done":             "Réunion terminée",
    "failed":           "Erreur",
    # Recall-compat aliases (au cas où)
    "ready":                        "En attente",
    "joining_call":                 "Connexion...",
    "in_waiting_room":              "Salle d'attente",
    "in_call_not_recording":        "Connecté",
    "in_call_recording":            "En réunion — transcription active",
    "call_ended":                   "Réunion terminée",
    "fatal":                        "Erreur fatale",
}

PLATFORM_NAMES = {
    "zoom":        "Zoom",
    "google_meet": "Google Meet",
    "teams":       "Microsoft Teams",
    "webex":       "Webex",
    "gotomeeting": "GoToMeeting",
    "ringcentral": "RingCentral",
    "unknown":     "Visioconférence",
}


def detect_platform(url: str) -> str:
    u = url.lower()
    if "zoom.us" in u:                                       return "zoom"
    if "meet.google.com" in u:                               return "google_meet"
    if "teams.microsoft.com" in u or "teams.live.com" in u:  return "teams"
    if "webex.com" in u:                                     return "webex"
    if "gotomeeting.com" in u:                               return "gotomeeting"
    if "ringcentral.com" in u:                               return "ringcentral"
    return "unknown"


def format_transcript(segments: List[Dict]) -> str:
    """
    Formate la transcription en texte lisible avec horodatage et locuteur.
    Compatible Recall.ai et MeetingBaas (les deux formats).

    Ex: [02:34] Jean Dupont : On valide le budget Q3.
    """
    lines = []
    for seg in segments:
        # MeetingBaas format
        speaker = seg.get("speaker") or seg.get("user_name") or "Locuteur inconnu"
        words = seg.get("words") or []
        # Fallback: segment avec juste "text" et "start_time"
        if not words and seg.get("text"):
            start_s = seg.get("start_time", 0) or 0
            text = seg.get("text", "").strip()
        else:
            if not words:
                continue
            start_s = words[0].get("start_time", 0) or 0
            text = " ".join(w.get("text", "") for w in words).strip()
        if not text:
            continue
        minutes, seconds = divmod(int(start_s), 60)
        lines.append(f"[{minutes:02d}:{seconds:02d}] {speaker} : {text}")
    return "\n".join(lines)


class MeetingBaasClient:
    """Client REST synchrone pour l'API MeetingBaas."""

    def __init__(self, api_key: str, webhook_url: str = "", bot_name: str = "Luna (YAWatch)"):
        self.api_key = api_key
        self.webhook_url = webhook_url.rstrip("/")
        self.default_bot_name = bot_name

    @classmethod
    def from_env(cls) -> "MeetingBaasClient":
        api_key = os.getenv("MEETINGBAAS_API_KEY", "")
        webhook_url = (
            os.getenv("MEETINGBAAS_WEBHOOK_URL")
            or os.getenv("VOICE_CALLBACK_URL", "")
        )
        bot_name = os.getenv("MEETINGBAAS_BOT_NAME", "Luna (YAWatch)")
        if not api_key:
            logger.warning("MEETINGBAAS_API_KEY manquant — fonctionnalité réunion désactivée")
        return cls(api_key=api_key, webhook_url=webhook_url, bot_name=bot_name)

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.webhook_url)

    def _headers(self) -> Dict[str, str]:
        return {
            "x-meeting-baas-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # API synchrone
    # ------------------------------------------------------------------

    def create_bot(
        self,
        meeting_url: str,
        bot_name: Optional[str] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Crée un bot qui rejoint la réunion et transcrit les échanges."""
        payload: Dict[str, Any] = {
            "meeting_url": meeting_url,
            "bot_name": bot_name or self.default_bot_name,
            "recording_mode": "audio_only",
            "webhook_url": f"{self.webhook_url}/api/webhooks/meetingbaas",
            "speech_to_text": {
                "provider": "Default",
            },
        }
        try:
            r = httpx.post(
                f"{MEETINGBAAS_API_URL}/bots",
                json=payload,
                headers=self._headers(),
                timeout=30.0,
            )
            r.raise_for_status()
            envelope = r.json()
            # v2: {"success": true, "data": {"bot_id": "..."}}
            inner = envelope.get("data", envelope)
            bot_id = inner.get("bot_id") or inner.get("id", "")
            logger.info(f"MeetingBaas bot créé : {bot_id} → {meeting_url}")
            return True, {**inner, "id": bot_id, "bot_id": bot_id}
        except httpx.HTTPStatusError as e:
            detail = {}
            try:
                detail = e.response.json()
            except Exception:
                pass
            logger.error(f"MeetingBaas create_bot HTTP {e.response.status_code}: {detail}")
            return False, {"error": f"HTTP {e.response.status_code}", "detail": detail}
        except Exception as e:
            logger.error(f"MeetingBaas create_bot: {e}")
            return False, {"error": str(e)}

    def stop_bot(self, bot_id: str) -> bool:
        """Fait quitter la réunion au bot (v2: POST /bots/{id}/leave)."""
        try:
            r = httpx.post(
                f"{MEETINGBAAS_API_URL}/bots/{bot_id}/leave",
                headers=self._headers(),
                timeout=15.0,
            )
            r.raise_for_status()
            logger.info(f"MeetingBaas bot {bot_id} arrêté")
            return True
        except Exception as e:
            logger.warning(f"MeetingBaas stop_bot {bot_id}: {e}")
            return False

    def get_bot(self, bot_id: str) -> Dict[str, Any]:
        """Retourne l'état actuel du bot (v2: status à plat dans data)."""
        try:
            r = httpx.get(
                f"{MEETINGBAAS_API_URL}/bots/{bot_id}",
                headers=self._headers(),
                timeout=10.0,
            )
            r.raise_for_status()
            envelope = r.json()
            # v2: {"success": true, "data": {...}}
            return envelope.get("data", envelope)
        except Exception as e:
            logger.error(f"MeetingBaas get_bot {bot_id}: {e}")
            return {}

    def get_transcript(self, bot_id: str) -> List[Dict]:
        """Récupère la transcription via get_bot (v2: pas d'endpoint /transcript séparé)."""
        try:
            bot_data = self.get_bot(bot_id)
            # v2: transcription est dans data.transcription (liste de segments ou null)
            transcript = bot_data.get("transcription") or bot_data.get("raw_transcription") or []
            if isinstance(transcript, list):
                return transcript
            return []
        except Exception as e:
            logger.error(f"MeetingBaas get_transcript {bot_id}: {e}")
            return []

    # ------------------------------------------------------------------
    # Wrappers async
    # ------------------------------------------------------------------

    async def create_bot_async(
        self,
        meeting_url: str,
        bot_name: Optional[str] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        loop = asyncio.get_event_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, lambda: self.create_bot(meeting_url, bot_name)),
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
