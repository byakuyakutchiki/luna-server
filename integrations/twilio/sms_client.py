"""
Luna Twilio SMS Client - Client SMS pour Luna

Client léger utilisé côté Luna pour envoyer des SMS
via l'API Twilio directement.

Usage:
    client = TwilioSMSClient.from_env()
    result = client.send("0612345678", "Bonjour depuis Luna !")
"""
import os
import logging
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class TwilioSMSClient:
    """
    Client SMS Twilio pour Luna.

    Gère:
    - Envoi de SMS
    - Normalisation des numéros français
    - Estimation des segments
    - Validation des webhooks
    """

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
        status_callback_url: Optional[str] = None,
    ):
        """
        Args:
            account_sid: Twilio Account SID
            auth_token: Twilio Auth Token
            from_number: Numéro Twilio d'envoi (E.164)
            status_callback_url: URL callback pour statut de livraison
        """
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.status_callback_url = status_callback_url

        self._client = None
        self._validator = None

    @classmethod
    def from_env(cls) -> "TwilioSMSClient":
        """
        Crée un client depuis les variables d'environnement.

        Variables requises:
            TWILIO_ACCOUNT_SID
            TWILIO_AUTH_TOKEN
            TWILIO_SMS_FROM
            TWILIO_STATUS_CALLBACK_URL (optionnel)
        """
        account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        from_number = os.getenv("TWILIO_SMS_FROM", "")
        callback_url = os.getenv("TWILIO_STATUS_CALLBACK_URL")

        if not all([account_sid, auth_token, from_number]):
            logger.warning(
                "Twilio non configuré. Variables manquantes: "
                + ", ".join(
                    v for v, val in [
                        ("TWILIO_ACCOUNT_SID", account_sid),
                        ("TWILIO_AUTH_TOKEN", auth_token),
                        ("TWILIO_SMS_FROM", from_number),
                    ]
                    if not val
                )
            )

        return cls(
            account_sid=account_sid,
            auth_token=auth_token,
            from_number=from_number,
            status_callback_url=callback_url,
        )

    @property
    def is_configured(self) -> bool:
        """Vérifie si Twilio est correctement configuré"""
        return all([self.account_sid, self.auth_token, self.from_number])

    @property
    def client(self):
        """Client Twilio (lazy init)"""
        if self._client is None:
            from twilio.rest import Client
            self._client = Client(self.account_sid, self.auth_token)
        return self._client

    @property
    def validator(self):
        """Validateur de webhooks (lazy init)"""
        if self._validator is None:
            from twilio.request_validator import RequestValidator
            self._validator = RequestValidator(self.auth_token)
        return self._validator

    def send(
        self,
        to: str,
        body: str,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Envoie un SMS.

        Args:
            to: Numéro destinataire (format FR ou E.164)
            body: Contenu du message

        Returns:
            Tuple (succès, détails)
            Si succès: (True, {"sid": "...", "status": "...", "segments": 1})
            Si échec: (False, {"error": "...", "code": 0})
        """
        if not self.is_configured:
            return False, {"error": "Twilio non configuré", "code": 0}

        # Normalise le numéro
        to_normalized = self.normalize_phone(to)

        try:
            kwargs = {
                "body": body,
                "from_": self.from_number,
                "to": to_normalized,
            }

            if self.status_callback_url:
                kwargs["status_callback"] = self.status_callback_url

            message = self.client.messages.create(**kwargs)

            logger.info(f"SMS envoyé: {message.sid} -> {to_normalized}")

            return True, {
                "sid": message.sid,
                "status": message.status,
                "segments": int(message.num_segments) if message.num_segments else 1,
            }

        except Exception as e:
            error_code = getattr(e, "code", 0)
            error_msg = str(e)
            logger.error(f"Erreur envoi SMS: [{error_code}] {error_msg}")

            return False, {
                "error": error_msg,
                "code": error_code,
            }

    async def send_async(
        self,
        to: str,
        body: str,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Version async de send() avec timeout 15s.
        Wraps l'appel synchrone Twilio.
        """
        import asyncio
        loop = asyncio.get_event_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(None, self.send, to, body),
                timeout=15.0,
            )
        except asyncio.TimeoutError:
            logger.error(f"Timeout envoi SMS vers {to}")
            return False, {"error": "Timeout connexion Twilio"}

    def validate_webhook(
        self,
        signature: str,
        url: str,
        params: Dict[str, str],
    ) -> bool:
        """
        Valide la signature d'un webhook Twilio.

        Args:
            signature: Header X-Twilio-Signature
            url: URL complète du webhook
            params: Paramètres POST du webhook

        Returns:
            True si la signature est valide
        """
        if not self.is_configured:
            return False

        try:
            return self.validator.validate(url, params, signature)
        except Exception as e:
            logger.error(f"Erreur validation webhook: {e}")
            return False

    @staticmethod
    def normalize_phone(phone: str) -> str:
        """
        Normalise un numéro vers le format E.164.

        Exemples:
            "0612345678"    -> "+33612345678"
            "06 12 34 56 78" -> "+33612345678"
            "+33612345678"   -> "+33612345678"

        Args:
            phone: Numéro en format libre

        Returns:
            Numéro au format E.164
        """
        # Supprime espaces, tirets, parenthèses, points
        cleaned = "".join(c for c in phone if c.isdigit() or c == "+")

        # Format français: 0X -> +33X
        if cleaned.startswith("0") and len(cleaned) == 10:
            return "+33" + cleaned[1:]

        # Déjà en format international
        if cleaned.startswith("+"):
            return cleaned

        # Ajoute le + si manquant mais commence par un indicatif
        if cleaned.startswith("33") and len(cleaned) >= 11:
            return "+" + cleaned

        # Par défaut, suppose français
        return "+" + cleaned

    @staticmethod
    def estimate_segments(body: str) -> int:
        """
        Estime le nombre de segments SMS.

        GSM-7: 160 chars (1 segment), 153 chars/segment (multi)
        Unicode: 70 chars (1 segment), 67 chars/segment (multi)
        """
        gsm_basic = set(
            '@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ '
            '!"#¤%&\'()*+,-./0123456789:;<=>?¡'
            'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            'ÄÖÑÜÉabcdefghijklmnopqrstuvwxyz'
            'äöñüà'
        )

        is_gsm = all(c in gsm_basic for c in body)
        length = len(body)

        if is_gsm:
            return 1 if length <= 160 else -(-length // 153)
        else:
            return 1 if length <= 70 else -(-length // 67)

    def get_status(self) -> Dict[str, Any]:
        """Retourne le statut de configuration"""
        return {
            "configured": self.is_configured,
            "from_number": self.from_number if self.is_configured else None,
            "has_callback": bool(self.status_callback_url),
        }
