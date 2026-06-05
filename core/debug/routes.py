"""
Debug Routes - Endpoints pour valider l'etat du systeme (non sensibles).
"""
import os
import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from core.settings import get_settings
from integrations.twilio.sms_client import TwilioSMSClient
from integrations.twilio.voice_client import TwilioVoiceClient
from integrations.email.email_client import EmailClient
from integrations.email.gmail_client import GmailClient
from integrations.reservations.duffel_client import DuffelClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.get("/services-mode")
async def get_services_mode():
    """
    Retourne l'etat actuel des services externes.
    Aucune information sensible n'est exposee (pas de cles API).
    """
    settings = get_settings()

    # Statut des integrations (sans secrets)
    twilio_sms = TwilioSMSClient.from_env()
    twilio_voice = TwilioVoiceClient.from_env()
    email = EmailClient.from_env()
    gmail = GmailClient.from_env()
    duffel = DuffelClient.from_env()

    # Stripe: on regarde juste si la cle est configuree
    stripe_key = os.getenv("STRIPE_API_KEY", "")
    stripe_test_key = os.getenv("STRIPE_TEST_SECRET_KEY", "")

    return JSONResponse({
        "foundation_test_mode": settings.foundation_test_mode,
        "allow_test_external": settings.allow_test_external,
        "services": {
            "sms": {
                "mode": "simulated" if settings.foundation_test_mode else "live",
                "configured": twilio_sms.is_configured,
            },
            "calls": {
                "mode": "simulated" if settings.foundation_test_mode else "live",
                "configured": twilio_voice.is_configured,
            },
            "email_sendgrid": {
                "mode": "simulated" if settings.foundation_test_mode else "live",
                "configured": email.is_configured,
            },
            "email_gmail": {
                "mode": "simulated" if settings.foundation_test_mode else "live",
                "configured": gmail.is_configured,
            },
            "booking": {
                "mode": "sandbox+blocked_confirm" if settings.foundation_test_mode else "live",
                "configured": duffel.is_configured,
                "duffel_mode": "test" if duffel.is_test else "live",
            },
            "payment": {
                "mode": "test_keys" if settings.foundation_test_mode else "live_keys",
                "stripe_configured": bool(stripe_key),
                "stripe_test_configured": bool(stripe_test_key),
            },
        }
    })
