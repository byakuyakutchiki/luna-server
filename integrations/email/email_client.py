"""
Luna Email Client - Envoi d'emails via SendGrid HTTP API

Utilise httpx (deja dans les deps) pour appeler l'API SendGrid.
Pas besoin du package sendgrid.

Le sender_name inclut le nom du souscripteur pour que le destinataire
sache de qui vient l'email. Ex: "Luna de Gwladys" <luna@yawatch.fr>

Usage:
    client = EmailClient.from_env()
    ok, details = await client.send(
        to="maman@gmail.com",
        subject="Bonjour de Gwladys",
        body_text="Maman, je t'envoie ce message via Luna.",
        subscriber_name="Gwladys",
    )
"""
import os
import re
import logging
import time
from typing import Dict, Any, Tuple, Optional

import httpx

from core.settings import get_settings

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r'^[^@\s\n\r]+@[^@\s\n\r]+\.[^@\s\n\r]{2,}$')

SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"


class EmailClient:
    """
    Client email via SendGrid HTTP API.

    Pattern identique a TwilioSMSClient: simple, is_configured, from_env().
    """

    def __init__(
        self,
        api_key: str,
        sender_address: str,
        default_sender_name: str = "Luna YAWatch",
    ):
        self.api_key = api_key
        self.sender_address = sender_address
        self.default_sender_name = default_sender_name

    @classmethod
    def from_env(cls) -> "EmailClient":
        api_key = os.getenv("SENDGRID_API_KEY", "")
        sender_address = os.getenv("LUNA_EMAIL_FROM", "")
        sender_name = os.getenv("LUNA_EMAIL_SENDER_NAME", "Luna YAWatch")

        if not api_key:
            logger.warning("SENDGRID_API_KEY non configuree — emails desactives")
        if not sender_address:
            logger.warning("LUNA_EMAIL_FROM non configuree — emails desactives")

        return cls(
            api_key=api_key,
            sender_address=sender_address,
            default_sender_name=sender_name,
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.sender_address)

    async def send(
        self,
        to: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        subscriber_name: Optional[str] = None,
        attachments: Optional[list] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Envoie un email via SendGrid.

        Le sender_name affiche "Luna de <subscriber_name>" pour que
        le destinataire sache au nom de qui Luna envoie.

        Args:
            to: Adresse email destinataire
            subject: Objet de l'email
            body_text: Contenu texte
            body_html: Contenu HTML (optionnel, genere depuis body_text si absent)
            subscriber_name: Nom du souscripteur (ex: "Gwladys")

        Returns:
            (True, {"status_code": 202}) ou (False, {"error": "..."})
        """
        settings = get_settings()
        if settings.foundation_test_mode:
            # Sauvegarde locale au lieu d'envoyer
            tmp_dir = "tmp/emails"
            os.makedirs(tmp_dir, exist_ok=True)
            safe_to = re.sub(r'[^a-zA-Z0-9@._-]', '_', to)
            filepath = f"{tmp_dir}/{int(time.time())}_{safe_to}.html"
            html_content = body_html or body_text.replace("\n", "<br>")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"<h1>To: {to}</h1><h2>Subject: {subject}</h2><hr>{html_content}")
            logger.info(f"[DRY RUN] Email to {to}: {subject} — saved to {filepath}")
            return True, {"simulated": True, "to": to, "subject": subject, "saved_to": filepath}

        if not self.is_configured:
            return False, {"error": "Email non configure (SENDGRID_API_KEY ou LUNA_EMAIL_FROM manquant)"}

        if not _EMAIL_RE.match(to):
            logger.warning("Adresse email invalide refusée: %r", to[:80])
            return False, {"error": "Adresse email invalide"}

        # Sender name = "Luna de Gwladys" si subscriber_name fourni
        if subscriber_name:
            sender_name = f"Luna de {subscriber_name}"
        else:
            sender_name = self.default_sender_name

        # Fallback HTML
        if not body_html:
            body_html = body_text.replace("\n", "<br>")

        payload = {
            "personalizations": [
                {
                    "to": [{"email": to}],
                    "subject": subject,
                }
            ],
            "from": {
                "email": self.sender_address,
                "name": sender_name,
            },
            "content": [
                {"type": "text/plain", "value": body_text},
                {"type": "text/html", "value": body_html},
            ],
        }

        # Attachments: [{"filename": "report.pdf", "filepath": "/path/to/file"}]
        if attachments:
            import base64
            sg_attachments = []
            for att in attachments:
                try:
                    with open(att["filepath"], "rb") as f:
                        content_b64 = base64.b64encode(f.read()).decode()
                    sg_attachments.append({
                        "content": content_b64,
                        "filename": att["filename"],
                        "type": att.get("type", "application/pdf"),
                        "disposition": "attachment",
                    })
                except Exception as e:
                    logger.warning(f"Failed to attach {att.get('filename')}: {e}")
            if sg_attachments:
                payload["attachments"] = sg_attachments

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(SENDGRID_API_URL, json=payload, headers=headers)

            if resp.status_code in (200, 201, 202):
                logger.info(f"Email envoye a {to} (sujet: {subject[:50]})")
                return True, {"status_code": resp.status_code}
            else:
                error_body = resp.text[:500]
                logger.error(f"SendGrid erreur {resp.status_code}: {error_body}")
                # Extraire le vrai message SendGrid (ex: "Maximum credits exceeded")
                sg_msg = ""
                try:
                    errs = resp.json().get("errors") or []
                    sg_msg = "; ".join(e.get("message", "") for e in errs if e.get("message"))
                except Exception:
                    pass
                return False, {
                    "error": sg_msg or f"SendGrid HTTP {resp.status_code}",
                    "status_code": resp.status_code,
                    "details": error_body,
                }

        except httpx.TimeoutException:
            logger.error(f"Timeout envoi email vers {to}")
            return False, {"error": "Timeout connexion SendGrid"}
        except Exception as e:
            logger.error(f"Erreur envoi email: {e}")
            return False, {"error": str(e)}

    async def send_for_tenant(
        self,
        tenant_id: int,
        redis_client,
        gmail_client,
        to: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        subscriber_name: Optional[str] = None,
        attachments: Optional[list] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Envoie un email pour un tenant specifique.

        Priorite:
        1. Gmail OAuth2 du tenant (si connecte)
        2. SendGrid global (fallback)
        """
        # Tente Gmail d'abord
        if gmail_client and gmail_client.is_configured and redis_client:
            integration = redis_client.get_email_integration(tenant_id)
            if integration and integration.get("service") == "gmail":
                return await gmail_client.send(
                    tenant_id=tenant_id,
                    redis_client=redis_client,
                    to=to,
                    subject=subject,
                    body_text=body_text,
                    body_html=body_html,
                    subscriber_name=subscriber_name,
                )

        # Fallback SendGrid
        if self.is_configured:
            return await self.send(
                to=to,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                subscriber_name=subscriber_name,
                attachments=attachments,
            )

        return False, {"error": "Aucun service email configure (ni Gmail OAuth ni SendGrid)"}

    def get_status(self) -> Dict[str, Any]:
        return {
            "configured": self.is_configured,
            "sender_address": self.sender_address if self.is_configured else None,
            "sender_name": self.default_sender_name,
        }
