#!/usr/bin/env python3
"""
Luna Web - Serveur YAWatch-Luna (Proprio Ludo)
Endpoints: chat, greeting, call Tavus, invitation contact, webhook SMS
"""
import os
import re
import time
import logging
import openai
from collections import defaultdict
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import Optional

from integrations.twilio.sms_client import TwilioSMSClient
from integrations.tavus.tavus_client import TavusClient, build_tavus_context

# Core modules (optional - graceful fallback if Redis down)
try:
    from core.memory.memory_manager import MemoryManager
    from core.memory.redis_client import RedisClient
    from core.memory.schemas import PlanType, MessageRole, Channel, Conversation
    from core.safety.guardian import SafetyGuardian, SafetyLevel
    from core.actions.quota_guard import QuotaGuard
    from core.actions.models import ActionType as CoreActionType
    _CORE_AVAILABLE = True
except ImportError as _import_err:
    _CORE_AVAILABLE = False

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("luna_web")

# --- Config ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
ADMIN_NUMBER = os.getenv("ADMIN_NUMBER", "+33658477952")
TENANT_ID = 1  # Ludo = tenant 1 pour l'instant

# --- Clients ---
openai_client = OpenAI(api_key=OPENAI_API_KEY)
sms_client = TwilioSMSClient.from_env()
tavus_client = TavusClient.from_env()

# --- Core modules (Redis, Safety, Quota) ---
_redis_client: Optional[object] = None
_memory_manager: Optional[object] = None
_safety_guardian: Optional[object] = None
_quota_guard: Optional[object] = None

def _init_core():
    """Initialize core modules. Graceful if Redis is down or imports failed."""
    global _redis_client, _memory_manager, _safety_guardian, _quota_guard
    if not _CORE_AVAILABLE:
        logger.warning("Core modules non disponibles (import failed) - mode degrade")
        return
    try:
        _redis_client = RedisClient()
        if _redis_client.ping():
            _memory_manager = MemoryManager(
                tenant_id=TENANT_ID,
                plan=PlanType.ESSENTIEL,
                redis_client=_redis_client,
            )
            _safety_guardian = SafetyGuardian(
                tenant_id=TENANT_ID,
                memory_manager=_memory_manager,
                sms_service=sms_client,
            )
            _quota_guard = QuotaGuard(memory_manager=_memory_manager)
            logger.info("Core modules initialises (Redis OK)")
        else:
            logger.warning("Redis injoignable - mode degrade (memoire locale)")
    except Exception as e:
        logger.warning(f"Core init echoue: {e} - mode degrade")

_init_core()

NOW = datetime.now().strftime("%A %d %B %Y, %Hh%M")

LUNA_SYSTEM_PROMPT = f"""Tu es Luna, l'assistante IA personnelle de YAWatch-Luna.

=== IDENTITE ===
- Tu es Luna, une compagne bienveillante et chaleureuse, disponible 24h/24, 7j/7.
- Tu parles en francais, ton rassurant, moderne et empathique.
- Tu tutoies le souscripteur sauf demande contraire.
- Tu es au service de Ludo (Ludovic SAINT-LOUIS), fondateur et proprio de YAWatch-Luna.
- Date du jour : {NOW}
- Numero admin : {ADMIN_NUMBER}

=== ARCHITECTURE YAWATCH-LUNA ===
YAWatch-Luna est un service d'assistance IA par abonnement.
Luna agit AU NOM du souscripteur selon ses instructions.

Composants :
- Backend Python FastAPI/Uvicorn, HTTPS port 8888
- LLM : OpenAI GPT-4 Turbo (conversations texte)
- Video avatar : Tavus (persona Luna, appels video temps reel)
- SMS/Appels : Twilio (SMS, appels vocaux, WhatsApp)
- Memoire : Redis (conversations, instructions, contacts, notes)

=== OFFRES & ABONNEMENTS ===
- Essentiel (139 EUR/mois) : 20 SMS, 15 min visio, 100 MB memoire
- Confort (229 EUR/mois) : 50 SMS, 45 min visio, 500 MB memoire
- Premium (399 EUR/mois) : 100 SMS, 90 min visio, 2 GB memoire
Alertes quotas : 80% avertissement, 90% urgences seulement, 100% bloque

=== CAPACITES ===
1. Chat texte (web)
2. Appels video avec avatar Luna (Tavus)
3. Envoi SMS aux contacts de confiance (max 5, verifies par OTP)
4. Invitation de contacts dans la visio par SMS (lien Tavus dans le SMS)
5. Rappels et instructions (quotidiens, recurrents, conditionnels)
6. Surveillance d'inactivite et alertes contacts
7. Prise de notes automatique

=== INVITATION VISIO PAR SMS ===
Quand Ludo est en appel video avec Luna, il peut demander :
"Invite Marie dans l'appel" ou "Ajoute mon fils a la visio"
Luna envoie alors un SMS au contact de confiance avec le lien pour rejoindre.
Le contact clique sur le lien et rejoint directement la conversation video.

=== CONTACTS DE CONFIANCE ===
- Maximum 5 par souscripteur
- Verifies par OTP SMS
- Heures calmes : 22h-7h (sauf urgence critique)
- Chaque contact : nom, relation, tel, canal prefere, flag urgence-seulement

=== CONFIRMATION ===
AUCUNE action consommant du quota sans confirmation explicite.
Exception : alertes d'urgence critiques (auto-execution).
Timeout : 10 minutes.

=== SECURITE ===
1. Luna n'est PAS professionnel de sante, juridique ou financier.
2. Luna ne donne AUCUN conseil medical (risque juridique).
3. Luna ne peut PAS appeler les services d'urgence (interdit pour une IA).
4. Luna PEUT alerter les contacts de confiance par SMS.
5. Luna suggere les numeros d'urgence :
   - Police : 17, Pompiers : 18, Urgences : 112
   - Prevention suicide : 3114 (24h/24)
   - Maltraitance : 3977
6. Luna refuse les demandes illegales.
7. Luna detecte la detresse et propose de contacter quelqu'un.

=== STYLE ===
- Reponses concises et naturelles
- Chaleureuse mais pas infantilisante
- Proactive : propose des actions concretes
- Confirme avant d'executer toute action

Commence par saluer Ludo chaleureusement."""

# --- State ---
conversations: dict[str, list] = {}
_conversation_ts: dict[str, float] = {}  # session_id -> last activity timestamp
SESSION_TTL = 86400  # 24h

# --- Rate Limiting ---
_rate_limits: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 30  # max requests per window per IP
_request_count = 0  # for periodic cleanup

def _check_rate_limit(client_ip: str) -> bool:
    """Returns True if request is allowed."""
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    _rate_limits[client_ip] = [t for t in _rate_limits[client_ip] if t > window_start]
    if len(_rate_limits[client_ip]) >= RATE_LIMIT_MAX:
        return False
    _rate_limits[client_ip].append(now)
    return True

def _cleanup_sessions():
    """Remove sessions older than SESSION_TTL."""
    now = time.time()
    expired = [sid for sid, ts in _conversation_ts.items() if now - ts > SESSION_TTL]
    for sid in expired:
        conversations.pop(sid, None)
        _conversation_ts.pop(sid, None)
    if expired:
        logger.info(f"Cleaned up {len(expired)} expired sessions")


# --- App ---
app = FastAPI(title="Luna - YAWatch")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

# --- CORS ---
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "https://localhost:8888").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# --- Middleware: rate limit + logging + session cleanup ---
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    global _request_count
    client_ip = request.client.host if request.client else "unknown"
    start_time = time.time()

    # Rate limit (API endpoints only)
    if request.url.path.startswith("/api/") and not _check_rate_limit(client_ip):
        logger.warning(f"RATE_LIMITED {client_ip} {request.method} {request.url.path}")
        return JSONResponse(
            status_code=429,
            content={"error": "Trop de requetes. Reessaie dans une minute."},
        )

    response = await call_next(request)

    duration_ms = (time.time() - start_time) * 1000
    logger.info(f"{request.method} {request.url.path} [{response.status_code}] {duration_ms:.0f}ms - {client_ip}")

    # Periodic session cleanup (every 100 requests)
    _request_count += 1
    if _request_count % 100 == 0:
        _cleanup_sessions()

    return response


# --- Models ---
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(default="default", max_length=100)

    @field_validator("message")
    @classmethod
    def strip_message(cls, v: str) -> str:
        return v.strip()


class InviteRequest(BaseModel):
    conversation_id: str = Field(..., min_length=1, max_length=100)
    contact_name: str = Field(..., min_length=1, max_length=100)
    contact_phone: str = Field(..., min_length=6, max_length=20)

    @field_validator("contact_phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = re.sub(r"[\s\-\.\(\)]", "", v)
        if not re.match(r"^\+?\d{6,15}$", cleaned):
            raise ValueError("Format de telephone invalide")
        return cleaned


# =========================================================================
# ENDPOINTS
# =========================================================================

@app.get("/")
async def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.post("/api/chat")
async def chat(req: ChatRequest):
    try:
        # Safety check (if guardian available)
        if _safety_guardian:
            try:
                safety = _safety_guardian.check(req.message)
                if safety.block_action and safety.luna_response:
                    return {"response": safety.luna_response}
            except Exception as e:
                logger.warning(f"Safety check failed: {e}")

        if req.session_id not in conversations:
            conversations[req.session_id] = [
                {"role": "system", "content": LUNA_SYSTEM_PROMPT}
            ]

        _conversation_ts[req.session_id] = time.time()
        messages = conversations[req.session_id]
        messages.append({"role": "user", "content": req.message})

        # Persist to Redis (if available)
        if _memory_manager:
            try:
                _memory_manager.add_message(
                    conv_id=req.session_id,
                    role=MessageRole.SUBSCRIBER,
                    content=req.message,
                    channel=Channel.APP,
                )
            except Exception as e:
                logger.warning(f"Redis store failed: {e}")

        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            max_tokens=500,
            temperature=0.8,
            timeout=30,
        )
        luna_msg = response.choices[0].message.content
        messages.append({"role": "assistant", "content": luna_msg})

        # Persist Luna response to Redis
        if _memory_manager:
            try:
                _memory_manager.add_message(
                    conv_id=req.session_id,
                    role=MessageRole.LUNA,
                    content=luna_msg,
                    channel=Channel.APP,
                )
            except Exception as e:
                logger.warning(f"Redis store failed: {e}")

        return {"response": luna_msg}

    except openai.AuthenticationError:
        return {"response": "[Erreur] Cle OpenAI invalide ou expiree."}
    except openai.RateLimitError:
        return {"response": "[Erreur] Quota OpenAI depasse. Reessaie."}
    except openai.APIConnectionError:
        return {"response": "[Erreur] Impossible de joindre OpenAI."}
    except Exception as e:
        if req.session_id in conversations and len(conversations[req.session_id]) > 1:
            conversations[req.session_id].pop()
        return {"response": f"[Erreur] Luna indisponible : {type(e).__name__}"}


@app.get("/api/greeting")
async def greeting():
    try:
        messages = [{"role": "system", "content": LUNA_SYSTEM_PROMPT}]
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            max_tokens=300,
            temperature=0.8,
            timeout=30,
        )
        return {"response": response.choices[0].message.content}
    except Exception as e:
        return {"response": f"Salut Ludo ! Luna a un souci technique ({type(e).__name__}). Reessaie."}


@app.post("/api/call")
async def start_call():
    """Crée un appel vidéo Tavus et enregistre la conversation"""
    context = build_tavus_context(
        subscriber_name="Ludo",
        memory_manager=tavus_client.memory,
    )
    success, data = await tavus_client.create_conversation(
        tenant_id=TENANT_ID,
        custom_greeting="Salut Ludo ! Ravie de te voir. Comment je peux t'aider ?",
        context=context,
    )
    if not success:
        return {"error": data.get("error", "Erreur Tavus inconnue")}
    return {
        "conversation_url": data["conversation_url"],
        "conversation_id": data["conversation_id"],
    }


@app.post("/api/invite-contact")
async def invite_contact(req: InviteRequest):
    """
    Invite un contact de confiance dans la visio en cours.
    Envoie un SMS avec le lien Tavus.
    """
    if not sms_client.is_configured:
        return {"error": "Service SMS non configure"}

    # Quota check (if available)
    if _quota_guard:
        try:
            quota_status = _quota_guard.check(TENANT_ID, CoreActionType.SEND_SMS)
            if not quota_status.allowed:
                return {"error": quota_status.warning_message or "Quota SMS atteint"}
        except Exception as e:
            logger.warning(f"Quota check failed: {e}")

    phone = sms_client.normalize_phone(req.contact_phone)
    if not phone:
        return {"error": f"Numero invalide: {req.contact_phone}"}

    success, message = await tavus_client.add_participant_via_sms(
        conversation_id=req.conversation_id,
        contact_name=req.contact_name,
        contact_phone=phone,
        sms_client=sms_client,
        tenant_id=TENANT_ID,
    )
    if not success:
        return {"error": message}
    return {"success": True, "message": message}


@app.post("/api/webhook/sms")
async def webhook_sms(request: Request):
    """
    Webhook Twilio pour recevoir les SMS entrants.
    Twilio envoie un POST avec les params du message recu.
    """
    form = await request.form()
    from_number = form.get("From", "")
    body = form.get("Body", "")
    to_number = form.get("To", "")
    sms_sid = form.get("MessageSid", "")

    logger.info(f"SMS recu de {from_number}: {body[:80]}")

    # Validation signature Twilio (stricte si configuré)
    if sms_client.is_configured:
        signature = request.headers.get("X-Twilio-Signature", "")
        if not signature:
            logger.warning(f"Signature Twilio manquante pour SMS de {from_number}")
            return Response(status_code=403, content="Forbidden", media_type="text/plain")
        url = str(request.url)
        params = dict(form)
        if not sms_client.validate_webhook(signature, url, params):
            logger.warning(f"Signature Twilio invalide pour SMS de {from_number}")
            return Response(status_code=403, content="Forbidden", media_type="text/plain")

    # Enregistre le message entrant dans la conversation
    logger.info(f"SMS entrant OK - De: {from_number}, Corps: {body[:100]}")

    # Reponse TwiML vide (pas de reponse automatique par SMS pour l'instant)
    twiml = "<Response></Response>"
    return Response(content=twiml, media_type="application/xml")


@app.get("/api/history")
async def history(session_id: str = "default", limit: int = 50):
    """Historique des messages d'une session."""
    # Try Redis first
    if _memory_manager:
        try:
            messages = _memory_manager.get_messages(session_id, limit=limit)
            return {
                "messages": [
                    {
                        "role": "luna" if msg.role == MessageRole.LUNA else "user",
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat() if hasattr(msg, "timestamp") else "",
                    }
                    for msg in messages
                ]
            }
        except Exception as e:
            logger.warning(f"Redis history fetch failed: {e}")

    # Fallback to in-memory
    if session_id in conversations:
        msgs = conversations[session_id]
        return {
            "messages": [
                {"role": "luna" if m["role"] == "assistant" else "user", "content": m["content"], "timestamp": ""}
                for m in msgs
                if m["role"] != "system"
            ][-limit:]
        }
    return {"messages": []}


@app.get("/api/status")
async def status():
    """Statut du serveur Luna"""
    redis_ok = False
    if _redis_client:
        try:
            redis_ok = _redis_client.ping()
        except Exception:
            pass

    return {
        "luna": "online",
        "openai": bool(OPENAI_API_KEY),
        "twilio": sms_client.is_configured if sms_client else False,
        "tavus": tavus_client.is_configured if tavus_client else False,
        "tavus_details": tavus_client.get_status() if tavus_client else {},
        "redis": redis_ok,
        "active_sessions": len(conversations),
        "core_modules": {
            "memory": _memory_manager is not None,
            "safety": _safety_guardian is not None,
            "quota": _quota_guard is not None,
        },
    }


# =========================================================================
# MAIN
# =========================================================================

if __name__ == "__main__":
    import uvicorn

    ssl_dir = os.path.dirname(__file__)
    logger.info("Demarrage Luna Web - YAWatch-Luna (Proprio Ludo)")
    logger.info(f"OpenAI: {'OK' if OPENAI_API_KEY else 'MANQUANT'}")
    logger.info(f"Twilio: {'OK' if sms_client.is_configured else 'NON CONFIGURE'}")
    logger.info(f"Tavus: {'OK' if tavus_client.is_configured else 'NON CONFIGURE'}")
    logger.info(f"Redis/Memory: {'OK' if _memory_manager else 'OFFLINE'}")
    logger.info(f"Safety Guardian: {'OK' if _safety_guardian else 'OFFLINE'}")
    logger.info(f"Quota Guard: {'OK' if _quota_guard else 'OFFLINE'}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8888,
        ssl_keyfile=os.path.join(ssl_dir, "key.pem"),
        ssl_certfile=os.path.join(ssl_dir, "cert.pem"),
    )
