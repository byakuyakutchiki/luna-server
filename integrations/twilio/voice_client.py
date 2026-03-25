"""
Luna Twilio Voice Client - Client appels vocaux pour Luna

Lance des appels sortants via Twilio Voice.
L'appel connecte le destinataire a Luna via OpenAI Realtime API
grace a un WebSocket Media Stream.

Usage:
    client = TwilioVoiceClient.from_env()
    success, data = await client.initiate_call("+33612345678")
"""
import os
import logging
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class TwilioVoiceClient:
    """
    Client Twilio Voice pour Luna.

    Gere:
    - Lancement d'appels vocaux sortants
    - Generation du TwiML pour Media Streams
    - Normalisation des numeros (reutilise sms_client)
    """

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
        voice_callback_url: str = "",
    ):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.voice_callback_url = voice_callback_url
        self._client = None

    @classmethod
    def from_env(cls) -> "TwilioVoiceClient":
        """
        Cree un client depuis les variables d'environnement.

        Variables requises:
            TWILIO_ACCOUNT_SID
            TWILIO_AUTH_TOKEN
            TWILIO_PHONE_NUMBER
            VOICE_CALLBACK_URL (URL publique du serveur)
        """
        account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        from_number = os.getenv("TWILIO_PHONE_NUMBER", "")
        voice_callback_url = os.getenv("VOICE_CALLBACK_URL", "")

        if not all([account_sid, auth_token, from_number]):
            logger.warning(
                "Twilio Voice non configure. Variables manquantes: "
                + ", ".join(
                    v for v, val in [
                        ("TWILIO_ACCOUNT_SID", account_sid),
                        ("TWILIO_AUTH_TOKEN", auth_token),
                        ("TWILIO_PHONE_NUMBER", from_number),
                    ]
                    if not val
                )
            )

        if not voice_callback_url:
            logger.warning("VOICE_CALLBACK_URL manquant - les appels vocaux ne fonctionneront pas")

        return cls(
            account_sid=account_sid,
            auth_token=auth_token,
            from_number=from_number,
            voice_callback_url=voice_callback_url,
        )

    @property
    def is_configured(self) -> bool:
        return all([self.account_sid, self.auth_token, self.from_number, self.voice_callback_url])

    @property
    def client(self):
        if self._client is None:
            from twilio.rest import Client
            self._client = Client(self.account_sid, self.auth_token)
        return self._client

    @property
    def twiml_url(self) -> str:
        """URL du endpoint TwiML que Twilio va fetcher quand l'appel est decroche."""
        return f"{self.voice_callback_url}/api/voice-call/twiml"

    def initiate_call(self, to: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Lance un appel vocal sortant.

        Twilio appelle le destinataire, et quand il decroche,
        fetche le TwiML qui ouvre un Media Stream vers notre serveur.

        Args:
            to: Numero destinataire (format FR ou E.164)

        Returns:
            (True, {"call_sid": "...", "status": "..."}) ou (False, {"error": "..."})
        """
        if not self.is_configured:
            return False, {"error": "Twilio Voice non configure"}

        from integrations.twilio.sms_client import TwilioSMSClient
        to_normalized = TwilioSMSClient.normalize_phone(to)

        try:
            call = self.client.calls.create(
                to=to_normalized,
                from_=self.from_number,
                url=self.twiml_url,
            )
            logger.info(f"Appel vocal lance: {call.sid} -> {to_normalized}")
            return True, {
                "call_sid": call.sid,
                "status": call.status,
            }
        except Exception as e:
            error_code = getattr(e, "code", 0)
            error_msg = str(e)
            logger.error(f"Erreur appel vocal: [{error_code}] {error_msg}")
            return False, {"error": error_msg, "code": error_code}

    # Semaphore: max appels Twilio simultanes (evite rate limit 429)
    _call_semaphore = None

    @classmethod
    def _get_call_semaphore(cls):
        if cls._call_semaphore is None:
            import asyncio
            max_calls = int(os.getenv("TWILIO_MAX_CONCURRENT_CALLS", "20"))
            cls._call_semaphore = asyncio.Semaphore(max_calls)
        return cls._call_semaphore

    async def initiate_call_async(self, to: str) -> Tuple[bool, Dict[str, Any]]:
        """Version async de initiate_call() avec timeout 15s et backpressure."""
        import asyncio
        sem = self._get_call_semaphore()
        try:
            async with sem:
                loop = asyncio.get_event_loop()
                return await asyncio.wait_for(
                    loop.run_in_executor(None, self.initiate_call, to),
                    timeout=15.0,
                )
        except asyncio.TimeoutError:
            logger.error(f"Timeout appel vocal vers {to}")
            return False, {"error": "Timeout connexion Twilio"}

    def generate_twiml(self, call_sid: str = "") -> str:
        """
        Genere le TwiML qui dit a Twilio d'ouvrir un Media Stream.

        Args:
            call_sid: CallSid Twilio pour matcher les parametres d'appel.

        Returns:
            TwiML XML string
        """
        from twilio.twiml.voice_response import VoiceResponse, Connect

        response = VoiceResponse()
        response.say("Un instant, Luna arrive.", language="fr-FR")
        connect = Connect()
        ws_url = self.voice_callback_url.replace("https://", "wss://")
        stream_url = f"{ws_url}/api/voice-call/media-stream"
        if call_sid:
            from urllib.parse import quote
            stream_url += f"?call_sid={quote(call_sid)}"
        connect.stream(url=stream_url)
        response.append(connect)
        return str(response)
