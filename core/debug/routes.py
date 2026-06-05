"""
Debug Routes - Endpoints pour valider l'etat du systeme (non sensibles).
"""
import os
import logging
import pathlib
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from core.settings import get_settings
from integrations.twilio.sms_client import TwilioSMSClient
from integrations.twilio.voice_client import TwilioVoiceClient
from integrations.email.email_client import EmailClient
from integrations.email.gmail_client import GmailClient
from integrations.reservations.duffel_client import DuffelClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/debug", tags=["debug"])

_IRIS_SESSION_DIR = pathlib.Path("/tmp/iris_sessions")


@router.get("/iris/sessions")
async def iris_sessions_list():
    """Liste les dernières sessions Iris enregistrées (pour diagnostic Claude)."""
    if not _IRIS_SESSION_DIR.exists():
        return JSONResponse({"sessions": []})
    files = sorted(_IRIS_SESSION_DIR.glob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
    result = []
    for f in files[:20]:
        try:
            lines = f.read_text().strip().splitlines()
            events = [l for l in lines if '"type"' in l]
            result.append({
                "file": f.name,
                "events": len(events),
                "size_bytes": f.stat().st_size,
                "modified": round(f.stat().st_mtime),
            })
        except Exception:
            pass
    return JSONResponse({"sessions": result})


@router.get("/iris/session/{filename}")
async def iris_session_detail(filename: str, last: int = Query(default=50)):
    """Retourne les N derniers événements d'une session Iris (pour diagnostic Claude)."""
    path = _IRIS_SESSION_DIR / filename
    if not path.exists() or not path.name.endswith(".jsonl"):
        return JSONResponse({"error": "session introuvable"}, status_code=404)
    try:
        import json as _json
        lines = path.read_text().strip().splitlines()
        events = []
        for line in lines[-last:]:
            try:
                events.append(_json.loads(line))
            except Exception:
                pass
        return JSONResponse({"filename": filename, "total": len(lines), "events": events})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


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
