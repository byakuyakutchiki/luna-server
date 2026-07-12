"""
Luna Gmail Client - Envoi d'emails via Gmail API avec OAuth2

Chaque tenant (proprietaire Luna) connecte son propre Gmail.
Les emails partent depuis l'adresse du proprietaire, pas d'une adresse tierce.

Flow OAuth2:
1. Admin appelle get_auth_url(tenant_id) -> redirige vers Google
2. Proprietaire autorise Luna (scope gmail.send)
3. Google redirige vers callback avec code
4. handle_callback() echange code -> tokens, stocke dans Redis
5. send() charge tokens, refresh si expire, envoie via Gmail API

Usage:
    client = GmailClient(client_id, client_secret, redirect_uri)
    # Etape 1: Obtenir l'URL d'auth
    url = client.get_auth_url(tenant_id=2)
    # Etape 2: Apres callback
    result = await client.handle_callback(code, state, redis_client)
    # Etape 3: Envoyer un email
    ok, details = await client.send(tenant_id=2, redis_client, to, subject, body)
"""
import os
import json
import hmac
import hashlib
import logging
import asyncio
import base64
import time
from typing import Dict, Any, Tuple, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

import httpx

from core.settings import get_settings

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
# gmail.send (envoi) + userinfo.email (lire l'adresse du compte, requise pour le FROM)
GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/userinfo.email"


class GmailClient:
    """
    Client Gmail OAuth2 per-tenant.
    Chaque tenant a ses propres tokens stockes dans Redis.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        state_secret: str = "",
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        # Secret pour signer le state (anti-CSRF)
        self.state_secret = state_secret or client_secret[:16]

    @classmethod
    def from_env(cls, base_url: str = "") -> "GmailClient":
        client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
        client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
        redirect_uri = os.getenv(
            "GOOGLE_OAUTH_REDIRECT_URI",
            f"{base_url}/api/email/oauth/callback" if base_url else "",
        )
        state_secret = os.getenv("JWT_SECRET_KEY", "")[:16]

        if not client_id or not client_secret:
            logger.info("Gmail OAuth2 non configure (GOOGLE_OAUTH_CLIENT_ID manquant)")

        return cls(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            state_secret=state_secret,
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.redirect_uri)

    # =========================================================================
    # OAUTH2 FLOW
    # =========================================================================

    def get_auth_url(self, tenant_id: int) -> str:
        """
        Genere l'URL de consentement Google pour un tenant.

        Le state contient le tenant_id signe (anti-CSRF).
        """
        state = self._sign_state(tenant_id)
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": GMAIL_SCOPE,
            "access_type": "offline",  # Pour obtenir un refresh_token
            "prompt": "consent",  # Force le consentement (sinon pas de refresh_token)
            "state": state,
        }
        query = "&".join(f"{k}={httpx.URL('', params={k: v}).params[k]}" for k, v in params.items())
        return f"{GOOGLE_AUTH_URL}?{query}"

    async def handle_callback(
        self,
        code: str,
        state: str,
        redis_client,
    ) -> Dict[str, Any]:
        """
        Gere le callback OAuth2 de Google.

        Echange le code contre des tokens, recupere l'email,
        et stocke le tout dans Redis.

        Returns:
            {"success": True, "tenant_id": X, "email": "..."} ou
            {"success": False, "error": "..."}
        """
        # Verifie le state
        tenant_id = self._verify_state(state)
        if tenant_id is None:
            return {"success": False, "error": "State invalide (CSRF)"}

        # Echange code -> tokens
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(GOOGLE_TOKEN_URL, data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.redirect_uri,
                })

            if resp.status_code != 200:
                logger.error(f"Gmail token exchange failed: {resp.status_code} {resp.text[:200]}")
                return {"success": False, "error": f"Google token error: {resp.status_code}"}

            tokens = resp.json()
            access_token = tokens.get("access_token", "")
            refresh_token = tokens.get("refresh_token", "")
            expires_in = tokens.get("expires_in", 3600)

            if not access_token:
                return {"success": False, "error": "Pas d'access_token dans la reponse Google"}

        except Exception as e:
            logger.error(f"Gmail token exchange error: {e}")
            return {"success": False, "error": str(e)}

        # Recupere l'email de l'utilisateur
        email = await self._get_user_email(access_token)
        if not email:
            return {"success": False, "error": "Impossible de recuperer l'email du compte Google"}

        # Stocke dans Redis
        integration_data = {
            "service": "gmail",
            "email": email,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_expiry": str(int(datetime.utcnow().timestamp()) + expires_in),
            "connected_at": datetime.utcnow().isoformat(),
        }

        try:
            redis_client.save_email_integration(tenant_id, integration_data)
        except Exception as e:
            logger.error(f"Redis save email integration failed: {e}")
            return {"success": False, "error": f"Erreur Redis: {e}"}

        logger.info(f"Gmail connected: tenant={tenant_id}, email={email}")
        return {"success": True, "tenant_id": tenant_id, "email": email}

    # =========================================================================
    # SEND EMAIL
    # =========================================================================

    async def send(
        self,
        tenant_id: int,
        redis_client,
        to: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        subscriber_name: Optional[str] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Envoie un email via Gmail API pour un tenant specifique.

        Charge les tokens depuis Redis, refresh si necessaire.
        Le FROM est l'email du proprietaire (pas une adresse tierce).
        Le sender name affiche "Luna de {subscriber_name}".
        """
        settings = get_settings()
        if settings.foundation_test_mode:
            # Sauvegarde locale au lieu d'envoyer
            tmp_dir = "tmp/emails"
            os.makedirs(tmp_dir, exist_ok=True)
            safe_to = to.replace("@", "_at_").replace(".", "_")
            filepath = f"{tmp_dir}/{int(time.time())}_{safe_to}.html"
            html_content = body_html or body_text.replace("\n", "<br>")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"<h1>To: {to}</h1><h2>Subject: {subject}</h2><hr>{html_content}")
            logger.info(f"[DRY RUN] Gmail email tenant={tenant_id} to={to}: {subject} — saved to {filepath}")
            return True, {"simulated": True, "to": to, "subject": subject, "saved_to": filepath}

        # Charge l'integration
        integration = redis_client.get_email_integration(tenant_id)
        if not integration or integration.get("service") != "gmail":
            return False, {"error": "Gmail non connecte pour ce tenant"}

        access_token = integration.get("access_token", "")
        refresh_token = integration.get("refresh_token", "")
        token_expiry = int(integration.get("token_expiry", "0"))
        sender_email = integration.get("email", "")

        if not sender_email:
            return False, {"error": "Email du compte Gmail manquant"}

        # Refresh si expire
        now = int(datetime.utcnow().timestamp())
        if now >= token_expiry - 60:  # Refresh 60s avant expiration
            access_token = await self._refresh_access_token(
                refresh_token, tenant_id, redis_client
            )
            if not access_token:
                return False, {"error": "Impossible de rafraichir le token Gmail. Reconnectez le compte."}

        # Construit l'email
        sender_name = f"Luna de {subscriber_name}" if subscriber_name else "Luna YAWatch"

        msg = MIMEMultipart("alternative")
        msg["to"] = to
        msg["from"] = f"{sender_name} <{sender_email}>"
        msg["subject"] = subject

        msg.attach(MIMEText(body_text, "plain"))
        if body_html:
            msg.attach(MIMEText(body_html, "html"))
        else:
            msg.attach(MIMEText(body_text.replace("\n", "<br>"), "html"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        # Envoie via Gmail API
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    GMAIL_SEND_URL,
                    json={"raw": raw},
                    headers={"Authorization": f"Bearer {access_token}"},
                )

            if resp.status_code in (200, 201):
                result = resp.json()
                logger.info(f"Gmail email sent: tenant={tenant_id}, to={to}, id={result.get('id')}")
                return True, {"message_id": result.get("id"), "from": sender_email}
            else:
                error = resp.text[:300]
                logger.error(f"Gmail send failed: {resp.status_code} {error}")
                return False, {"error": f"Gmail API {resp.status_code}", "details": error}

        except httpx.TimeoutException:
            return False, {"error": "Timeout Gmail API"}
        except Exception as e:
            logger.error(f"Gmail send error: {e}")
            return False, {"error": str(e)}

    # =========================================================================
    # INTERNAL
    # =========================================================================

    async def _get_user_email(self, access_token: str) -> Optional[str]:
        """Recupere l'email du compte Google via userinfo."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    GOOGLE_USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
            if resp.status_code == 200:
                return resp.json().get("email")
        except Exception as e:
            logger.error(f"Google userinfo error: {e}")
        return None

    async def _refresh_access_token(
        self,
        refresh_token: str,
        tenant_id: int,
        redis_client,
    ) -> Optional[str]:
        """Rafraichit l'access_token via le refresh_token."""
        if not refresh_token:
            return None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(GOOGLE_TOKEN_URL, data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                })

            if resp.status_code != 200:
                logger.error(f"Gmail token refresh failed: {resp.status_code}")
                return None

            data = resp.json()
            new_access_token = data.get("access_token", "")
            expires_in = data.get("expires_in", 3600)

            # Met a jour Redis
            redis_client.save_email_integration(tenant_id, {
                "access_token": new_access_token,
                "token_expiry": str(int(datetime.utcnow().timestamp()) + expires_in),
            })

            logger.info(f"Gmail token refreshed: tenant={tenant_id}")
            return new_access_token

        except Exception as e:
            logger.error(f"Gmail token refresh error: {e}")
            return None

    def _sign_state(self, tenant_id: int) -> str:
        """Signe le state avec HMAC pour anti-CSRF."""
        payload = str(tenant_id)
        sig = hmac.new(
            self.state_secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()[:16]
        return f"{tenant_id}.{sig}"

    def _verify_state(self, state: str) -> Optional[int]:
        """Verifie et decode le state."""
        if "." not in state:
            return None
        parts = state.split(".", 1)
        try:
            tenant_id = int(parts[0])
        except ValueError:
            return None
        expected = self._sign_state(tenant_id)
        if hmac.compare_digest(state, expected):
            return tenant_id
        return None

    def get_status(self) -> Dict[str, Any]:
        return {
            "configured": self.is_configured,
            "redirect_uri": self.redirect_uri if self.is_configured else None,
        }
