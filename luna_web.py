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
    import traceback
    print(f"CORE IMPORT ERROR: {_import_err}")
    traceback.print_exc()

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("luna_web")

# --- Config ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise SystemExit("ERREUR FATALE: OPENAI_API_KEY manquante dans .env. Voir .env.example.")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
ADMIN_NUMBER = os.getenv("ADMIN_NUMBER", "")
if not ADMIN_NUMBER:
    raise SystemExit("ERREUR FATALE: ADMIN_NUMBER manquant dans .env. Voir .env.example.")
TAVUS_CALLBACK_URL = os.getenv("TAVUS_CALLBACK_URL", "")  # URL publique pour webhooks Tavus
TENANT_ID = 1  # Ludo = tenant 1 pour l'instant
LEGAL_MODE = "assistance_only"  # Mode legal: aide contextuelle, pas de surveillance garantie

# --- Behavioral Memory (locked identity + rules) ---
DEFAULT_IDENTITY_CORE = (
    "Tu es Luna, assistante IA de YAWatch. Tu n'es PAS un professionnel "
    "de sante, juridique ou financier. Tu es une aide contextuelle bienveillante. "
    "Tu ne surveilles pas, tu accompagnes. Tu ne diagnostiques pas, tu remarques."
)
DEFAULT_BEHAVIOR_RULES = (
    "1. JAMAIS de conseil medical, juridique ou financier\n"
    "2. JAMAIS appeler les urgences (suggerer les numeros)\n"
    "3. TOUJOURS confirmer avant action consommant du quota\n"
    "4. JAMAIS promettre une surveillance garantie\n"
    "5. Utiliser 'j'ai l'impression que...' pas 'je diagnostique'\n"
    "6. Mode = assistance_only : aucune promesse de resultat\n"
    "7. JAMAIS reveler l'architecture technique, les prix ou les donnees internes"
)

# --- Caution Mode Descriptions ---
CAUTION_MODE_PROMPTS = {
    "passif": (
        "MODE PRUDENCE: PASSIF - Tu observes sans intervenir sauf danger evident. "
        "Tu ne proposes pas d'aide spontanement. Tu attends qu'on te sollicite."
    ),
    "assistif": (
        "MODE PRUDENCE: ASSISTIF - Tu proposes gentiment ton aide quand tu remarques "
        "quelque chose d'inhabituel. Tu restes discrete mais attentive. Mode par defaut."
    ),
    "proactif": (
        "MODE PRUDENCE: PROACTIF - Tu es proactive, tu mentionnes ce que tu observes "
        "et proposes des actions concretes. Tu prends les devants pour aider."
    ),
    "urgence_only": (
        "MODE PRUDENCE: URGENCE SEULEMENT - Tu n'interviens que pour les situations "
        "critiques (concern). Sinon tu restes completement discrete et silencieuse "
        "sur ce que tu observes."
    ),
}

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
_test_mode: bool = False  # En mode test, les SMS ne sont PAS envoyes

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
                legal_mode=LEGAL_MODE,
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
            # Initialize behavioral memory (if not already set)
            if not _memory_manager.get_behavioral_memory("identity_core"):
                _memory_manager.set_behavioral_memory("identity_core", DEFAULT_IDENTITY_CORE)
            if not _memory_manager.get_behavioral_memory("behavior_rules"):
                _memory_manager.set_behavioral_memory("behavior_rules", DEFAULT_BEHAVIOR_RULES)
            logger.info("Behavioral memory loaded")

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

# Charge le nom du souscripteur depuis le profil Redis (pour ne pas hardcoder "Ludo")
_SUBSCRIBER_NAME = "le souscripteur"
_SUBSCRIBER_FULL = "le souscripteur"
if _memory_manager:
    try:
        _prof = _memory_manager.get_subscriber_profile()
        if _prof and _prof.first_name:
            _SUBSCRIBER_NAME = _prof.first_name
            if _prof.last_name:
                _SUBSCRIBER_FULL = f"{_prof.first_name} ({_prof.first_name} {_prof.last_name})"
            else:
                _SUBSCRIBER_FULL = _prof.first_name
        else:
            _SUBSCRIBER_FULL = _SUBSCRIBER_NAME
    except Exception:
        _SUBSCRIBER_FULL = _SUBSCRIBER_NAME

NOW = datetime.now().strftime("%A %d %B %Y, %Hh%M")

LUNA_SYSTEM_PROMPT = f"""Tu es Luna, l'assistante IA personnelle de YAWatch-Luna.

=== IDENTITE ===
- Tu es Luna, une compagne bienveillante et chaleureuse, disponible 24h/24, 7j/7.
- Tu parles en francais, ton rassurant, moderne et empathique.
- Tu tutoies le souscripteur sauf demande contraire.
- Tu es au service de {_SUBSCRIBER_FULL}.
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
Quand le souscripteur est en appel video avec Luna, il peut demander :
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

=== MODE LEGAL : {LEGAL_MODE} ===
Luna est une AIDE CONTEXTUELLE, PAS un service de securite ni de surveillance.
- Tu ne promets JAMAIS de resultat, de protection ou de surveillance garantie.
- Tu es une compagne bienveillante, pas un dispositif medical ou de securite.
- Tu accompagnes, tu ne surveilles pas. Tu remarques, tu ne diagnostiques pas.

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

=== PRUDENCE VERBALE (OBLIGATOIRE) ===
Tu ne dis JAMAIS ces mots/expressions :
- "surveillance", "je surveille", "sous surveillance"
- "diagnostic", "je diagnostique"
- "chute" (dire "situation au sol")
- "urgence medicale" (dire "situation preoccupante")
- "detection certaine", "je garantis", "je protege"
Tu utilises TOUJOURS ces formulations :
- "j'ai l'impression que...", "il me semble que...", "j'ai remarque que..."
- "il se pourrait que...", "cela ressemble a..."
- "je te suggere de...", "peut-etre que..."

=== STYLE ===
- Reponses concises et naturelles
- Chaleureuse mais pas infantilisante
- Proactive : propose des actions concretes
- Confirme avant d'executer toute action

Commence par saluer {_SUBSCRIBER_NAME} chaleureusement."""

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

        # Inject behavioral memory (locked identity + rules) before user message
        if _memory_manager:
            try:
                rules = _memory_manager.get_behavioral_rules()
                if rules["identity_core"] or rules["behavior_rules"]:
                    behavioral_prompt = (
                        f"[MEMOIRE COMPORTEMENTALE VERROUILLEE]\n"
                        f"IDENTITE: {rules['identity_core']}\n"
                        f"REGLES: {rules['behavior_rules']}"
                    )
                    messages.append({"role": "system", "content": behavioral_prompt})
            except Exception:
                pass

        # Inject caution mode from profile
        _caution_mode = "assistif"
        if _memory_manager:
            try:
                profile = _memory_manager.get_subscriber_profile()
                if profile:
                    _caution_mode = getattr(profile, "caution_mode", "assistif") or "assistif"
            except Exception:
                pass
        caution_prompt = CAUTION_MODE_PROMPTS.get(_caution_mode, CAUTION_MODE_PROMPTS["assistif"])
        messages.append({"role": "system", "content": caution_prompt})

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

        # Inject perception context if available (filtered by caution_mode)
        if _perception_analyzer and _memory_manager:
            try:
                if _memory_manager.is_perception_enabled():
                    perception_ctx = _perception_analyzer.get_context_for_luna(
                        caution_mode=_caution_mode
                    )
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

        # Legal compliance check on Luna's response
        if _safety_guardian:
            try:
                compliant, violations = _safety_guardian.check_legal_compliance(luna_msg)
                if not compliant:
                    logger.warning(f"Luna response legal violations: {violations}")
            except Exception:
                pass

        # Log event in chronological journal
        if _memory_manager:
            try:
                _memory_manager.log_event(
                    category="communication",
                    description=f"Chat: {req.message[:80]}... → Luna repond",
                    source="chat",
                )
            except Exception:
                pass

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
        return {"response": f"Salut ! Luna a un souci technique ({type(e).__name__}). Reessaie."}


@app.post("/api/call")
async def start_call():
    """Crée un appel vidéo Tavus et enregistre la conversation"""
    context = build_tavus_context(
        subscriber_name=_SUBSCRIBER_NAME,
        memory_manager=tavus_client.memory,
    )
    success, data = await tavus_client.create_conversation(
        tenant_id=TENANT_ID,
        custom_greeting=f"Salut {_SUBSCRIBER_NAME} ! Ravie de te voir. Comment je peux t'aider ?",
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

    # Read caution_mode from profile
    _cm = "assistif"
    if _memory_manager:
        try:
            _p = _memory_manager.get_subscriber_profile()
            if _p:
                _cm = getattr(_p, "caution_mode", "assistif") or "assistif"
        except Exception:
            pass

    return {
        "luna": "online",
        "legal_mode": LEGAL_MODE,
        "caution_mode": _cm,
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
# FAMILY PACK ENDPOINTS
# =========================================================================

from core.memory.schemas import (
    FamilyMember, FamilyGroup, FamilyRole, FamilyMemberType,
    EscalationRule, EscalationStage, FamilyMessage, FamilyMessageType,
    FamilyAuditLog, DistressLevel, DistressKeywords
)
import random
import string


def _generate_otp() -> str:
    """Genere un code OTP a 6 chiffres"""
    return ''.join(random.choices(string.digits, k=6))


def _log_family_audit(action: str, actor_phone: str, actor_name: str,
                      target_phone: str = None, target_name: str = None,
                      details: dict = None, severity: str = "info"):
    """Log une action dans l'audit famille"""
    if not _redis_client:
        return
    import json
    from datetime import datetime
    audit = FamilyAuditLog(
        tenant_id=TENANT_ID,
        actor_phone=actor_phone,
        actor_name=actor_name,
        action=action,
        target_phone=target_phone,
        target_name=target_name,
        details=details or {},
        severity=severity,
    )
    _redis_client.add_family_audit(TENANT_ID, json.dumps(audit.to_redis()))


# --- Family Group ---

@app.get("/api/family")
async def get_family():
    """Recupere le groupe familial et ses membres"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Redis non disponible"})

    group_data = _redis_client.get_family_group(TENANT_ID)
    if not group_data:
        return {"group": None, "members": [], "count": 0}

    group = FamilyGroup.from_redis(group_data)
    members = []
    for phone in _redis_client.get_family_members(TENANT_ID):
        member_data = _redis_client.get_family_member(TENANT_ID, phone)
        if member_data:
            member = FamilyMember.from_redis(member_data)
            members.append({
                "id": member.id,
                "phone": member.phone,
                "name": member.name,
                "relation": member.relation,
                "member_type": member.member_type.value,
                "role": member.role.value,
                "age": member.age,
                "is_verified": member.is_verified,
                "is_minor": member.is_minor(),
                "can_see_history": member.can_see_history,
                "can_send_messages": member.can_send_messages,
                "can_receive_alerts": member.can_receive_alerts,
                "is_active": member.is_active,
                "created_at": member.created_at.isoformat(),
            })

    return {
        "group": {
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "allow_internal_messaging": group.allow_internal_messaging,
            "share_activity_summary": group.share_activity_summary,
            "auto_escalate": group.auto_escalate,
        },
        "members": members,
        "count": len(members),
    }


@app.post("/api/family")
async def create_family(request: Request):
    """Cree ou met a jour le groupe familial"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Redis non disponible"})

    data = await request.json()
    from datetime import datetime

    # Verifier si groupe existe deja
    existing = _redis_client.get_family_group(TENANT_ID)
    if existing:
        # Mise a jour
        group = FamilyGroup.from_redis(existing)
        if "name" in data:
            group.name = data["name"]
        if "description" in data:
            group.description = data["description"]
        if "allow_internal_messaging" in data:
            group.allow_internal_messaging = data["allow_internal_messaging"]
        if "share_activity_summary" in data:
            group.share_activity_summary = data["share_activity_summary"]
        if "auto_escalate" in data:
            group.auto_escalate = data["auto_escalate"]
        group.updated_at = datetime.utcnow()
    else:
        # Creation
        group = FamilyGroup(
            tenant_id=TENANT_ID,
            name=data.get("name", "Ma famille"),
            description=data.get("description", ""),
        )

    _redis_client.set_family_group(TENANT_ID, group.to_redis())
    _log_family_audit("family_group_created" if not existing else "family_group_updated",
                      "system", "Luna", details={"name": group.name})

    return {"success": True, "group_id": group.id}


# --- Family Members ---

@app.get("/api/family/members")
async def list_family_members():
    """Liste tous les membres de la famille"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Redis non disponible"})

    members = []
    for phone in _redis_client.get_family_members(TENANT_ID):
        member_data = _redis_client.get_family_member(TENANT_ID, phone)
        if member_data:
            member = FamilyMember.from_redis(member_data)
            members.append({
                "id": member.id,
                "phone": member.phone,
                "name": member.name,
                "relation": member.relation,
                "role": member.role.value,
                "member_type": member.member_type.value,
                "age": member.age,
                "is_verified": member.is_verified,
                "is_minor": member.is_minor(),
                "needs_parental_consent": member.needs_parental_consent(),
            })

    return {"members": members, "count": len(members)}


@app.post("/api/family/members")
async def add_family_member(request: Request):
    """Ajoute un membre a la famille (envoie OTP de verification)"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Redis non disponible"})

    data = await request.json()

    # Validation
    phone = data.get("phone", "").strip()
    name = data.get("name", "").strip()
    relation = data.get("relation", "").strip()

    if not phone or not name:
        return JSONResponse(status_code=400, content={"error": "phone et name requis"})

    # Verifier si deja membre
    if _redis_client.get_family_member(TENANT_ID, phone):
        return JSONResponse(status_code=400, content={"error": "Ce membre existe deja"})

    # Valider le role
    role_str = data.get("role", "information_only")
    valid_roles = [r.value for r in FamilyRole]
    if role_str not in valid_roles:
        return JSONResponse(status_code=400, content={
            "error": f"Role invalide: {role_str}. Roles valides: {', '.join(valid_roles)}"
        })

    # Determiner le type de membre selon l'age
    age = data.get("age")
    member_type = FamilyMemberType.ADULT
    if age:
        age = int(age)
        if age < 13:
            member_type = FamilyMemberType.CHILD
        elif age < 18:
            member_type = FamilyMemberType.TEEN
        elif age >= 65:
            member_type = FamilyMemberType.SENIOR

    # Creer le membre (non verifie)
    member = FamilyMember(
        tenant_id=TENANT_ID,
        phone=phone,
        name=name,
        relation=relation,
        member_type=member_type,
        role=FamilyRole(role_str),
        age=age,
        is_verified=False,
        can_see_history=data.get("can_see_history", False),
        can_send_messages=data.get("can_send_messages", True),
        can_receive_alerts=data.get("can_receive_alerts", True),
    )

    # Generer et stocker OTP
    otp = _generate_otp()
    member.verification_code = otp
    _redis_client.set_otp(phone, otp)

    # Ajouter le membre
    success = _redis_client.add_family_member(TENANT_ID, phone, member.to_redis())
    if not success:
        return JSONResponse(status_code=400, content={"error": "Quota de membres atteint (max 15)"})

    # Envoyer SMS avec OTP
    sms_sent = False
    if sms_client:
        message = f"Luna Family: {name}, votre code de verification est {otp}. Valide 10 min."
        sms_sent, _ = sms_client.send(phone, message)

    _log_family_audit("member_invited", "system", "Luna",
                      target_phone=phone, target_name=name,
                      details={"role": member.role.value, "sms_sent": sms_sent})

    return {
        "success": True,
        "member_id": member.id,
        "verification_required": True,
        "sms_sent": sms_sent,
        "message": f"Code de verification envoye a {phone}" if sms_sent else "Echec envoi SMS"
    }


@app.post("/api/family/members/{phone}/verify")
async def verify_family_member(phone: str, request: Request):
    """Verifie un membre avec son code OTP"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Redis non disponible"})

    data = await request.json()
    otp = data.get("code", "").strip()

    if not otp:
        return JSONResponse(status_code=400, content={"error": "Code requis"})

    # Verifier OTP
    if not _redis_client.verify_otp(phone, otp):
        return JSONResponse(status_code=400, content={"error": "Code invalide ou expire"})

    # Marquer comme verifie
    from datetime import datetime
    _redis_client.update_family_member(TENANT_ID, phone, {
        "is_verified": "1",
        "verified_at": datetime.utcnow().isoformat(),
        "verification_code": "",
    })

    member_data = _redis_client.get_family_member(TENANT_ID, phone)
    name = member_data.get("name", "Membre") if member_data else "Membre"

    _log_family_audit("member_verified", phone, name)

    return {"success": True, "message": f"{name} verifie avec succes"}


@app.patch("/api/family/members/{phone}")
async def update_family_member(phone: str, request: Request):
    """Met a jour un membre de la famille"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Redis non disponible"})

    data = await request.json()

    member_data = _redis_client.get_family_member(TENANT_ID, phone)
    if not member_data:
        return JSONResponse(status_code=404, content={"error": "Membre non trouve"})

    # Champs modifiables
    updates = {}
    if "name" in data:
        updates["name"] = data["name"]
    if "role" in data:
        updates["role"] = data["role"]
    if "can_see_history" in data:
        updates["can_see_history"] = "1" if data["can_see_history"] else "0"
    if "can_send_messages" in data:
        updates["can_send_messages"] = "1" if data["can_send_messages"] else "0"
    if "can_receive_alerts" in data:
        updates["can_receive_alerts"] = "1" if data["can_receive_alerts"] else "0"
    if "is_active" in data:
        updates["is_active"] = "1" if data["is_active"] else "0"

    from datetime import datetime
    updates["updated_at"] = datetime.utcnow().isoformat()

    _redis_client.update_family_member(TENANT_ID, phone, updates)

    _log_family_audit("member_updated", "system", "Luna",
                      target_phone=phone, target_name=member_data.get("name"),
                      details=updates)

    return {"success": True}


@app.delete("/api/family/members/{phone}")
async def remove_family_member(phone: str):
    """Supprime un membre de la famille"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Redis non disponible"})

    member_data = _redis_client.get_family_member(TENANT_ID, phone)
    if not member_data:
        return JSONResponse(status_code=404, content={"error": "Membre non trouve"})

    name = member_data.get("name", "Membre")
    _redis_client.remove_family_member(TENANT_ID, phone)

    _log_family_audit("member_removed", "system", "Luna",
                      target_phone=phone, target_name=name)

    return {"success": True}


# --- Family Messages (Internal Messaging) ---

@app.get("/api/family/messages")
async def get_family_messages(limit: int = 50, phone: str = None):
    """Recupere les messages famille (optionnel: filtre par destinataire)"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Redis non disponible"})

    messages = []
    for msg_id in _redis_client.get_family_messages(TENANT_ID, limit=limit):
        msg_data = _redis_client.get_family_message(TENANT_ID, msg_id)
        if msg_data:
            msg = FamilyMessage.from_redis(msg_data)
            # Filtrer par destinataire si specifie
            if phone and msg.to_phone and msg.to_phone != phone:
                continue
            messages.append({
                "id": msg.id,
                "from_phone": msg.from_phone,
                "from_name": msg.from_name,
                "to_phone": msg.to_phone,
                "to_name": msg.to_name,
                "content": msg.content,
                "message_type": msg.message_type.value,
                "is_read": msg.is_read,
                "read_by": msg.read_by,
                "created_at": msg.created_at.isoformat(),
                "requires_response": msg.requires_response,
                "responses": msg.responses,
            })

    return {"messages": messages, "count": len(messages)}


@app.post("/api/family/messages")
async def send_family_message(request: Request):
    """Envoie un message interne famille via Luna"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Redis non disponible"})

    data = await request.json()

    from_phone = data.get("from_phone", "luna")
    from_name = data.get("from_name", "Luna")
    to_phone = data.get("to_phone")  # None = groupe
    content = data.get("content", "").strip()
    message_type = data.get("message_type", "update")

    if not content:
        return JSONResponse(status_code=400, content={"error": "Contenu requis"})

    # Creer le message
    msg = FamilyMessage(
        tenant_id=TENANT_ID,
        from_phone=from_phone,
        from_name=from_name,
        to_phone=to_phone,
        to_name=data.get("to_name"),
        content=content,
        message_type=FamilyMessageType(message_type),
        requires_response=data.get("requires_response", False),
    )

    _redis_client.add_family_message(TENANT_ID, msg.id, msg.to_redis())

    # Notifier les destinataires (push ou SMS selon config)
    notified = []
    if to_phone:
        # Message direct
        member_data = _redis_client.get_family_member(TENANT_ID, to_phone)
        if member_data and member_data.get("can_receive_alerts") == "1":
            notified.append(to_phone)
    else:
        # Message groupe - notifier tous les membres actifs
        for phone in _redis_client.get_family_members(TENANT_ID):
            if phone != from_phone:  # Ne pas notifier l'expediteur
                member_data = _redis_client.get_family_member(TENANT_ID, phone)
                if member_data and member_data.get("is_active") == "1":
                    notified.append(phone)

    _log_family_audit("message_sent", from_phone, from_name,
                      target_phone=to_phone,
                      details={"type": message_type, "notified": len(notified)})

    return {
        "success": True,
        "message_id": msg.id,
        "notified_count": len(notified),
    }


@app.post("/api/family/messages/{msg_id}/read")
async def mark_message_read(msg_id: str, request: Request):
    """Marque un message comme lu par un membre"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Redis non disponible"})

    data = await request.json()
    phone = data.get("phone", "") or data.get("reader_phone", "")
    phone = phone.strip() if phone else ""

    if not phone:
        return JSONResponse(status_code=400, content={"error": "phone requis"})

    msg_data = _redis_client.get_family_message(TENANT_ID, msg_id)
    if not msg_data:
        return JSONResponse(status_code=404, content={"error": "Message non trouve"})

    import json
    from datetime import datetime
    read_by = json.loads(msg_data.get("read_by", "[]"))
    if phone not in read_by:
        read_by.append(phone)
        _redis_client.update_family_message(TENANT_ID, msg_id, {
            "read_by": json.dumps(read_by),
            "is_read": "1" if len(read_by) > 0 else "0",
            "read_at": datetime.utcnow().isoformat(),
        })

    return {"success": True}


# --- Escalation Rules ---

@app.get("/api/family/escalation")
async def get_escalation_rules():
    """Recupere les regles d'escalade"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Redis non disponible"})

    rules = []
    for rule_id in _redis_client.get_escalation_rules(TENANT_ID):
        rule_data = _redis_client.get_escalation_rule(TENANT_ID, rule_id)
        if rule_data:
            rule = EscalationRule.from_redis(rule_data)
            rules.append({
                "id": rule.id,
                "name": rule.name,
                "description": rule.description,
                "trigger_distress_level": rule.trigger_distress_level.value,
                "trigger_member_types": [t.value for t in rule.trigger_member_types],
                "stages": [s.to_dict() for s in rule.stages],
                "enabled": rule.enabled,
                "trigger_count": rule.trigger_count,
            })

    return {"rules": rules, "count": len(rules)}


@app.post("/api/family/escalation")
async def create_escalation_rule(request: Request):
    """Cree une regle d'escalade"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Redis non disponible"})

    data = await request.json()

    # Creer les etapes
    stages = []
    for stage_data in data.get("stages", []):
        stage = EscalationStage(
            order=stage_data["order"],
            delay_minutes=stage_data.get("delay_minutes", 0),
            target_roles=[FamilyRole(r) for r in stage_data["target_roles"]],
            message_template=stage_data.get("message_template", ""),
            include_emergency_numbers=stage_data.get("include_emergency_numbers", False),
        )
        stages.append(stage)

    rule = EscalationRule(
        tenant_id=TENANT_ID,
        name=data.get("name", "Regle d'escalade"),
        description=data.get("description", ""),
        trigger_distress_level=DistressLevel(data.get("trigger_distress_level", "high")),
        trigger_member_types=[FamilyMemberType(t) for t in data.get("trigger_member_types", [])],
        trigger_keywords=data.get("trigger_keywords", []),
        stages=stages,
        enabled=data.get("enabled", True),
    )

    _redis_client.add_escalation_rule(TENANT_ID, rule.id, rule.to_redis())

    _log_family_audit("escalation_rule_created", "system", "Luna",
                      details={"name": rule.name, "stages": len(stages)})

    return {"success": True, "rule_id": rule.id}


@app.delete("/api/family/escalation/{rule_id}")
async def delete_escalation_rule(rule_id: str):
    """Supprime une regle d'escalade"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Redis non disponible"})

    _redis_client.delete_escalation_rule(TENANT_ID, rule_id)

    _log_family_audit("escalation_rule_deleted", "system", "Luna",
                      details={"rule_id": rule_id})

    return {"success": True}


# --- Distress Detection (for Family Pack) ---

@app.post("/api/family/detect-distress")
async def detect_distress(request: Request):
    """Analyse un texte pour detecter la detresse (ados/enfants)"""
    data = await request.json()
    text = data.get("text", "")
    from_phone = data.get("from_phone")

    if not text:
        return JSONResponse(status_code=400, content={"error": "text requis"})

    # Detecter le niveau de detresse
    level, keywords, category = DistressKeywords.detect_level(text)

    result = {
        "level": level.value,
        "keywords_found": keywords,
        "category": category,
        "action_required": level in [DistressLevel.HIGH, DistressLevel.CRITICAL],
    }

    # Si niveau eleve, declencher l'escalade
    if level in [DistressLevel.HIGH, DistressLevel.CRITICAL] and from_phone:
        member_data = _redis_client.get_family_member(TENANT_ID, from_phone) if _redis else None
        if member_data:
            member_name = member_data.get("name", "Membre")
            result["escalation_triggered"] = True
            result["message"] = f"Alerte detresse detectee pour {member_name}"

            # Log et notifier
            _log_family_audit("distress_detected", from_phone, member_name,
                              details={"level": level.value, "category": category},
                              severity="critical" if level == DistressLevel.CRITICAL else "alert")

    return result


# --- Family Audit Log ---

@app.get("/api/family/audit")
async def get_family_audit(limit: int = 50):
    """Recupere le journal d'audit famille"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Redis non disponible"})

    import json
    entries = []
    for entry_json in _redis_client.get_family_audit(TENANT_ID, limit=limit):
        try:
            entry_data = json.loads(entry_json)
            audit = FamilyAuditLog.from_redis(entry_data)
            entries.append({
                "id": audit.id,
                "actor_name": audit.actor_name,
                "action": audit.action,
                "target_name": audit.target_name,
                "details": audit.details,
                "severity": audit.severity,
                "timestamp": audit.timestamp.isoformat(),
            })
        except:
            pass

    return {"entries": entries, "count": len(entries)}


# --- Default Escalation Rule for Teens (Bullying/Distress) ---

@app.post("/api/family/setup-teen-protection")
async def setup_teen_protection():
    """Configure automatiquement la protection ados (harcelement, detresse)"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Redis non disponible"})

    # Creer un groupe famille si pas existant
    if not _redis_client.get_family_group(TENANT_ID):
        group = FamilyGroup(tenant_id=TENANT_ID, name="Ma famille")
        _redis_client.set_family_group(TENANT_ID, group.to_redis())

    # Creer la regle d'escalade pour ados
    stages = [
        EscalationStage(
            order=1,
            delay_minutes=0,
            target_roles=[FamilyRole.TEEN],  # D'abord dialogue avec l'ado
            message_template="Luna a remarque que tu sembles preoccupe(e). Tu veux en parler?",
            include_emergency_numbers=False,
        ),
        EscalationStage(
            order=2,
            delay_minutes=5,
            target_roles=[FamilyRole.PRIMARY_CAREGIVER],
            message_template="[Luna Family] Votre enfant {name} a exprime des signes de detresse. Details: {summary}. Nous vous conseillons d'en discuter avec lui/elle.",
            include_emergency_numbers=False,
        ),
        EscalationStage(
            order=3,
            delay_minutes=15,
            target_roles=[FamilyRole.PRIMARY_CAREGIVER, FamilyRole.SECONDARY_CAREGIVER],
            message_template="[URGENT Luna Family] {name} necessite une attention immediate. Si vous ne pouvez pas le/la joindre, appelez le 3114 (prevention suicide) ou le 0 800 235 236 (Fil Sante Jeunes).",
            include_emergency_numbers=True,
        ),
    ]

    rule = EscalationRule(
        tenant_id=TENANT_ID,
        name="Protection ados - harcelement/detresse",
        description="Detection automatique du harcelement et de la detresse chez les adolescents",
        trigger_distress_level=DistressLevel.MEDIUM,
        trigger_member_types=[FamilyMemberType.TEEN, FamilyMemberType.CHILD],
        stages=stages,
        enabled=True,
    )

    _redis_client.add_escalation_rule(TENANT_ID, rule.id, rule.to_redis())

    _log_family_audit("teen_protection_enabled", "system", "Luna",
                      details={"rule_id": rule.id})

    return {
        "success": True,
        "rule_id": rule.id,
        "message": "Protection ados configuree avec succes. Luna va maintenant detecter les signes de harcelement et de detresse.",
    }


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
# EVENT LOG ENDPOINTS
# =========================================================================

@app.get("/api/events")
async def get_events(limit: int = 50, offset: int = 0):
    """Retourne le journal d'evenements chronologique."""
    if not _memory_manager:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    try:
        events = _memory_manager.get_event_log(limit=min(limit, 200), offset=offset)
        return {"events": events, "count": len(events)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/events/export")
async def export_events(limit: int = 200):
    """Exporte le journal d'evenements en texte brut."""
    if not _memory_manager:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    try:
        events = _memory_manager.get_event_log(limit=min(limit, 500))
        lines = []
        for ev in events:
            ts = ev.get("timestamp", "?")
            cat = ev.get("category", "?")
            desc = ev.get("description", "")
            reasoning = ev.get("reasoning", "")
            line = f"[{ts}] [{cat.upper()}] {desc}"
            if reasoning:
                line += f" | Raison: {reasoning}"
            lines.append(line)
        return Response(content="\n".join(lines), media_type="text/plain; charset=utf-8")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


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

    success, details = sms_client.send(phone, f"[Luna pour {_SUBSCRIBER_NAME}] {message}")
    reasoning = f"Luna envoie un SMS a {matched_name} car le souscripteur l'a demande pendant la visio"
    if success:
        if _memory_manager:
            try:
                _memory_manager.add_note(
                    content=f"[Action SMS] {reasoning} | Contenu: {message[:100]}",
                    context="visio_tool_call",
                    tags=["sms", "visio", matched_name, "reasoning"],
                )
            except Exception:
                pass
        # Log event
        try:
            _memory_manager.log_event(
                category="action",
                description=f"SMS envoye a {matched_name}: {message[:60]}",
                reasoning=reasoning,
                source="tool_call",
            )
        except Exception:
            pass
        return {"status": "success", "message": f"SMS envoye a {matched_name}", "reasoning": reasoning}
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

    reasoning = f"Luna prend une note a la demande du souscripteur pendant la visio"
    note = _memory_manager.add_note(
        content=f"{content}\n[Raison: {reasoning}]",
        context="visio_tool_call",
        tags=["visio", "note", "reasoning"],
    )
    return {"status": "success", "message": f"Note enregistree: {content[:50]}", "reasoning": reasoning}


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

    reasoning = f"Luna alerte les contacts car: {reason}"
    if _memory_manager:
        try:
            _memory_manager.add_note(
                content=f"[Action ALERTE] {reasoning} | {sent} contact(s) alertes",
                context="alerte_urgence",
                tags=["urgence", "alerte", "reasoning"],
            )
        except Exception:
            pass

    # Log event
    if _memory_manager:
        try:
            _memory_manager.log_event(
                category="safety",
                description=f"ALERTE envoyee a {sent} contact(s): {reason}",
                reasoning=reasoning,
                source="tool_call",
            )
        except Exception:
            pass
    return {"status": "success", "message": f"Alerte envoyee a {sent} contact(s) de confiance", "reasoning": reasoning}


async def _tool_report_observation(args: Dict) -> Dict:
    """Log une observation visuelle de Tavus Raven pendant un appel video."""
    if not _memory_manager:
        return {"status": "error", "message": "Memoire non disponible"}

    observation = args.get("observation", "")
    severity = args.get("severity", "info")

    reasoning = f"Luna note une observation visuelle Raven pendant la visio: {severity}"
    if observation:
        _memory_manager.add_note(
            content=f"[Observation visio] {observation}\n[Raison: {reasoning}]",
            context="visio_perception",
            tags=["perception", "visio", "raven", severity, "reasoning"],
        )
        _memory_manager.log_perception_event({
            "type": "visio_observation",
            "severity": severity,
            "description": observation,
            "reasoning": reasoning,
            "source": "tavus_raven",
            "timestamp": datetime.utcnow().isoformat(),
        })

    return {"status": "success", "message": "Observation notee", "reasoning": reasoning}


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
                    reasoning = f"Detection automatique par la perception camera: {abn['type']}"
                    try:
                        _memory_manager.add_note(
                            content=f"[Perception] {abn['description']}\n[Raison: {reasoning}]",
                            context="perception",
                            tags=["perception", abn["type"], abn["severity"], "reasoning"],
                        )
                        _memory_manager.log_event(
                            category="perception",
                            description=abn["description"],
                            reasoning=reasoning,
                            source="perception_loop",
                            details={"severity": abn["severity"], "type": abn["type"]},
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

                    # Enregistre le compte-rendu comme note + event log
                    if _memory_manager:
                        try:
                            _memory_manager.add_note(
                                content=f"[Auto] {result.message}",
                                context="instruction_execution",
                                tags=["auto", result.status.value, task.instruction.action_type.value],
                            )
                            _memory_manager.log_event(
                                category="instruction",
                                description=f"Instruction executee: {result.message}",
                                reasoning=f"Declenchee par le scheduler ({task.instruction.original_text[:60]})",
                                source="instruction_loop",
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

# =========================================================================
# TEST / SIMULATOR ENDPOINTS
# =========================================================================

@app.get("/api/test/scenarios")
async def list_scenarios():
    """Liste les scenarios de test disponibles."""
    try:
        from core.testing.simulator import ALL_SCENARIOS
        return {
            "scenarios": [
                {"name": s.name, "description": s.description, "steps": len(s.steps)}
                for s in ALL_SCENARIOS.values()
            ]
        }
    except ImportError:
        return JSONResponse(status_code=503, content={"error": "Module testing non disponible"})


@app.post("/api/test/scenario")
async def run_scenario(req: Request):
    """Execute un scenario de test. Protege par cle admin."""
    body = await req.json()
    scenario_name = body.get("scenario", "")
    admin_key = body.get("admin_key", "")

    # Protection par cle admin (utilise ADMIN_NUMBER comme cle simple)
    if admin_key != ADMIN_NUMBER:
        return JSONResponse(status_code=403, content={"error": "Cle admin requise"})

    try:
        from core.testing.simulator import ScenarioSimulator, ALL_SCENARIOS

        if scenario_name not in ALL_SCENARIOS:
            return JSONResponse(
                status_code=400,
                content={"error": f"Scenario inconnu: {scenario_name}", "available": list(ALL_SCENARIOS.keys())}
            )

        global _test_mode
        _test_mode = True

        async def test_chat_fn(message: str) -> str:
            """Appelle le chat en mode test."""
            try:
                test_session = f"test_{datetime.now().strftime('%H%M%S')}"
                if test_session not in conversations:
                    conversations[test_session] = [
                        {"role": "system", "content": LUNA_SYSTEM_PROMPT}
                    ]
                messages = conversations[test_session]
                messages.append({"role": "user", "content": message})
                response = openai_client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=messages,
                    max_tokens=500,
                    temperature=0.8,
                    timeout=30,
                )
                luna_msg = response.choices[0].message.content
                messages.append({"role": "assistant", "content": luna_msg})
                return luna_msg
            except Exception as e:
                return f"[ERREUR TEST] {e}"

        simulator = ScenarioSimulator(chat_fn=test_chat_fn)
        scenario = ALL_SCENARIOS[scenario_name]
        result = await simulator.run_scenario(scenario)

        _test_mode = False

        return result.to_dict()

    except ImportError:
        return JSONResponse(status_code=503, content={"error": "Module testing non disponible"})
    except Exception as e:
        _test_mode = False
        return JSONResponse(status_code=500, content={"error": str(e)})


if __name__ == "__main__":
    import uvicorn

    ssl_dir = os.path.dirname(__file__)
    logger.info(f"Demarrage Luna Web - YAWatch-Luna (Souscripteur: {_SUBSCRIBER_NAME})")
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
