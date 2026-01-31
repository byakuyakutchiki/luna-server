#!/usr/bin/env python3
"""
Luna Web - Serveur YAWatch-Luna (Proprio Ludo)
Endpoints: chat, greeting, call Tavus, invitation contact, webhook SMS
"""
import os
import re
import time
import asyncio
import logging
import openai
from collections import defaultdict
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict

from integrations.twilio.sms_client import TwilioSMSClient
from integrations.tavus.tavus_client import TavusClient, build_tavus_context

# Core modules (optional - graceful fallback if Redis down)
try:
    from core.memory.memory_manager import MemoryManager
    from core.memory.redis_client import RedisClient
    from core.memory.schemas import (
        PlanType, MessageRole, Channel, Conversation,
        SubscriberProfile, InstructionType, ActionType as SchemaActionType,
    )
    from core.safety.guardian import SafetyGuardian, SafetyLevel
    from core.actions.quota_guard import QuotaGuard
    from core.actions.models import ActionType as CoreActionType
    from core.instructions.parser import InstructionParser, ParsedInstruction
    from core.instructions.scheduler import InstructionScheduler, ScheduledTask
    from core.instructions.executor import InstructionExecutor, create_instruction_executor
    from core.documents.generator import DocumentGenerator
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
TAVUS_CALLBACK_URL = os.getenv("TAVUS_CALLBACK_URL", "")  # URL publique pour webhooks Tavus
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
_scheduler: Optional[object] = None
_executor: Optional[object] = None
_instruction_loop_task: Optional[object] = None
_doc_generator: Optional[object] = None
_perception_detector: Optional[object] = None
_perception_analyzer: Optional[object] = None
_perception_loop_task: Optional[object] = None

def _init_core():
    """Initialize core modules. Graceful if Redis is down or imports failed."""
    global _redis_client, _memory_manager, _safety_guardian, _quota_guard, _scheduler, _executor, _doc_generator, _perception_detector, _perception_analyzer
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
            _scheduler = InstructionScheduler()
            _executor = create_instruction_executor(
                memory_manager=_memory_manager,
                sms_service=sms_client,
                safety_guardian=_safety_guardian,
            )
            _doc_generator = DocumentGenerator(
                output_dir=os.path.join(os.path.dirname(__file__), "static", "documents"),
                tenant_id=TENANT_ID,
            )
            # Perception (ne demarre PAS la camera, juste les objets)
            try:
                from core.perception.detector import PerceptionDetector
                from core.perception.analyzer import SceneAnalyzer
                _perception_detector = PerceptionDetector()
                _perception_analyzer = SceneAnalyzer()
            except ImportError:
                logger.info("Perception module non disponible (ultralytics/cv2 manquant)")
            logger.info("Core modules initialises (Redis OK, Scheduler OK, DocGen OK)")
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

=== PERCEPTION CONTEXTUELLE ===
Si la perception camera est activee, tu recois des informations sur
l'environnement du souscripteur (presence, posture, objets visibles).
Ces informations t'aident a mieux comprendre le contexte, comme une
compagne attentive qui observe naturellement.
- Tu peux mentionner ce que tu "vois" naturellement dans la conversation
- Si tu remarques quelque chose de preoccupant (personne au sol depuis
  longtemps), propose gentiment de l'aide ou de contacter un proche
- Tu ne promets JAMAIS une surveillance garantie
- Tu ne dis JAMAIS "je surveille" - tu dis "j'ai remarque que..."
- La perception est une aide contextuelle, pas un systeme de securite

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


@asynccontextmanager
async def lifespan(app):
    """Startup: charge instructions, lance boucles, configure Tavus. Shutdown: stoppe tout."""
    global _instruction_loop_task, _perception_loop_task
    if _CORE_AVAILABLE and _scheduler:
        await _load_instructions_to_scheduler()
        _instruction_loop_task = asyncio.create_task(_instruction_loop())
        logger.info("Instruction engine started")
    # Perception loop (camera PAS ouverte, juste le loop pret)
    if _perception_detector:
        _perception_loop_task = asyncio.create_task(_perception_loop())
        logger.info("Perception loop ready (disabled by default)")
    # Configure Tavus tool calling + perception
    if tavus_client.is_configured:
        await tavus_client.configure_tools()
        await tavus_client.configure_perception()
    yield
    # Shutdown
    if _instruction_loop_task:
        _instruction_loop_task.cancel()
        try:
            await _instruction_loop_task
        except asyncio.CancelledError:
            pass
        logger.info("Instruction engine stopped")
    if _perception_loop_task:
        _perception_loop_task.cancel()
        try:
            await _perception_loop_task
        except asyncio.CancelledError:
            pass
    if _perception_detector:
        _perception_detector.release()

# --- App ---
app = FastAPI(title="Luna - YAWatch", lifespan=lifespan)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

# --- CORS ---
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "https://localhost:8888").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
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


class ProfileRequest(BaseModel):
    first_name: str = Field(default="", max_length=100)
    last_name: str = Field(default="", max_length=100)
    date_of_birth: Optional[str] = None
    address: str = Field(default="", max_length=500)
    city: str = Field(default="", max_length=100)
    department: str = Field(default="", max_length=100)
    phone: str = Field(default="", max_length=20)
    email: str = Field(default="", max_length=200)
    language: str = Field(default="fr", max_length=5)
    tutoiement: bool = True
    family_status: str = Field(default="", max_length=50)
    children: str = Field(default="", max_length=500)
    lives_alone: bool = True
    pets: str = Field(default="", max_length=200)
    autonomy: str = Field(default="autonome", max_length=50)
    mobility: str = Field(default="autonome", max_length=50)
    professional_status: str = Field(default="", max_length=50)
    job_title: str = Field(default="", max_length=200)
    income_range: str = Field(default="", max_length=100)
    siret: str = Field(default="", max_length=20)
    doctor_name: str = Field(default="", max_length=200)
    doctor_phone: str = Field(default="", max_length=20)
    pharmacy: str = Field(default="", max_length=200)
    allergies: str = Field(default="", max_length=1000)
    treatments: str = Field(default="", max_length=1000)
    conditions: str = Field(default="", max_length=1000)
    medical_contact_person: str = Field(default="", max_length=200)
    mutual_name: str = Field(default="", max_length=200)
    mutual_number: str = Field(default="", max_length=100)
    carte_vitale: str = Field(default="", max_length=50)
    housing_type: str = Field(default="", max_length=50)
    housing_status: str = Field(default="", max_length=50)
    floor: str = Field(default="", max_length=100)
    landlord_name: str = Field(default="", max_length=200)
    landlord_phone: str = Field(default="", max_length=20)
    home_insurance: str = Field(default="", max_length=200)
    concierge: str = Field(default="", max_length=200)
    tax_number: str = Field(default="", max_length=50)
    caf_number: str = Field(default="", max_length=50)
    france_travail_id: str = Field(default="", max_length=50)
    cpam_center: str = Field(default="", max_length=100)
    bank_name: str = Field(default="", max_length=200)
    bank_advisor: str = Field(default="", max_length=200)
    documents_expiry: str = Field(default="", max_length=1000)
    tone: str = Field(default="chaleureux", max_length=50)
    wake_time: str = Field(default="08:00", max_length=5)
    sleep_time: str = Field(default="22:00", max_length=5)
    quiet_hours_start: str = Field(default="22:00", max_length=5)
    quiet_hours_end: str = Field(default="07:00", max_length=5)
    sensitive_topics: str = Field(default="", max_length=1000)
    interests: str = Field(default="", max_length=1000)
    habits: str = Field(default="", max_length=1000)
    presentation: str = Field(default="", max_length=200)
    permanent_rules: str = Field(default="", max_length=2000)
    blacklist: str = Field(default="", max_length=1000)
    priorities: str = Field(default="", max_length=1000)
    max_budget: str = Field(default="", max_length=100)


class ContactRequest(BaseModel):
    phone: str = Field(..., min_length=6, max_length=20)
    name: str = Field(..., min_length=1, max_length=100)
    relation: str = Field(..., min_length=1, max_length=50)
    preferred_channel: str = Field(default="sms", max_length=10)
    emergency_only: bool = False
    availability: str = Field(default="24/7", max_length=100)
    info_level: str = Field(default="tout", max_length=50)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = re.sub(r"[\s\-\.\(\)]", "", v)
        if not re.match(r"^\+?\d{6,15}$", cleaned):
            raise ValueError("Format de telephone invalide")
        return cleaned


class InstructionRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class NoteRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    context: str = Field(default="manual", max_length=100)
    tags: Optional[list] = None


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

        # Inject perception context if available
        if _perception_analyzer and _memory_manager:
            try:
                if _memory_manager.is_perception_enabled():
                    perception_ctx = _perception_analyzer.get_context_for_luna()
                    if perception_ctx:
                        messages.append({"role": "system", "content": perception_ctx})
            except Exception:
                pass

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
        callback_url=TAVUS_CALLBACK_URL if TAVUS_CALLBACK_URL else None,
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
        "perception": {
            "available": _perception_detector is not None,
            "enabled": _memory_manager.is_perception_enabled() if _memory_manager else False,
            "camera": _perception_detector.is_camera_available() if _perception_detector else False,
        },
    }


# =========================================================================
# PROFILE ENDPOINTS
# =========================================================================

@app.get("/api/profile")
async def get_profile():
    """Retourne le profil souscripteur"""
    if not _memory_manager:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    profile = _memory_manager.get_subscriber_profile()
    if not profile:
        return {"profile": None}
    return {"profile": profile.model_dump()}


@app.post("/api/profile")
async def set_profile(req: ProfileRequest):
    """Cree ou remplace le profil souscripteur"""
    if not _memory_manager:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    profile = SubscriberProfile(tenant_id=TENANT_ID, **req.model_dump())
    _memory_manager.set_subscriber_profile(profile)
    return {"success": True, "profile": profile.model_dump()}


@app.patch("/api/profile")
async def update_profile(request: Request):
    """Mise a jour partielle du profil"""
    if not _memory_manager:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    body = await request.json()
    if not body:
        return JSONResponse(status_code=400, content={"error": "Corps vide"})
    profile = _memory_manager.update_subscriber_profile(body)
    if not profile:
        return JSONResponse(status_code=404, content={"error": "Profil non trouve"})
    return {"success": True, "profile": profile.model_dump()}


# =========================================================================
# CONTACTS ENDPOINTS
# =========================================================================

@app.get("/api/contacts")
async def list_contacts():
    """Liste les contacts de confiance"""
    if not _memory_manager:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    contacts = _memory_manager.list_trusted_contacts()
    return {
        "contacts": [
            {
                "phone": c.phone,
                "name": c.name,
                "relation": c.relation,
                "preferred_channel": c.preferred_channel.value if hasattr(c.preferred_channel, "value") else str(c.preferred_channel),
                "emergency_only": c.emergency_only,
                "verified_at": c.verified_at.isoformat() if c.verified_at else None,
            }
            for c in contacts
        ],
        "count": len(contacts),
        "max": 5,
    }


@app.post("/api/contacts")
async def add_contact(req: ContactRequest):
    """Ajoute un contact de confiance (max 5)"""
    if not _memory_manager:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    try:
        channel = Channel(req.preferred_channel) if req.preferred_channel in [c.value for c in Channel] else Channel.SMS
        contact = _memory_manager.add_trusted_contact(
            phone=req.phone,
            name=req.name,
            relation=req.relation,
            preferred_channel=channel,
            emergency_only=req.emergency_only,
        )
        return {"success": True, "contact": {
            "phone": contact.phone,
            "name": contact.name,
            "relation": contact.relation,
        }}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@app.delete("/api/contacts/{phone}")
async def delete_contact(phone: str):
    """Supprime un contact de confiance"""
    if not _memory_manager:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    _memory_manager.remove_trusted_contact(phone)
    return {"success": True}


# =========================================================================
# INSTRUCTIONS ENDPOINTS
# =========================================================================

@app.get("/api/instructions")
async def list_instructions():
    """Liste les instructions actives"""
    if not _memory_manager:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    instructions = _memory_manager.list_active_instructions()
    return {
        "instructions": [
            {
                "id": instr.id,
                "type": instr.type.value,
                "description": instr.description,
                "schedule": instr.schedule,
                "action": instr.action.value,
                "target": instr.target,
                "enabled": instr.enabled,
                "last_executed": instr.last_executed.isoformat() if instr.last_executed else None,
                "created_at": instr.created_at.isoformat() if instr.created_at else None,
            }
            for instr in instructions
        ],
        "count": len(instructions),
    }


@app.post("/api/instructions")
async def create_instruction(req: InstructionRequest):
    """Cree une instruction a partir de texte naturel (francais)"""
    if not _memory_manager:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    if not _CORE_AVAILABLE:
        return JSONResponse(status_code=503, content={"error": "Parser non disponible"})

    try:
        # Parse le texte naturel en instruction structuree
        parsed = InstructionParser.parse(req.text)

        # Map parser ActionType -> schema ActionType
        # Schema has: SMS, CALL, VISIO, REMINDER, NOTE, ALERT
        action_map = {
            "reminder": SchemaActionType.REMINDER,
            "sms_contact": SchemaActionType.SMS,
            "call_contact": SchemaActionType.CALL,
            "check_in": SchemaActionType.REMINDER,
            "surveillance": SchemaActionType.ALERT,
            "note": SchemaActionType.NOTE,
            "daily_routine": SchemaActionType.REMINDER,
            "information": SchemaActionType.REMINDER,
        }
        action = action_map.get(parsed.action_type.value, SchemaActionType.REMINDER)

        # Map parser RecurrenceType -> schema InstructionType
        type_map = {
            "once": InstructionType.ONE_TIME,
            "daily": InstructionType.DAILY,
            "weekly": InstructionType.RECURRING,
            "monthly": InstructionType.RECURRING,
            "weekdays": InstructionType.RECURRING,
            "weekend": InstructionType.RECURRING,
        }
        instr_type = type_map.get(parsed.recurrence.value, InstructionType.ONE_TIME)

        # Genere le schedule (cron ou heure)
        schedule_str = parsed.to_cron() or ""
        if not schedule_str and parsed.scheduled_time:
            schedule_str = f"{parsed.scheduled_time.hour:02d}:{parsed.scheduled_time.minute:02d}"

        instr = _memory_manager.add_instruction(
            description=req.text,
            action=action,
            instruction_type=instr_type,
            schedule=schedule_str,
            target=parsed.target or "self",
            message_template=parsed.message_template or "",
            priority=parsed.priority,
        )

        # Schedule dans le scheduler en memoire
        if _scheduler:
            try:
                _scheduler.schedule(
                    instruction_id=instr.id,
                    tenant_id=TENANT_ID,
                    instruction=parsed,
                )
            except Exception as e:
                logger.warning(f"Scheduler schedule failed: {e}")

        # Confirmation text
        confirmation = InstructionParser.format_confirmation(parsed)

        return {
            "success": True,
            "instruction": {
                "id": instr.id,
                "type": instr.type.value,
                "description": instr.description,
                "action": instr.action.value,
                "schedule": instr.schedule,
                "target": instr.target,
            },
            "parsed": {
                "action": parsed.action_type.value,
                "recurrence": parsed.recurrence.value,
                "time": f"{parsed.scheduled_time.hour:02d}:{parsed.scheduled_time.minute:02d}" if parsed.scheduled_time else None,
                "target": parsed.target,
                "message": parsed.message_template,
                "confidence": parsed.confidence,
                "needs_clarification": parsed.needs_clarification,
                "clarification_question": parsed.clarification_question,
            },
            "confirmation": confirmation,
        }
    except Exception as e:
        logger.error(f"Instruction creation failed: {e}")
        return JSONResponse(status_code=400, content={"error": str(e)})


@app.delete("/api/instructions/{instr_id}")
async def delete_instruction(instr_id: str):
    """Desactive une instruction"""
    if not _memory_manager:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    _memory_manager.disable_instruction(instr_id)
    return {"success": True}


@app.post("/api/instructions/{instr_id}/execute")
async def execute_instruction(instr_id: str):
    """Execute immediatement une instruction"""
    if not _memory_manager:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    instr = _memory_manager.get_instruction(instr_id)
    if not instr:
        return JSONResponse(status_code=404, content={"error": "Instruction non trouvee"})
    _memory_manager.mark_instruction_executed(instr_id)
    return {"success": True, "message": f"Instruction '{instr.description[:50]}' marquee executee"}


# =========================================================================
# NOTES ENDPOINTS
# =========================================================================

@app.get("/api/notes")
async def list_notes(limit: int = 50):
    """Liste les notes recentes"""
    if not _memory_manager:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    notes = _memory_manager.list_notes(limit=min(limit, 200))
    return {
        "notes": [
            {
                "id": n.id,
                "content": n.content,
                "context": n.context,
                "source": n.source,
                "tags": n.tags,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notes
        ],
        "count": len(notes),
    }


@app.post("/api/notes")
async def add_note(req: NoteRequest):
    """Ajoute une note"""
    if not _memory_manager:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    try:
        note = _memory_manager.add_note(
            content=req.content,
            context=req.context,
            tags=req.tags,
        )
        return {"success": True, "note": {"id": note.id, "content": note.content}}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


# =========================================================================
# QUOTA ENDPOINT
# =========================================================================

@app.get("/api/quota")
async def get_quota():
    """Retourne quotas + usage courant"""
    if not _memory_manager:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    try:
        quota_status = _memory_manager.get_quota_status()
        daily_stats = _memory_manager.get_daily_stats()
        return {
            "quota": quota_status,
            "daily": daily_stats,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# =========================================================================
# TAVUS WEBHOOK - Tool calling + transcription
# =========================================================================

@app.post("/api/webhook/tavus")
async def webhook_tavus(request: Request):
    """
    Webhook Tavus pour recevoir les events:
    - conversation.tool_call : Luna a appele une fonction depuis la visio
    - application.transcription_ready : transcription complete de la conversation
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    event_type = body.get("event_type", "") or body.get("type", "")
    logger.info(f"Tavus webhook: {event_type}")

    # --- Tool Call ---
    if "tool_call" in event_type:
        return await _handle_tavus_tool_call(body)

    # --- Transcription ready ---
    if "transcription" in event_type:
        return await _handle_tavus_transcription(body)

    # Acknowledge unknown events
    logger.info(f"Tavus webhook event non gere: {event_type}")
    return {"status": "ok"}


async def _handle_tavus_tool_call(body: Dict) -> Dict:
    """Route un tool call Tavus vers le bon handler backend."""
    import json as _json

    tool_name = body.get("tool_name", "") or body.get("function_name", "")
    args_raw = body.get("tool_arguments", "") or body.get("arguments", "{}")
    conversation_id = body.get("conversation_id", "")

    try:
        args = _json.loads(args_raw) if isinstance(args_raw, str) else args_raw
    except _json.JSONDecodeError:
        args = {}

    logger.info(f"Tavus tool_call: {tool_name}({args}) [conv={conversation_id}]")

    result = {"status": "error", "message": "Fonction inconnue"}

    try:
        if tool_name == "send_sms":
            result = await _tool_send_sms(args)
        elif tool_name == "create_instruction":
            result = await _tool_create_instruction(args)
        elif tool_name == "create_note":
            result = await _tool_create_note(args)
        elif tool_name == "get_contacts":
            result = await _tool_get_contacts()
        elif tool_name == "generate_document":
            result = await _tool_generate_document(args)
        elif tool_name == "alert_contacts":
            result = await _tool_alert_contacts(args)
        elif tool_name == "report_observation":
            result = await _tool_report_observation(args)
        else:
            logger.warning(f"Tavus tool inconnu: {tool_name}")
    except Exception as e:
        logger.error(f"Tavus tool_call error ({tool_name}): {e}")
        result = {"status": "error", "message": str(e)}

    return result


async def _tool_send_sms(args: Dict) -> Dict:
    """Envoie un SMS a un contact de confiance."""
    if not _memory_manager or not sms_client.is_configured:
        return {"status": "error", "message": "Service SMS non disponible"}

    contact_name = args.get("contact_name", "")
    message = args.get("message", "")
    if not contact_name or not message:
        return {"status": "error", "message": "Nom du contact et message requis"}

    # Cherche le contact par nom
    contacts = _memory_manager.list_trusted_contacts()
    phone = None
    matched_name = ""
    for c in contacts:
        if contact_name.lower() in c.name.lower() or contact_name.lower() in (c.relation or "").lower():
            phone = c.phone
            matched_name = c.name
            break

    if not phone:
        return {"status": "error", "message": f"Contact '{contact_name}' non trouve parmi les contacts de confiance"}

    success, details = sms_client.send(phone, f"[Luna pour Ludo] {message}")
    if success:
        if _memory_manager:
            try:
                _memory_manager.add_note(
                    content=f"SMS envoye a {matched_name}: {message[:100]}",
                    context="visio_tool_call",
                    tags=["sms", "visio", matched_name],
                )
            except Exception:
                pass
        return {"status": "success", "message": f"SMS envoye a {matched_name}"}
    return {"status": "error", "message": f"Echec envoi SMS: {details.get('error', 'inconnu')}"}


async def _tool_create_instruction(args: Dict) -> Dict:
    """Cree une instruction depuis la visio."""
    if not _memory_manager or not _CORE_AVAILABLE:
        return {"status": "error", "message": "Memoire non disponible"}

    text = args.get("text", "")
    if not text:
        return {"status": "error", "message": "Texte de l'instruction requis"}

    parsed = InstructionParser.parse(text)

    action_map = {
        "reminder": SchemaActionType.REMINDER,
        "sms_contact": SchemaActionType.SMS,
        "call_contact": SchemaActionType.CALL,
        "check_in": SchemaActionType.REMINDER,
        "surveillance": SchemaActionType.ALERT,
        "note": SchemaActionType.NOTE,
        "daily_routine": SchemaActionType.REMINDER,
        "information": SchemaActionType.REMINDER,
    }
    action = action_map.get(parsed.action_type.value, SchemaActionType.REMINDER)

    type_map = {
        "once": InstructionType.ONE_TIME,
        "daily": InstructionType.DAILY,
        "weekly": InstructionType.RECURRING,
        "monthly": InstructionType.RECURRING,
        "weekdays": InstructionType.RECURRING,
        "weekend": InstructionType.RECURRING,
    }
    instr_type = type_map.get(parsed.recurrence.value, InstructionType.ONE_TIME)

    schedule_str = parsed.to_cron() or ""
    if not schedule_str and parsed.scheduled_time:
        schedule_str = f"{parsed.scheduled_time.hour:02d}:{parsed.scheduled_time.minute:02d}"

    instr = _memory_manager.add_instruction(
        description=text,
        action=action,
        instruction_type=instr_type,
        schedule=schedule_str,
        target=parsed.target or "self",
        message_template=parsed.message_template or "",
        priority=parsed.priority,
    )

    if _scheduler:
        try:
            _scheduler.schedule(instruction_id=instr.id, tenant_id=TENANT_ID, instruction=parsed)
        except Exception:
            pass

    confirmation = InstructionParser.format_confirmation(parsed)
    return {"status": "success", "message": confirmation, "instruction_id": instr.id}


async def _tool_create_note(args: Dict) -> Dict:
    """Prend une note depuis la visio."""
    if not _memory_manager:
        return {"status": "error", "message": "Memoire non disponible"}

    content = args.get("content", "")
    if not content:
        return {"status": "error", "message": "Contenu de la note requis"}

    note = _memory_manager.add_note(content=content, context="visio_tool_call", tags=["visio", "note"])
    return {"status": "success", "message": f"Note enregistree: {content[:50]}"}


async def _tool_get_contacts() -> Dict:
    """Liste les contacts de confiance."""
    if not _memory_manager:
        return {"status": "error", "message": "Memoire non disponible"}

    contacts = _memory_manager.list_trusted_contacts()
    if not contacts:
        return {"status": "success", "message": "Aucun contact de confiance enregistre.", "contacts": []}

    contact_list = [{"name": c.name, "relation": c.relation} for c in contacts]
    names = ", ".join([f"{c.name} ({c.relation})" for c in contacts])
    return {"status": "success", "message": f"Contacts de confiance: {names}", "contacts": contact_list}


async def _tool_generate_document(args: Dict) -> Dict:
    """Genere un document depuis la visio."""
    if not _doc_generator or not _memory_manager:
        return {"status": "error", "message": "Generateur de documents non disponible"}

    doc_type = args.get("doc_type", "courrier_admin")
    subject = args.get("subject", "")
    details = args.get("details", "")

    if not subject:
        return {"status": "error", "message": "Sujet du document requis"}

    # Genere le contenu avec GPT
    profile = _memory_manager.get_subscriber_profile()
    profile_dict = profile.model_dump() if profile else {}

    prompt = f"Redige un {doc_type} professionnel en francais.\nObjet: {subject}\n"
    if details:
        prompt += f"Details: {details}\n"
    if profile_dict.get("first_name"):
        prompt += f"Expediteur: {profile_dict.get('first_name', '')} {profile_dict.get('last_name', '')}\n"
    prompt += "Redige uniquement le corps du courrier, sans en-tete ni signature (ils seront ajoutes automatiquement)."

    try:
        gpt_resp = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.7,
            timeout=30,
        )
        body_text = gpt_resp.choices[0].message.content
    except Exception as e:
        return {"status": "error", "message": f"Erreur GPT: {e}"}

    if doc_type == "fiche_sante" and profile_dict:
        filename = _doc_generator.generate_health_sheet(profile_dict)
    else:
        filename = _doc_generator.generate_letter(
            doc_type=doc_type,
            subject=subject,
            body_text=body_text,
            profile=profile_dict,
        )

    url = f"/static/documents/{TENANT_ID}/{filename}"

    if _memory_manager:
        try:
            _memory_manager.add_note(
                content=f"Document genere: {subject} ({doc_type}) → {filename}",
                context="document",
                tags=["document", doc_type],
            )
        except Exception:
            pass

    return {"status": "success", "message": f"Document genere: {subject}. Telechargeable dans l'onglet Documents.", "url": url, "filename": filename}


async def _tool_alert_contacts(args: Dict) -> Dict:
    """Alerte tous les contacts de confiance."""
    if not _memory_manager or not sms_client.is_configured:
        return {"status": "error", "message": "Service SMS non disponible"}

    reason = args.get("reason", "situation preoccupante")
    contacts = _memory_manager.list_trusted_contacts()

    if not contacts:
        return {"status": "error", "message": "Aucun contact de confiance enregistre"}

    profile = _memory_manager.get_subscriber_profile()
    name = profile.first_name if profile else "votre proche"

    sent = 0
    for c in contacts:
        msg = f"[ALERTE Luna] {name} a besoin d'aide. Raison: {reason}. Merci de verifier qu'il va bien. En cas d'urgence, appelez le 112."
        success, _ = sms_client.send(c.phone, msg)
        if success:
            sent += 1

    if _memory_manager:
        try:
            _memory_manager.add_note(
                content=f"ALERTE envoyee a {sent} contact(s): {reason}",
                context="alerte_urgence",
                tags=["urgence", "alerte"],
            )
        except Exception:
            pass

    return {"status": "success", "message": f"Alerte envoyee a {sent} contact(s) de confiance"}


async def _tool_report_observation(args: Dict) -> Dict:
    """Log une observation visuelle de Tavus Raven pendant un appel video."""
    if not _memory_manager:
        return {"status": "error", "message": "Memoire non disponible"}

    observation = args.get("observation", "")
    severity = args.get("severity", "info")

    if observation:
        _memory_manager.add_note(
            content=f"[Observation visio] {observation}",
            context="visio_perception",
            tags=["perception", "visio", "raven", severity],
        )
        _memory_manager.log_perception_event({
            "type": "visio_observation",
            "severity": severity,
            "description": observation,
            "source": "tavus_raven",
            "timestamp": datetime.utcnow().isoformat(),
        })

    return {"status": "success", "message": "Observation notee"}


async def _handle_tavus_transcription(body: Dict) -> Dict:
    """Sauvegarde la transcription d'un appel Tavus."""
    if not _memory_manager:
        return {"status": "ok"}

    transcript = body.get("transcript", "") or body.get("data", {}).get("transcript", "")
    conversation_id = body.get("conversation_id", "")

    if transcript:
        try:
            _memory_manager.add_note(
                content=f"Transcription visio: {transcript[:2000]}",
                context="visio_transcription",
                tags=["visio", "transcription", conversation_id],
            )
            logger.info(f"Tavus transcription saved for {conversation_id}")
        except Exception as e:
            logger.warning(f"Failed to save transcription: {e}")

    return {"status": "ok"}


# =========================================================================
# DOCUMENTS ENDPOINTS
# =========================================================================

class DocumentRequest(BaseModel):
    doc_type: str = Field(..., max_length=50)
    subject: str = Field(default="", max_length=500)
    details: str = Field(default="", max_length=2000)
    recipient: str = Field(default="", max_length=200)


@app.post("/api/documents/generate")
async def generate_document(req: DocumentRequest):
    """Genere un document DOCX via GPT + python-docx"""
    if not _doc_generator:
        return JSONResponse(status_code=503, content={"error": "Generateur non disponible"})

    profile_dict = {}
    if _memory_manager:
        profile = _memory_manager.get_subscriber_profile()
        if profile:
            profile_dict = profile.model_dump()

    # Special case: fiche sante (from profile directly)
    if req.doc_type == "fiche_sante" and profile_dict:
        filename = _doc_generator.generate_health_sheet(profile_dict)
        return {
            "success": True,
            "filename": filename,
            "download_url": f"/static/documents/{TENANT_ID}/{filename}",
            "type": "fiche_sante",
        }

    # Special case: export notes
    if req.doc_type == "export_notes" and _memory_manager:
        notes = _memory_manager.list_notes(limit=200)
        note_dicts = [{"content": n.content, "context": n.context, "created_at": n.created_at.isoformat() if n.created_at else "", "tags": n.tags} for n in notes]
        filename = _doc_generator.generate_notes_export(note_dicts)
        return {
            "success": True,
            "filename": filename,
            "download_url": f"/static/documents/{TENANT_ID}/{filename}",
            "type": "export_notes",
        }

    # General case: GPT generates the body
    prompt = f"Redige un {req.doc_type} professionnel en francais.\nObjet: {req.subject}\n"
    if req.details:
        prompt += f"Details: {req.details}\n"
    if req.recipient:
        prompt += f"Destinataire: {req.recipient}\n"
    if profile_dict.get("first_name"):
        prompt += f"Expediteur: {profile_dict.get('first_name', '')} {profile_dict.get('last_name', '')}, {profile_dict.get('address', '')}, {profile_dict.get('city', '')}\n"
    prompt += "Redige uniquement le corps du courrier, sans en-tete ni signature (ils seront ajoutes automatiquement). Ton professionnel et respectueux."

    try:
        gpt_resp = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.7,
            timeout=30,
        )
        body_text = gpt_resp.choices[0].message.content
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"GPT error: {e}"})

    filename = _doc_generator.generate_letter(
        doc_type=req.doc_type,
        subject=req.subject,
        body_text=body_text,
        recipient=req.recipient,
        profile=profile_dict,
    )

    return {
        "success": True,
        "filename": filename,
        "download_url": f"/static/documents/{TENANT_ID}/{filename}",
        "type": req.doc_type,
        "preview": body_text[:300],
    }


@app.get("/api/documents")
async def list_documents():
    """Liste les documents generes"""
    if not _doc_generator:
        return JSONResponse(status_code=503, content={"error": "Generateur non disponible"})
    docs = _doc_generator.list_documents()
    for d in docs:
        d["download_url"] = f"/static/documents/{TENANT_ID}/{d['filename']}"
    return {"documents": docs, "count": len(docs)}


@app.get("/static/documents/{tenant_id}/{filename}")
async def serve_document(tenant_id: int, filename: str):
    """Sert un document genere au telechargement"""
    # Securite : empeche path traversal
    if ".." in filename or "/" in filename:
        return JSONResponse(status_code=400, content={"error": "Nom de fichier invalide"})
    filepath = os.path.join(os.path.dirname(__file__), "static", "documents", str(tenant_id), filename)
    if not os.path.exists(filepath):
        return JSONResponse(status_code=404, content={"error": "Document non trouve"})
    return FileResponse(
        filepath,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )


# =========================================================================
# PERCEPTION - Aide contextuelle visuelle
# =========================================================================

PERCEPTION_INTERVAL = 10  # secondes entre captures


async def _perception_loop():
    """Background loop: capture + detect toutes les PERCEPTION_INTERVAL secondes."""
    logger.info(f"Perception loop started ({PERCEPTION_INTERVAL}s interval)")
    while True:
        try:
            await asyncio.sleep(PERCEPTION_INTERVAL)

            if not _perception_detector or not _perception_analyzer:
                continue
            if not _memory_manager or not _memory_manager.is_perception_enabled():
                continue
            if not _perception_detector.is_camera_available():
                continue

            # YOLO + cv2 sont bloquants → executor
            loop = asyncio.get_event_loop()
            frame_analysis = await loop.run_in_executor(
                None, _perception_detector.capture_and_detect
            )

            if not frame_analysis:
                continue

            scene_state = _perception_analyzer.analyze(frame_analysis)
            _memory_manager.update_perception_state(scene_state)

            # Log les anomalies significatives
            for abn in scene_state.abnormalities:
                if abn["severity"] in ("attention", "concern"):
                    _memory_manager.log_perception_event(abn)
                    try:
                        _memory_manager.add_note(
                            content=f"[Perception] {abn['description']}",
                            context="perception",
                            tags=["perception", abn["type"], abn["severity"]],
                        )
                    except Exception:
                        pass

        except asyncio.CancelledError:
            logger.info("Perception loop stopped")
            break
        except Exception as e:
            logger.error(f"Perception loop error: {e}")


@app.post("/api/perception/start")
async def start_perception():
    """Active la perception camera (opt-in)."""
    if not _perception_detector or not _memory_manager:
        return JSONResponse(status_code=503, content={"error": "Perception non disponible"})

    if not _perception_detector._initialized:
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(None, _perception_detector.initialize)
        if not success:
            return JSONResponse(status_code=500, content={
                "error": "Camera non accessible. Verifie que la webcam est branchee."
            })

    _memory_manager.set_perception_enabled(True)
    logger.info("Perception activated by user")
    return {"success": True, "message": "Perception activee"}


@app.post("/api/perception/stop")
async def stop_perception():
    """Desactive la perception camera."""
    if not _memory_manager:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})

    _memory_manager.set_perception_enabled(False)
    if _perception_detector:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _perception_detector.release)

    if _perception_analyzer:
        _perception_analyzer.reset()

    logger.info("Perception deactivated by user")
    return {"success": True, "message": "Perception desactivee, camera liberee"}


@app.get("/api/perception/status")
async def perception_status():
    """Statut de la perception."""
    enabled = _memory_manager.is_perception_enabled() if _memory_manager else False
    camera_ok = _perception_detector.is_camera_available() if _perception_detector else False

    state = None
    if enabled and _memory_manager:
        scene = _memory_manager.get_perception_state()
        if scene:
            state = scene.to_dict()

    return {
        "available": _perception_detector is not None,
        "enabled": enabled,
        "camera_connected": camera_ok,
        "current_scene": state,
    }


@app.get("/api/perception/scene")
async def get_current_scene():
    """Scene actuelle detectee."""
    if not _memory_manager:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    scene = _memory_manager.get_perception_state()
    if not scene:
        return {"scene": None, "message": "Aucune scene disponible"}
    return {"scene": scene.to_dict()}


# =========================================================================
# INSTRUCTION ENGINE - Background loop
# =========================================================================

async def _load_instructions_to_scheduler():
    """Charge les instructions actives depuis Redis dans le scheduler au demarrage"""
    if not _memory_manager or not _scheduler:
        return
    try:
        instructions = _memory_manager.list_active_instructions()
        loaded = 0
        for instr in instructions:
            try:
                # Re-parse l'instruction pour obtenir un ParsedInstruction
                parsed = InstructionParser.parse(instr.description)
                _scheduler.schedule(
                    instruction_id=instr.id,
                    tenant_id=TENANT_ID,
                    instruction=parsed,
                )
                loaded += 1
            except Exception as e:
                logger.warning(f"Could not schedule instruction {instr.id}: {e}")
        logger.info(f"Loaded {loaded}/{len(instructions)} instructions into scheduler")
    except Exception as e:
        logger.warning(f"Failed to load instructions: {e}")


async def _instruction_loop():
    """Boucle de fond : verifie les taches dues toutes les 30s et les execute"""
    logger.info("Instruction loop started (30s interval)")
    while True:
        try:
            await asyncio.sleep(30)
            if not _scheduler or not _executor:
                continue

            due_tasks = _scheduler.pop_due_tasks()
            if not due_tasks:
                continue

            logger.info(f"Instruction loop: {len(due_tasks)} task(s) due")
            for task in due_tasks:
                try:
                    result = await _executor.execute(
                        task,
                        context={"tenant_id": task.tenant_id},
                    )
                    logger.info(
                        f"Instruction {task.instruction_id} executed: "
                        f"{result.status.value} - {result.message}"
                    )

                    # Marque l'instruction comme executee dans Redis
                    if _memory_manager:
                        try:
                            _memory_manager.mark_instruction_executed(task.instruction_id)
                        except Exception:
                            pass

                    # Enregistre le compte-rendu comme note
                    if _memory_manager:
                        try:
                            _memory_manager.add_note(
                                content=f"[Auto] {result.message}",
                                context="instruction_execution",
                                tags=["auto", result.status.value, task.instruction.action_type.value],
                            )
                        except Exception:
                            pass

                    # Replanifie si recurrent (le scheduler gere ca)
                    if result.status.value in ("success", "partial"):
                        _scheduler.complete_task(task, result=result.message)
                    else:
                        _scheduler.fail_task(task, error=result.error or "unknown")

                except Exception as e:
                    logger.error(f"Error executing task {task.instruction_id}: {e}")
                    _scheduler.fail_task(task, error=str(e))

        except asyncio.CancelledError:
            logger.info("Instruction loop stopped")
            break
        except Exception as e:
            logger.error(f"Instruction loop error: {e}")


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
    logger.info(f"Scheduler: {'OK' if _scheduler else 'OFFLINE'}")
    logger.info(f"Executor: {'OK' if _executor else 'OFFLINE'}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8888,
        ssl_keyfile=os.path.join(ssl_dir, "key.pem"),
        ssl_certfile=os.path.join(ssl_dir, "cert.pem"),
    )
