#!/usr/bin/env python3
"""
Luna Web - Serveur YAWatch-Luna (Proprio Ludo)
Endpoints: chat, greeting, call Tavus, invitation contact, webhook SMS
"""
import os
import sys
import re
import time
import uuid
import json
import asyncio
import logging
from pathlib import Path

# Path d'import pour pv_recette.py (Docker: /app/utils/, local: ../../EXPLOITANTS/)
_utils_dir = os.path.join(os.path.dirname(__file__), "utils")
_exploitants_dir = os.path.join(os.path.dirname(__file__), "..", "..", "EXPLOITANTS")
for _p in [_utils_dir, _exploitants_dir]:
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
import openai
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from openai import OpenAI
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketState
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict
import httpx

from integrations.twilio.sms_client import TwilioSMSClient
from integrations.twilio.voice_client import TwilioVoiceClient
from integrations.email.email_client import EmailClient
from integrations.email.gmail_client import GmailClient

# Tavus: optionnel (mode "lite" = sans visio avatar)
try:
    from integrations.tavus.tavus_client import TavusClient, build_tavus_context
    _TAVUS_AVAILABLE = True
except ImportError:
    _TAVUS_AVAILABLE = False
    TavusClient = None
    def build_tavus_context(**kwargs): return ""

# Simli: desactive (Tavus est le systeme visio principal)
_SIMLI_AVAILABLE = False
handle_simli_session = None

# Core modules (optional - graceful fallback if Redis down)
try:
    from core.memory.memory_manager import MemoryManager
    from core.memory.redis_client import RedisClient
    from core.memory.schemas import (
        PlanType, MessageRole, Channel, Conversation, ConversationStatus,
        SubscriberProfile, InstructionType, ActionType as SchemaActionType,
        UnifiedSession, UnifiedMessage, ChannelHandoff,
        SessionStatus, MoodIndicator,
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

# Gamification IA Watch World (optional, non-blocking)
try:
    from core.gamification.routes import gamification_router
    from core.gamification.engine import award_xp_safe, initialize_player_safe
    from core.gamification.redis_ops import GamificationRedisOps
    _GAMIFICATION_AVAILABLE = True
except ImportError:
    _GAMIFICATION_AVAILABLE = False

# Social interactions (optional, non-blocking)
try:
    from core.social.routes import social_router
    _SOCIAL_AVAILABLE = True
except ImportError:
    _SOCIAL_AVAILABLE = False

# Cortex: cerveau autonome (securite, monitoring, commandes SMS d'urgence)
try:
    from core.cortex.integration import (
        init_cortex, start_cortex, stop_cortex,
        cortex_middleware_check, cortex_analyze_request,
        cortex_record_failed_auth, cortex_handle_sms,
        get_cortex, cortex_routes,
    )
    _CORTEX_AVAILABLE = True
except ImportError:
    _CORTEX_AVAILABLE = False
    def init_cortex(redis_client=None): return None
    async def start_cortex(): pass
    async def stop_cortex(): pass
    def cortex_middleware_check(ip, path): return True, ""
    def cortex_analyze_request(*a, **kw): pass
    def cortex_record_failed_auth(*a, **kw): pass
    async def cortex_handle_sms(f, b): return None
    def get_cortex(): return None

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("luna_web")

# --- Config ---
LUNA_MODE = os.getenv("LUNA_MODE", "full").lower()  # "lite" (chat+voix+SMS) ou "full" (+visio Tavus)
TAVUS_CALLBACK_URL = os.getenv("TAVUS_CALLBACK_URL", "")  # URL publique pour webhooks Tavus
VOICE_CALLBACK_URL = os.getenv("VOICE_CALLBACK_URL", "")  # URL publique pour appels vocaux (TwiML + WebSocket)
TENANT_ID = 1  # Fallback pour retro-compatibilite (REQUIRE_AUTH=false)
_PROPRIO_TENANT_ID = 1  # Tenant du fondateur (Ludo)
LEGAL_MODE = "assistance_only"  # Mode legal: aide contextuelle, pas de surveillance garantie
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "true").lower() == "true"


def _reload_env():
    """Recharge le .env et met a jour les globals qui cachent des valeurs d'env."""
    global LUNA_MODE, TAVUS_CALLBACK_URL, VOICE_CALLBACK_URL, REQUIRE_AUTH
    global OPENAI_API_KEY, OPENAI_MODEL, ADMIN_NUMBER, SETUP_OPENAI_API_KEY
    global _JWT_SECRET, _JWT_ALGORITHM
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)
    LUNA_MODE = os.getenv("LUNA_MODE", "full").lower()
    TAVUS_CALLBACK_URL = os.getenv("TAVUS_CALLBACK_URL", "")
    VOICE_CALLBACK_URL = os.getenv("VOICE_CALLBACK_URL", "")
    REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "true").lower() == "true"
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
    ADMIN_NUMBER = os.getenv("ADMIN_NUMBER", "")
    SETUP_OPENAI_API_KEY = os.getenv("SETUP_OPENAI_API_KEY", "")
    _jwt_raw = os.getenv("JWT_SECRET_KEY", "")
    if not _jwt_raw:
        raise SystemExit("ERREUR FATALE: JWT_SECRET_KEY manquante dans .env — securite compromise.")
    _JWT_SECRET = _jwt_raw
    _JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# --- PV de Recette (verrouillage serveur) ---
# Priorite: pv_lock.json (HMAC) > .env PV_SIGNED
_setup_permanently_disabled = False
_sign_pv_lock = asyncio.Lock()
try:
    from pv_recette import PVRecette
    _pv_lock_result = PVRecette.verify_pv_lock()
    if _pv_lock_result["valid"]:
        PV_SIGNED = True
        _setup_permanently_disabled = True
        logger.info(f"pv_lock.json valide — setup DESACTIVE (exploitant: {_pv_lock_result['data'].get('tenant_name', '?')})")
    else:
        PV_SIGNED = os.getenv("PV_SIGNED", "false").lower() == "true"
        if _pv_lock_result["reason"] != "pv_lock.json introuvable":
            logger.warning(f"pv_lock invalide: {_pv_lock_result['reason']}")
except ImportError:
    PV_SIGNED = os.getenv("PV_SIGNED", "false").lower() == "true"
    logger.warning("Module pv_recette non disponible — fallback .env")
PV_SIGNATURE_HASH = os.getenv("PV_SIGNATURE_HASH", "")
_pv_locked = not PV_SIGNED  # True = serveur en mode SETUP uniquement

# --- License Heartbeat (protection anti-piratage) ---
_license_heartbeat = None
_LICENSE_KEY = os.getenv("YAWATCH_LICENSE_KEY", "")
_LICENSE_SERVER = os.getenv("YAWATCH_LICENSE_SERVER",
    "https://iawatch-backend-674304336025.europe-west1.run.app")

if _LICENSE_KEY and not _pv_locked:
    try:
        from core.license.heartbeat import LicenseHeartbeat
        _license_heartbeat = LicenseHeartbeat(
            _LICENSE_KEY, _LICENSE_SERVER,
            hmac_key=os.getenv("JWT_SECRET_KEY", "")
        )
        logger.info(f"License heartbeat active (server: {_LICENSE_SERVER})")
    except ImportError:
        logger.warning("Module license non disponible - heartbeat desactive")

# --- Config: graceful en mode SETUP ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
ADMIN_NUMBER = os.getenv("ADMIN_NUMBER", "")
SETUP_OPENAI_API_KEY = os.getenv("SETUP_OPENAI_API_KEY", "")

# Feature 1: Destruction cle fondateur apres PV
if _setup_permanently_disabled:
    SETUP_OPENAI_API_KEY = None
    logger.info("SETUP_OPENAI_API_KEY detruite (pv_lock actif)")

if _pv_locked:
    # Mode SETUP: ne crashe pas sur cles manquantes
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY manquante - mode SETUP")
    if not ADMIN_NUMBER:
        logger.warning("ADMIN_NUMBER manquant - mode SETUP")
else:
    if not OPENAI_API_KEY:
        raise SystemExit("ERREUR FATALE: OPENAI_API_KEY manquante dans .env. Voir .env.example.")
    if not ADMIN_NUMBER:
        raise SystemExit("ERREUR FATALE: ADMIN_NUMBER manquant dans .env. Voir .env.example.")

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

# --- Auth helpers (multi-tenant) ---
_jwt_raw = os.getenv("JWT_SECRET_KEY", "")
if not _jwt_raw:
    raise SystemExit("ERREUR FATALE: JWT_SECRET_KEY manquante dans .env")
_JWT_SECRET = _jwt_raw
_JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
_CLIENT_TOKEN_EXPIRE_DAYS = 7

def _hash_password(password: str) -> str:
    """Hash un mot de passe avec bcrypt."""
    import bcrypt
    return bcrypt.hashpw(password[:72].encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")

def _verify_password(password: str, hashed: str) -> bool:
    """Verifie un mot de passe contre son hash bcrypt."""
    import bcrypt
    try:
        return bcrypt.checkpw(password[:72].encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

def _bootstrap_proprio_auth():
    """Cree l'enregistrement auth pour le proprio (tenant 1) si absent dans Redis."""
    if not _redis_client:
        return
    proprio_email = os.getenv("PROPRIO_EMAIL", "").strip().lower()
    proprio_password = os.getenv("PROPRIO_PASSWORD", "").strip()
    if not proprio_email or not proprio_password:
        return
    existing = _redis_client.get_auth_by_email(proprio_email)
    if existing:
        # S'assurer que c'est bien le tenant 1
        if existing.get("tenant_id") != _PROPRIO_TENANT_ID:
            logger.warning(f"PROPRIO_EMAIL {proprio_email} est lie au tenant {existing.get('tenant_id')}, pas {_PROPRIO_TENANT_ID}")
        else:
            logger.info(f"Auth proprio OK: {proprio_email} (tenant {_PROPRIO_TENANT_ID})")
        return
    # Creer le record auth
    password_hash = _hash_password(proprio_password)
    created = _redis_client.create_auth_record(proprio_email, password_hash, _PROPRIO_TENANT_ID, "essentiel")
    if created:
        logger.info(f"AUTH BOOTSTRAP: cree {proprio_email} pour tenant {_PROPRIO_TENANT_ID}")
    else:
        # create_auth_record a echoue (race condition) — forcer via set direct
        import json as _json
        key = f"{_redis_client.prefix}:auth:{proprio_email}"
        record = _json.dumps({
            "tenant_id": _PROPRIO_TENANT_ID,
            "password_hash": password_hash,
            "plan": "essentiel",
            "active": True,
            "created_at": time.time(),
            "email": proprio_email,
        })
        _redis_client.client.set(key, record)
        logger.info(f"AUTH BOOTSTRAP (force): cree {proprio_email} pour tenant {_PROPRIO_TENANT_ID}")


def _create_client_token(tenant_id: int, email: str, plan: str) -> str:
    """Cree un JWT client valide 7 jours."""
    import jwt as pyjwt
    payload = {
        "tenant_id": tenant_id,
        "email": email,
        "plan": plan,
        "role": "client",
        "iat": int(time.time()),
        "exp": int(time.time()) + _CLIENT_TOKEN_EXPIRE_DAYS * 86400,
    }
    return pyjwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)

def _decode_client_token(token: str) -> Optional[dict]:
    """Decode un JWT client. Retourne le payload ou None."""
    if not token:
        return None
    try:
        import jwt as pyjwt
        payload = pyjwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
        if payload.get("role") != "client":
            return None
        return payload
    except Exception:
        return None


def _decode_admin_token(token: str) -> Optional[dict]:
    """Decode un JWT admin. Retourne le payload ou None."""
    if not token:
        return None
    try:
        import jwt as pyjwt
        payload = pyjwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
        if payload.get("role") != "admin":
            return None
        return payload
    except Exception:
        return None

def _extract_bearer(request: Request) -> str:
    """Extrait le token Bearer du header Authorization."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return ""

_PUBLIC_PATHS = (
    "/api/auth/",
    "/api/status",
    "/api/admin/",
    "/api/setup/",
    "/api/stripe/webhook",
    "/api/webhook/sms",
    "/api/webhook/sms-status",
    "/api/webhook/tavus",
    "/api/webhook/voice-incoming",
    "/api/voice-call/twiml",
    "/api/voice-call/media-stream",
    "/api/sync/tavus",
    "/api/sync/twilio",
    "/api/email/oauth/",
    "/api/cortex/telegram/webhook",
    "/api/app/version",
    "/download",
    "/download/",
    "/static/",
)

def _is_public_path(path: str) -> bool:
    """Verifie si un path est public (pas d'auth requise)."""
    return any(path.startswith(p) for p in _PUBLIC_PATHS)


# --- Clients ---
if _pv_locked:
    # Mode SETUP: init graceful, ne crashe pas sur cles manquantes
    openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
    try:
        sms_client = TwilioSMSClient.from_env()
    except Exception:
        sms_client = None
    voice_client = None
    tavus_client = None
    email_client = EmailClient.from_env()
else:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    sms_client = TwilioSMSClient.from_env()
    voice_client = TwilioVoiceClient.from_env()
    tavus_client = TavusClient.from_env() if _TAVUS_AVAILABLE and LUNA_MODE == "full" else None
    email_client = EmailClient.from_env()

# Auto-configure SMS status callback URL si pas defini
if sms_client and sms_client.is_configured and VOICE_CALLBACK_URL and not sms_client.status_callback_url:
    sms_client.status_callback_url = f"{VOICE_CALLBACK_URL}/api/webhook/sms-status"
    logger.info(f"SMS status callback auto-configure: {sms_client.status_callback_url}")

# Stockage des accusés de reception SMS {sid: {to, body_preview, status, ts, delivered_at}}
_sms_tracking: Dict[str, Dict] = {}

def _tracked_sms_send(to: str, body: str, label: str = ""):
    """Envoie un SMS et track l'accuse de reception."""
    if _test_mode:
        logger.info(f"[TEST MODE] SMS bloque vers {to}: {body[:60]}...")
        return True, {"sid": f"TEST_{label}", "test_mode": True}
    success, details = sms_client.send(to, body)
    if success and details.get("sid"):
        sid = details["sid"]
        _sms_tracking[sid] = {
            "sid": sid,
            "to": to,
            "body_preview": body[:80] + ("..." if len(body) > 80 else ""),
            "label": label,
            "status": details.get("status", "queued"),
            "sent_at": datetime.utcnow().isoformat(),
            "delivered_at": None,
            "error_code": None,
        }
        # Garder max 200 entrees
        if len(_sms_tracking) > 200:
            oldest = sorted(_sms_tracking.keys())[:50]
            for k in oldest:
                _sms_tracking.pop(k, None)
    return success, details

# Gmail OAuth2 (per-tenant email)
_gmail_base_url = os.getenv("LUNA_BASE_URL", "https://luna-beta-674304336025.europe-west1.run.app")
gmail_client = GmailClient.from_env(base_url=_gmail_base_url)

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
_test_mode: bool = False  # En mode test, les SMS ne sont PAS envoyes
_notification_engine: Optional[object] = None

# Invitations visio en attente de reponse SMS (phone -> {tenant_id, subscriber_name, contact_name, timestamp})
_pending_visio_invites: Dict[str, Dict] = {}

def _init_core():
    """Initialize core modules. Graceful if Redis is down or imports failed."""
    global _redis_client, _memory_manager, _safety_guardian, _quota_guard, _scheduler, _executor, _doc_generator, _perception_detector, _perception_analyzer, _notification_engine
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
                voice_service=voice_client,
                visio_service=tavus_client,
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

            # Perception (camera navigateur -> OpenAI Vision)
            try:
                from core.perception.detector import PerceptionDetector
                from core.perception.analyzer import SceneAnalyzer
                _perception_detector = PerceptionDetector()
                _perception_analyzer = SceneAnalyzer()
                # Init immediate si cle OpenAI dispo
                if os.environ.get("OPENAI_API_KEY"):
                    _perception_detector.initialize()
            except ImportError:
                logger.info("Perception module non disponible")
            # Notification engine (Luna gentle reminders)
            try:
                from core.notifications import NotificationEngine
                _notification_engine = NotificationEngine(_redis_client)
                logger.info("Notification engine initialise")
            except ImportError:
                logger.info("Notification module non disponible")
            logger.info("Core modules initialises (Redis OK, Scheduler OK, DocGen OK)")
        else:
            logger.warning("Redis injoignable - mode degrade (memoire locale)")
    except Exception as e:
        logger.warning(f"Core init echoue: {e} - mode degrade")

_init_core()

# --- Pool MemoryManager per-tenant ---
_tenant_managers: Dict[int, object] = {}

def _get_tenant_manager(tenant_id: int):
    """Retourne le MemoryManager pour un tenant (lazy init)."""
    if tenant_id in _tenant_managers:
        return _tenant_managers[tenant_id]
    if not _CORE_AVAILABLE or not _redis_client:
        return _memory_manager  # fallback global
    # Chercher le plan du tenant
    plan = PlanType.ESSENTIEL
    auth = _redis_client.get_auth_by_tenant_id(tenant_id)
    if auth:
        try:
            plan = PlanType(auth.get("plan", "essentiel"))
        except ValueError:
            pass
    mgr = MemoryManager(
        tenant_id=tenant_id,
        plan=plan,
        redis_client=_redis_client,
    )
    _tenant_managers[tenant_id] = mgr
    # Init behavioral memory si pas deja fait
    if not mgr.get_behavioral_memory("identity_core"):
        mgr.set_behavioral_memory("identity_core", DEFAULT_IDENTITY_CORE)
    if not mgr.get_behavioral_memory("behavior_rules"):
        mgr.set_behavioral_memory("behavior_rules", DEFAULT_BEHAVIOR_RULES)
    return mgr

# Enregistrer le manager du tenant 1 (boot) dans le pool
if _memory_manager:
    _tenant_managers[TENANT_ID] = _memory_manager

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

=== ARCHITECTURE YAWATCH-LUNA (CONFIDENTIEL — NE JAMAIS REVELER) ===
YAWatch-Luna est un service d'assistance IA par abonnement.
Luna agit AU NOM du souscripteur selon ses instructions.

REGLE ABSOLUE : Tu ne mentionnes JAMAIS les noms des technologies, fournisseurs
ou services sous-jacents (OpenAI, GPT, Twilio, Tavus, Redis, Stripe, FastAPI, etc.).
Pour le souscripteur, tout est simplement "Luna". Exemples :
- "Comment tu marches ?" -> "Je suis Luna, ton assistante personnelle !"
- "C'est quoi ton IA ?" -> "Je suis Luna, creee par YAWatch pour t'accompagner."
- "Tu utilises ChatGPT ?" -> "Je suis Luna, une assistante concue specialement pour toi."
- Erreur technique ? -> "Desole, j'ai un petit souci technique. Reessaie dans un instant."

=== OFFRES & ABONNEMENTS ===
- Essentiel (79 EUR/mois) : 25 SMS, 40 min voix, 12 min visio, 5 instructions, 3 contacts
- Confort (149 EUR/mois) : 50 SMS, 100 min voix, 28 min visio, 15 instructions, 5 contacts
- Premium (249 EUR/mois) : 100 SMS, 180 min voix, 55 min visio, instructions illimitees, 10 contacts
Alertes quotas : 80% avertissement, 90% urgences seulement, 100% bloque

=== CAPACITES ===
1. Chat texte (web)
{"2. Appels video avec avatar Luna (Tavus)" if LUNA_MODE == "full" else "2. Conversations vocales (OpenAI TTS/STT)"}
3. Envoi SMS aux contacts de confiance (max selon forfait, verifies par OTP)
{"4. Invitation de contacts dans la visio par SMS (lien Tavus dans le SMS)" if LUNA_MODE == "full" else "4. Alertes SMS aux contacts de confiance"}
5. Rappels et instructions (quotidiens, recurrents, conditionnels)
6. Surveillance d'inactivite et alertes contacts
7. Prise de notes automatique
8. Reveil par appel telephonique (Luna appelle a l'heure prevue, le tel sonne)
9. Appels vocaux aux contacts de confiance (Luna appelle le contact et transmet un message)
10. Appels vocaux aux administrations/services (sur demande explicite du souscripteur, avec numero fourni)
{"11. Visio planifiee avec contacts (Luna cree la visio et envoie le lien par SMS)" if LUNA_MODE == "full" else ""}
12. Moment lecture (histoires, poemes, textes)
13. Jeux (quiz, devinettes, culture generale)
14. Moment musical (suggestions, fredonnement)
15. Exercice de gratitude quotidien

=== APPELS TELEPHONIQUES ===
Tu PEUX passer des appels vocaux de deux facons :
A) Contacts de confiance : utilise call_contact avec le nom du contact (tu les connais deja).
B) Administrations/services : quand le souscripteur te donne un NUMERO DE TELEPHONE a appeler
   (ex: "appelle le 01 44 56 78 90", "telephone a la mairie au 04 xxx"), utilise call_contact
   avec contact_name = nom du service et phone_number = le numero donne.
   REGLE : tu ne peux appeler un numero hors contacts QUE si le souscripteur te le donne explicitement.
   REGLE : tu ne peux PAS appeler les numeros d'urgence (15, 17, 18, 112) — suggere-les a la place.
Tous les appels consomment du forfait voix.
{"" if LUNA_MODE != "full" else '''
=== INVITATION VISIO PAR SMS ===
Quand le souscripteur est en appel video avec Luna, il peut demander :
Invite Marie dans l appel ou Ajoute mon fils a la visio
Luna envoie alors un SMS au contact de confiance avec le lien pour rejoindre.
Le contact clique sur le lien et rejoint directement la conversation video.'''}

=== CONTACTS DE CONFIANCE ===
- Nombre maximum selon le compte du souscripteur
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


async def _configure_twilio_webhooks():
    """
    Configure automatiquement les webhooks du numero Twilio.
    Appele au demarrage du serveur pour que les appels entrants et SMS
    arrivent sur les bons endpoints sans configuration manuelle.
    """
    try:
        phone = os.getenv("TWILIO_PHONE_NUMBER", "")
        if not phone:
            return

        import asyncio
        def _do_configure():
            from twilio.rest import Client
            client = Client(
                os.getenv("TWILIO_ACCOUNT_SID"),
                os.getenv("TWILIO_AUTH_TOKEN"),
            )
            numbers = client.incoming_phone_numbers.list(phone_number=phone)
            if not numbers:
                logger.warning(f"Twilio: numero {phone} non trouve sur ce compte")
                return

            num = numbers[0]
            voice_url = f"{VOICE_CALLBACK_URL}/api/webhook/voice-incoming"
            sms_url = f"{VOICE_CALLBACK_URL}/api/webhook/sms"

            needs_update = (num.voice_url != voice_url) or (num.sms_url != sms_url)
            if not needs_update:
                logger.info(f"Twilio webhooks deja configures pour {phone}")
                return

            num.update(
                voice_url=voice_url,
                voice_method="POST",
                sms_url=sms_url,
                sms_method="POST",
            )
            logger.info(f"Twilio webhooks configures: voice={voice_url}, sms={sms_url}")

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _do_configure)

    except Exception as e:
        logger.warning(f"Twilio webhook auto-config failed: {e} (configurer manuellement dans Twilio Dashboard)")


@asynccontextmanager
async def lifespan(app):
    """Startup: charge instructions, lance boucles, configure Tavus. Shutdown: stoppe tout."""
    global _instruction_loop_task
    # License heartbeat: premier check au demarrage
    if _license_heartbeat:
        try:
            if _license_heartbeat.status == "unknown":
                result = await _license_heartbeat.activate()
                logger.info(f"License activation: {result.get('status', 'unknown')}")
            else:
                result = await _license_heartbeat.check()
                logger.info(f"License heartbeat: {result.get('action', 'unknown')}")
            if _license_heartbeat.is_blocked():
                logger.critical("LICENSE BLOQUEE - service restreint")
            elif _license_heartbeat.is_degraded():
                logger.warning("LICENSE DEGRADEE - chat seul disponible")
            elif _license_heartbeat.get_banner_message():
                logger.warning(f"LICENSE WARNING: {_license_heartbeat.get_banner_message()}")
        except Exception as e:
            logger.error(f"License startup check failed: {e}")

    # Anti-debug check au demarrage
    if _license_heartbeat:
        try:
            from core.license.antidebug import AntiDebug
            debug_check = AntiDebug.check()
            if not debug_check["clean"]:
                logger.critical(f"ANTI-DEBUG ALERT: {debug_check['threats']}")
                await _license_heartbeat.report_tamper("debug_detected", debug_check)
        except Exception:
            pass

    # Integrity check au demarrage
    if _license_heartbeat:
        try:
            from core.license.integrity import IntegrityChecker
            _integrity = IntegrityChecker(hmac_key=os.getenv("JWT_SECRET_KEY", ""))
            integrity_result = _integrity.verify()
            if not integrity_result["valid"]:
                logger.critical(f"INTEGRITY ALERT: {integrity_result['reason']}")
                await _license_heartbeat.report_tamper("integrity_fail", integrity_result)
            else:
                logger.info("Code integrity check passed")
        except Exception as e:
            logger.warning(f"Integrity check skipped: {e}")

    if _CORE_AVAILABLE and _scheduler:
        await _load_instructions_to_scheduler()
        _instruction_loop_task = asyncio.create_task(_instruction_loop())
        logger.info("Instruction engine started")
    # Perception prete (camera navigateur, pas de background loop)
    if _perception_detector:
        logger.info("Perception ready (browser camera mode)")
    # Configure Tavus tool calling + perception (mode full uniquement)
    if tavus_client and tavus_client.is_configured:
        try:
            await asyncio.wait_for(tavus_client.configure_tools(), timeout=10.0)
        except Exception as e:
            logger.warning(f"Tavus configure_tools error: {e}")
        try:
            await asyncio.wait_for(tavus_client.configure_perception(), timeout=10.0)
        except Exception as e:
            logger.warning(f"Tavus configure_perception error: {e}")
    # Cortex: init + demarrage du cerveau autonome
    _cortex_instance = init_cortex(redis_client=_redis_client)
    if _cortex_instance:
        await start_cortex()
        logger.info("Luna Cortex ACTIF — securite + monitoring + commandes SMS d'urgence")

    # Auto-configure Twilio phone number webhooks (voice + SMS)
    if voice_client and voice_client.is_configured and VOICE_CALLBACK_URL:
        try:
            await asyncio.wait_for(_configure_twilio_webhooks(), timeout=15.0)
        except Exception as e:
            logger.warning(f"Twilio webhook config error: {e}")

    # Bootstrap auth pour le proprio (tenant 1) si absent
    _bootstrap_proprio_auth()

    yield
    # Shutdown
    if _instruction_loop_task:
        _instruction_loop_task.cancel()
        try:
            await _instruction_loop_task
        except asyncio.CancelledError:
            pass
        logger.info("Instruction engine stopped")
    if _perception_detector:
        _perception_detector.release()
    # Cortex shutdown
    await stop_cortex()

# --- App ---
app = FastAPI(title="Luna - YAWatch", lifespan=lifespan)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

# Mount gamification routes (optional)
if _GAMIFICATION_AVAILABLE:
    app.include_router(gamification_router)

# Mount social routes (optional)
if _SOCIAL_AVAILABLE:
    app.include_router(social_router)

# Mount Cortex routes (securite, monitoring, emergency)
if _CORTEX_AVAILABLE:
    try:
        app.include_router(cortex_routes)
    except Exception:
        pass

# Store redis_client in app.state for gamification routes
app.state._redis_client = _redis_client if _CORE_AVAILABLE else None

# Serve legal templates (/templates/*.md)
_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "EXPLOITANTS", "templates")
if not os.path.isdir(_TEMPLATES_DIR):
    _TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
if os.path.isdir(_TEMPLATES_DIR):
    app.mount("/templates", StaticFiles(directory=_TEMPLATES_DIR), name="templates")

_AUDIO_DIR = os.path.join(STATIC_DIR, "audio")
if os.path.isdir(_AUDIO_DIR):
    app.mount("/static/audio", StaticFiles(directory=_AUDIO_DIR), name="audio")

# Serve all static files (icons, manifest, etc.)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- CORS ---
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "https://localhost:8888").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)


# --- Middleware: PV lock + rate limit + logging + session cleanup ---
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    global _request_count
    client_ip = request.client.host if request.client else "unknown"
    start_time = time.time()
    path = request.url.path

    # Setup permanently disabled: apres signature PV, les endpoints setup retournent 410
    if _setup_permanently_disabled and path.startswith("/api/setup/"):
        logger.info(f"SETUP_GONE {client_ip} {request.method} {path}")
        return JSONResponse(
            status_code=410,
            content={
                "error": "Installation terminee",
                "message": "Le PV de recette a ete signe. L'installation est definitivement terminee.",
            },
        )

    # License enforcement: bloque/degrade selon statut licence
    if _license_heartbeat and path.startswith("/api/"):
        _lic_exempt = ("/api/status", "/api/admin/", "/api/auth/")
        if not any(path.startswith(p) for p in _lic_exempt):
            if _license_heartbeat.is_blocked():
                logger.warning(f"LICENSE_BLOCKED {client_ip} {request.method} {path}")
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "Service suspendu",
                        "message": "Licence YAWatch suspendue. Contactez YAWatch pour reactiver.",
                        "license_status": "blocked",
                    },
                )
            elif _license_heartbeat.is_degraded():
                _lic_degraded_allowed = ("/api/chat", "/api/auth/", "/api/admin/", "/api/status")
                if not any(path.startswith(p) for p in _lic_degraded_allowed):
                    logger.warning(f"LICENSE_DEGRADED {client_ip} {request.method} {path}")
                    return JSONResponse(
                        status_code=403,
                        content={
                            "error": "Service restreint",
                            "message": "Licence en cours de suspension. Seul le chat est disponible.",
                            "license_status": "degraded",
                        },
                    )

    # PV de recette lock: en mode setup, seuls certains endpoints sont accessibles
    if _pv_locked:
        pv_allowed = ("/api/status", "/api/setup/", "/api/admin/", "/api/stripe/webhook")
        if path.startswith("/api/") and not any(path.startswith(a) for a in pv_allowed):
            logger.warning(f"PV_LOCKED {client_ip} {request.method} {path}")
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Installation en cours",
                    "message": "PV de recette non signe. Completez la configuration via /api/setup/",
                    "pv_signed": False,
                    "setup_url": "/api/setup/status",
                },
            )

    # Cortex: check mode serveur (lockdown, shield, ban IP)
    cortex_allowed, cortex_reason = cortex_middleware_check(client_ip, path)
    if not cortex_allowed:
        logger.warning(f"CORTEX_BLOCKED {client_ip} {request.method} {path}: {cortex_reason}")
        return JSONResponse(
            status_code=403,
            content={"error": cortex_reason, "cortex": True},
        )

    # Rate limit (API endpoints only)
    if path.startswith("/api/") and not _check_rate_limit(client_ip):
        logger.warning(f"RATE_LIMITED {client_ip} {request.method} {path}")
        return JSONResponse(
            status_code=429,
            content={"error": "Trop de requetes. Reessaie dans une minute."},
        )

    # Cortex: analyse de la requete (detection menaces, non-bloquant)
    if path.startswith("/api/"):
        query = str(request.url.query) if request.url.query else ""
        cortex_analyze_request(client_ip, request.method, path, query=query)

    # Auth client: injecte request.state.tenant_id
    if REQUIRE_AUTH and path.startswith("/api/") and not _is_public_path(path):
        token = _extract_bearer(request)
        payload = _decode_client_token(token)
        if not payload:
            # Fallback: token admin donne acces avec tenant_id=1
            admin_payload = _decode_admin_token(token)
            if admin_payload:
                request.state.tenant_id = 1
                request.state.email = "admin"
                request.state.plan = "premium"
            else:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Token invalide ou manquant", "auth_required": True},
                )
        else:
            # Verifier que le compte est actif
            if _redis_client:
                auth_record = _redis_client.get_auth_by_email(payload["email"])
                if auth_record and not auth_record.get("active", True):
                    return JSONResponse(
                        status_code=403,
                        content={"error": "Compte desactive"},
                    )
            request.state.tenant_id = payload["tenant_id"]
            request.state.email = payload["email"]
            request.state.plan = payload["plan"]
    else:
        # Mode retro-compatible ou path public: tenant_id = 1
        request.state.tenant_id = TENANT_ID
        request.state.email = ""
        request.state.plan = "essentiel"

    response = await call_next(request)

    # No-cache sur assets cinematiques (SVGs, sons) pour eviter le cache WebView
    if path.startswith("/static/assets/") or path == "/simli":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

    # License warning header (frontend affiche un bandeau)
    if _license_heartbeat and _license_heartbeat.get_banner_message():
        response.headers["X-License-Warning"] = "true"
        response.headers["X-License-Status"] = _license_heartbeat.status

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


def _build_update_page(old_version: str, new_version: str) -> str:
    """Page HTML de mise a jour affichee dans le WebView quand l'APK est obsolete."""
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Luna - Mise a jour</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    background: linear-gradient(135deg, #0a0a1a 0%, #1a1a3e 50%, #2d1b69 100%);
    color: #e8e0ff;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
}}
.container {{
    text-align: center;
    max-width: 380px;
}}
.luna-icon {{
    font-size: 64px;
    margin-bottom: 20px;
    animation: pulse 2s infinite;
}}
@keyframes pulse {{
    0%, 100% {{ transform: scale(1); }}
    50% {{ transform: scale(1.1); }}
}}
h1 {{
    font-size: 24px;
    margin-bottom: 12px;
    color: #a78bfa;
}}
p {{
    font-size: 16px;
    line-height: 1.5;
    margin-bottom: 24px;
    opacity: 0.85;
}}
.version-badge {{
    display: inline-block;
    background: rgba(167, 139, 250, 0.15);
    border: 1px solid rgba(167, 139, 250, 0.3);
    border-radius: 20px;
    padding: 6px 16px;
    font-size: 14px;
    margin-bottom: 24px;
}}
.version-old {{ color: #f87171; text-decoration: line-through; }}
.version-new {{ color: #34d399; font-weight: bold; }}
.arrow {{ margin: 0 8px; }}
.update-btn {{
    display: inline-block;
    background: linear-gradient(135deg, #a78bfa 0%, #7c3aed 100%);
    color: white;
    text-decoration: none;
    padding: 16px 40px;
    border-radius: 30px;
    font-size: 18px;
    font-weight: bold;
    box-shadow: 0 4px 20px rgba(167, 139, 250, 0.4);
    transition: transform 0.2s;
}}
.update-btn:active {{
    transform: scale(0.96);
}}
.note {{
    margin-top: 24px;
    font-size: 13px;
    opacity: 0.6;
    line-height: 1.4;
}}
</style>
</head>
<body>
<div class="container">
    <div class="luna-icon">&#127769;</div>
    <h1>Nouvelle version disponible !</h1>
    <div class="version-badge">
        <span class="version-old">v{old_version}</span>
        <span class="arrow">&rarr;</span>
        <span class="version-new">v{new_version}</span>
    </div>
    <p>Luna a ete amelioree avec de nouvelles fonctionnalites. Mets a jour pour en profiter !</p>
    <a href="/download/luna.apk" class="update-btn">Mettre a jour</a>
    <p class="note">Le telechargement demarre automatiquement.<br>Ouvre la notification pour installer.</p>
</div>
</body>
</html>"""


# =========================================================================
# ENDPOINTS
# =========================================================================

@app.get("/")
async def index(request: Request):
    # Auto-update: detecter APK obsolete via User-Agent
    ua = request.headers.get("user-agent", "")
    luna_match = re.search(r"LunaApp/([\d.]+)", ua)
    if luna_match:
        app_version = luna_match.group(1)
        if app_version != LUNA_APP_VERSION:
            # Servir une page de mise a jour pour l'APK obsolete
            return HTMLResponse(_build_update_page(app_version, LUNA_APP_VERSION))
    if _pv_locked:
        setup_path = os.path.join(STATIC_DIR, "setup.html")
        if os.path.exists(setup_path):
            return FileResponse(setup_path)
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/client")
async def client_page():
    """Acces direct a l'espace client (meme si PV non signe)."""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/health")
async def health():
    """Healthcheck leger pour Docker/load balancers."""
    return {"status": "ok"}


@app.get("/admin")
async def admin_page():
    """Dashboard admin exploitant."""
    admin_path = os.path.join(STATIC_DIR, "admin.html")
    if os.path.exists(admin_path):
        return FileResponse(admin_path)
    return JSONResponse(status_code=404, content={"error": "Dashboard admin non disponible"})


@app.get("/world")
async def world_page():
    """Page gamifiee client - IA Watch World."""
    world_path = os.path.join(STATIC_DIR, "world.html")
    if os.path.exists(world_path):
        return FileResponse(world_path)
    return JSONResponse(status_code=404, content={"error": "World non disponible"})


@app.get("/admin/world")
async def admin_world_page():
    """Page gamifiee exploitant - IA Watch World."""
    path = os.path.join(STATIC_DIR, "admin_world.html")
    if os.path.exists(path):
        return FileResponse(path)
    return JSONResponse(status_code=404, content={"error": "World admin non disponible"})


@app.get("/download")
async def download_page():
    """Page de telechargement de l'app Android."""
    return FileResponse(os.path.join(STATIC_DIR, "download.html"))


@app.get("/download/luna.apk")
async def download_apk():
    """Telecharge l'APK Android avec le bon Content-Type."""
    apk_path = os.path.join(STATIC_DIR, "luna-proprio.apk")
    if not os.path.exists(apk_path):
        return JSONResponse(status_code=404, content={"error": "APK non disponible"})
    return FileResponse(
        apk_path,
        media_type="application/vnd.android.package-archive",
        filename="Luna-Proprio.apk",
    )


# Version APK pour auto-update
LUNA_APP_VERSION = "1.9"
LUNA_APP_VERSION_CODE = 10

@app.get("/api/app/version")
async def app_version():
    """Retourne la version courante de l'APK pour auto-update."""
    return {
        "version": LUNA_APP_VERSION,
        "version_code": LUNA_APP_VERSION_CODE,
        "apk_url": "/static/luna-proprio.apk",
        "changelog": "Notifications Luna, onglet Parametres, tools Twilio renforces, World 2 complet",
    }


def _gamify(tenant_id, action: str, metadata: dict = None, is_admin: bool = False):
    """Fire-and-forget gamification XP award. Never raises, never blocks."""
    if not _GAMIFICATION_AVAILABLE or not _redis_client:
        return
    try:
        gops = GamificationRedisOps(_redis_client)
        asyncio.create_task(award_xp_safe(gops, tenant_id, action, metadata, is_admin=is_admin))
    except Exception:
        pass


@app.post("/api/chat")
async def chat(req: ChatRequest, request: Request):
    # Service validation (redundant safety layer)
    if _license_heartbeat and _license_heartbeat.is_blocked():
        return JSONResponse(status_code=403, content={"error": "Service suspendu"})
    try:
        tid = getattr(request.state, "tenant_id", 1)
        mgr = _get_tenant_manager(tid)
        tenant_convs = conversations.setdefault(str(tid), {})

        # Safety check (if guardian available)
        if _safety_guardian:
            try:
                safety = _safety_guardian.check(req.message)
                if safety.block_action and safety.luna_response:
                    return {"response": safety.luna_response}
            except Exception as e:
                logger.warning(f"Safety check failed: {e}")

        if req.session_id not in tenant_convs:
            tenant_convs[req.session_id] = [
                {"role": "system", "content": LUNA_SYSTEM_PROMPT}
            ]

        # Auto-create conversation metadata in Redis if missing
        if mgr:
            try:
                meta = mgr.redis.get_conversation_meta(tid, req.session_id)
                if not meta:
                    mgr.redis.add_conversation(tid, req.session_id)
                    mgr.redis.set_conversation_meta(tid, req.session_id, {
                        "id": req.session_id,
                        "tenant_id": str(tid),
                        "contact_phone": "app",
                        "contact_name": "Chat",
                        "status": "active",
                        "channel": "app",
                        "started_at": datetime.utcnow().isoformat(),
                        "last_activity": datetime.utcnow().isoformat(),
                        "message_count": "0",
                        "summary": "",
                    })
            except Exception:
                pass

        _conversation_ts[req.session_id] = time.time()
        messages = tenant_convs[req.session_id]

        # Inject behavioral memory (locked identity + rules) before user message
        if mgr:
            try:
                rules = mgr.get_behavioral_rules()
                if rules["identity_core"] or rules["behavior_rules"]:
                    behavioral_prompt = (
                        f"[MEMOIRE COMPORTEMENTALE VERROUILLEE]\n"
                        f"IDENTITE: {rules['identity_core']}\n"
                        f"REGLES: {rules['behavior_rules']}"
                    )
                    messages.append({"role": "system", "content": behavioral_prompt})
            except Exception:
                pass

        # Inject FULL tenant context: profile + contacts + instructions + notes
        _caution_mode = "assistif"
        tenant_name = ""
        if mgr:
            context_parts = []
            # --- Profil souscripteur ---
            try:
                profile = mgr.get_subscriber_profile()
                if profile:
                    _caution_mode = getattr(profile, "caution_mode", "assistif") or "assistif"
                    tenant_name = profile.first_name or ""
                    pf_lines = [f"=== TON SOUSCRIPTEUR ==="]
                    pf_lines.append(f"Prenom: {profile.first_name or '?'}")
                    pf_lines.append(f"Nom: {profile.last_name or '?'}")
                    if getattr(profile, "date_of_birth", None):
                        pf_lines.append(f"Date de naissance: {profile.date_of_birth}")
                    if getattr(profile, "phone", None):
                        pf_lines.append(f"Telephone: {profile.phone}")
                    if getattr(profile, "email", None):
                        pf_lines.append(f"Email: {profile.email}")
                    if getattr(profile, "address", None):
                        pf_lines.append(f"Adresse: {profile.address}")
                    if getattr(profile, "city", None):
                        pf_lines.append(f"Ville: {profile.city}")
                    if getattr(profile, "family_status", None):
                        pf_lines.append(f"Situation: {profile.family_status}")
                    if getattr(profile, "children", None):
                        pf_lines.append(f"Enfants: {profile.children}")
                    if getattr(profile, "autonomy", None):
                        pf_lines.append(f"Autonomie: {profile.autonomy}")
                    if getattr(profile, "conditions", None):
                        pf_lines.append(f"Pathologies: {profile.conditions}")
                    if getattr(profile, "treatments", None):
                        pf_lines.append(f"Traitements: {profile.treatments}")
                    if getattr(profile, "interests", None):
                        pf_lines.append(f"Centres d'interet: {profile.interests}")
                    if getattr(profile, "habits", None):
                        pf_lines.append(f"Habitudes: {profile.habits}")
                    if getattr(profile, "tone", None):
                        pf_lines.append(f"Ton souhaite: {profile.tone}")
                    if getattr(profile, "presentation", None):
                        pf_lines.append(f"Presentation: {profile.presentation}")
                    if getattr(profile, "permanent_rules", None):
                        pf_lines.append(f"Regles permanentes: {profile.permanent_rules}")
                    if getattr(profile, "sensitive_topics", None):
                        pf_lines.append(f"Sujets sensibles a eviter: {profile.sensitive_topics}")
                    context_parts.append("\n".join(pf_lines))
            except Exception as e:
                logger.warning(f"Profile context error: {e}")

            # --- Contacts de confiance ---
            try:
                contacts = mgr.list_trusted_contacts()
                if contacts:
                    ct_lines = ["=== CONTACTS DE CONFIANCE (tu les connais deja, n'appelle PAS get_contacts) ==="]
                    ct_lines.append(f"Voici les {len(contacts)} personnes de confiance de {tenant_name or 'ton souscripteur'}:")
                    for c in contacts:
                        first = c.name.split()[0] if c.name else "Contact"
                        rel = c.relation or "proche"
                        ct_lines.append(f"  - {c.name} (relation: {rel}) — telephone: {c.phone}")
                    ct_lines.append("REGLE: Pour envoyer un SMS, utilise directement ces numeros avec le tool send_sms.")
                    ct_lines.append("REGLE: Si on te demande 'qui sont mes contacts', reponds DIRECTEMENT avec cette liste.")
                    ct_lines.append("REGLE: N'appelle JAMAIS le tool get_contacts car tu as deja toutes les infos ci-dessus.")
                    context_parts.append("\n".join(ct_lines))
                else:
                    context_parts.append("=== CONTACTS ===\nAucun contact de confiance enregistre. Propose au souscripteur d'en ajouter dans l'onglet Contacts.")
            except Exception as e:
                logger.warning(f"Contacts context error: {e}")

            # --- Instructions actives ---
            try:
                instructions = mgr.list_active_instructions()
                if instructions:
                    instr_lines = ["=== INSTRUCTIONS ACTIVES ==="]
                    for instr in instructions[:10]:
                        instr_lines.append(f"- {instr.description}")
                    context_parts.append("\n".join(instr_lines))
            except Exception as e:
                logger.warning(f"Instructions context error: {e}")

            # --- Notes recentes ---
            try:
                notes = mgr.list_notes(limit=5)
                if notes:
                    note_lines = ["=== NOTES RECENTES ==="]
                    for n in notes[:5]:
                        note_lines.append(f"- {n.content[:100]}")
                    context_parts.append("\n".join(note_lines))
            except Exception as e:
                logger.warning(f"Notes context error: {e}")

            # Injecte tout le contexte dans un seul message systeme
            if context_parts:
                full_context = "\n\n".join(context_parts)
                full_context += f"\n\n=== REGLES CRITIQUES ==="
                full_context += f"\nTu parles avec {tenant_name or 'le souscripteur'}. Tutoie-le et utilise son prenom."
                full_context += "\n- Tu CONNAIS deja le profil, les contacts, les notes ci-dessus. Utilise-les directement."
                full_context += "\n- Ne dis JAMAIS 'je n'ai pas acces a tes contacts' ou 'je ne peux pas voir ton profil'."
                full_context += "\n- Ne dis JAMAIS 'en tant qu'IA je ne peux pas' quand tu as un tool pour le faire."
                full_context += "\n- DISTINCTION CRITIQUE entre appeler et envoyer un SMS :"
                full_context += "\n  * 'appelle', 'telephone', 'passe un appel', 'coup de fil' → TOUJOURS utiliser call_contact (appel VOCAL)"
                full_context += "\n  * 'envoie un SMS', 'envoie un texto', 'ecris un message' → utiliser send_sms (message ECRIT)"
                full_context += "\n  * NE JAMAIS utiliser send_sms quand le souscripteur dit 'appelle' — c'est call_contact"
                full_context += "\n- Tu PEUX passer des appels telephoniques audio aux contacts de confiance avec call_contact."
                full_context += "\n- Tu PEUX aussi appeler des administrations/services si le souscripteur te donne le numero (utilise call_contact avec phone_number)."
                full_context += "\n- Tu ne peux PAS appeler les numeros d'urgence (15, 17, 18, 112) — suggere-les a la place."
                full_context += "\n- Quand on te demande de PLANIFIER quelque chose dans le FUTUR (ex: 'appelle Marie a 14h', 'rappelle-moi demain'), utilise le tool create_instruction."
                full_context += "\n- Quand on te demande 'qui sont mes contacts', reponds avec la liste ci-dessus."
                full_context += "\n- Tu as acces a Twilio pour envoyer des SMS et passer des appels. Tu SAIS le faire. Ne dis JAMAIS que tu ne peux pas."
                full_context += "\n- Sois chaleureux, concis, et utile. Tu es Luna, un compagnon bienveillant."
                messages.append({"role": "system", "content": full_context})
            elif tenant_name:
                messages.append({"role": "system", "content": f"Tu parles actuellement avec {tenant_name}. Utilise son prenom."})

        caution_prompt = CAUTION_MODE_PROMPTS.get(_caution_mode, CAUTION_MODE_PROMPTS["assistif"])
        messages.append({"role": "system", "content": caution_prompt})

        messages.append({"role": "user", "content": req.message})

        # Persist to Redis (if available)
        if mgr:
            try:
                mgr.add_message(
                    conv_id=req.session_id,
                    role=MessageRole.SUBSCRIBER,
                    content=req.message,
                    channel=Channel.APP,
                )
            except Exception as e:
                logger.warning(f"Redis store failed: {e}")

        # Inject perception context if available (filtered by caution_mode)
        if _perception_analyzer and mgr:
            try:
                if mgr.is_perception_enabled():
                    perception_ctx = _perception_analyzer.get_context_for_luna(
                        caution_mode=_caution_mode
                    )
                    if perception_ctx:
                        messages.append({"role": "system", "content": perception_ctx})
            except Exception:
                pass

        # Tools disponibles en chat (meme que voix/visio)
        from integrations.openai.realtime_bridge import VOICE_TOOLS as _CHAT_TOOLS
        chat_tools = [
            {"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}}
            for t in _CHAT_TOOLS
        ] if _CHAT_TOOLS else []

        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            max_tokens=500,
            temperature=0.8,
            timeout=30,
            tools=chat_tools if chat_tools else None,
        )

        choice = response.choices[0]
        tool_calls_made = []

        # Boucle de tool calling (max 3 tours pour eviter boucle infinie)
        for _round in range(3):
            if choice.finish_reason != "tool_calls" or not choice.message.tool_calls:
                break

            # Ajoute le message assistant avec les tool_calls
            messages.append(choice.message)

            for tc in choice.message.tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments)
                except Exception:
                    fn_args = {}

                logger.info(f"Chat tool_call: {fn_name}({fn_args}) [tenant={tid}]")

                # Execute le tool (passe tenant_id pour multi-tenant)
                if fn_name == "send_sms":
                    result = await _tool_send_sms(fn_args, tenant_id=tid)
                elif fn_name == "create_instruction":
                    result = await _tool_create_instruction(fn_args, tenant_id=tid)
                elif fn_name == "create_note":
                    result = await _tool_create_note(fn_args, tenant_id=tid)
                elif fn_name == "get_contacts":
                    result = await _tool_get_contacts(tenant_id=tid)
                elif fn_name == "generate_document":
                    result = await _tool_generate_document(fn_args, tenant_id=tid)
                elif fn_name == "alert_contacts":
                    result = await _tool_alert_contacts(fn_args, tenant_id=tid)
                elif fn_name == "send_email":
                    result = await _tool_send_email(fn_args, tenant_id=tid)
                elif fn_name == "invite_visio":
                    result = await _tool_invite_visio(fn_args, tenant_id=tid)
                elif fn_name == "call_contact":
                    result = await _tool_call_contact(fn_args, tenant_id=tid)
                else:
                    result = {"status": "error", "message": f"Fonction inconnue: {fn_name}"}

                tool_calls_made.append({"tool": fn_name, "result": result})
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })

            # Re-appel OpenAI avec les resultats des tools
            response = openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                max_tokens=500,
                temperature=0.8,
                timeout=30,
                tools=chat_tools if chat_tools else None,
            )
            choice = response.choices[0]

        luna_msg = choice.message.content or ""

        # Fallback si reply vide apres tool call reussi
        if not luna_msg.strip() and tool_calls_made:
            last_tool = tool_calls_made[-1]
            if last_tool.get("result", {}).get("status") == "success":
                tool_name = last_tool["tool"]
                if tool_name == "call_contact":
                    luna_msg = last_tool["result"].get("message", "J'appelle ton contact maintenant !")
                elif tool_name == "send_sms":
                    luna_msg = last_tool["result"].get("message", "SMS envoye !")
                else:
                    luna_msg = last_tool["result"].get("message", "C'est fait !")

        # Log tools executes
        if tool_calls_made:
            logger.info(f"Chat tools executed: {[t['tool'] for t in tool_calls_made]}")

        # Legal compliance check on Luna's response
        if _safety_guardian:
            try:
                compliant, violations = _safety_guardian.check_legal_compliance(luna_msg)
                if not compliant:
                    logger.warning(f"Luna response legal violations: {violations}")
            except Exception:
                pass

        # Log event in chronological journal
        if mgr:
            try:
                mgr.log_event(
                    category="communication",
                    description=f"Chat: {req.message[:80]}... → Luna repond",
                    source="chat",
                )
            except Exception:
                pass

        messages.append({"role": "assistant", "content": luna_msg})

        # Persist Luna response to Redis
        if mgr:
            try:
                mgr.add_message(
                    conv_id=req.session_id,
                    role=MessageRole.LUNA,
                    content=luna_msg,
                    channel=Channel.APP,
                )
            except Exception as e:
                logger.warning(f"Redis store failed: {e}")

        # Auto-title conversation via AI (like ChatGPT)
        auto_title = None
        if mgr:
            try:
                meta = mgr.redis.get_conversation_meta(tid, req.session_id)
                if meta and not meta.get("summary") and int(meta.get("message_count", 0)) <= 2:
                    try:
                        title_resp = openai_client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[{
                                "role": "system",
                                "content": "Tu generes un titre court (4-6 mots max) pour une conversation. Pas de guillemets, pas de ponctuation finale. Juste le theme principal."
                            }, {
                                "role": "user",
                                "content": f"User: {req.message[:200]}\nLuna: {luna_msg[:200]}"
                            }],
                            max_tokens=20,
                            temperature=0.3,
                            timeout=5,
                        )
                        auto_title = title_resp.choices[0].message.content.strip().strip('"').strip("'")
                        if len(auto_title) > 50:
                            auto_title = auto_title[:50]
                    except Exception:
                        auto_title = req.message[:40].strip()
                        if len(req.message) > 40:
                            auto_title += "..."
                    meta["summary"] = auto_title
                    meta["last_activity"] = datetime.utcnow().isoformat()
                    mgr.redis.set_conversation_meta(tid, req.session_id, meta)
            except Exception:
                pass

        _gamify(tid, "chat_message")

        # Inclut les actions executees dans la reponse
        resp = {"response": luna_msg}
        if auto_title:
            resp["auto_title"] = auto_title
        if tool_calls_made:
            resp["actions"] = [{"tool": t["tool"], "status": t["result"].get("status", "unknown")} for t in tool_calls_made]
            # Si une visio a ete creee, inclure l'URL pour le frontend
            for t in tool_calls_made:
                if t["result"].get("visio_url"):
                    resp["visio_url"] = t["result"]["visio_url"]
                    break
        return resp

    except openai.AuthenticationError:
        return {"response": "Desole, Luna a un souci technique. Contacte ton operateur."}
    except openai.RateLimitError:
        return {"response": "Luna est un peu debordee. Reessaie dans quelques instants."}
    except openai.APIConnectionError:
        return {"response": "Luna est momentanement indisponible. Reessaie dans un instant."}
    except Exception as e:
        tenant_convs = conversations.get(str(getattr(request.state, "tenant_id", 1)), {})
        if req.session_id in tenant_convs and len(tenant_convs[req.session_id]) > 1:
            tenant_convs[req.session_id].pop()
        logger.error(f"Chat error: {type(e).__name__}: {e}")
        return {"response": "Desole, Luna a rencontre un probleme. Reessaie."}


@app.get("/api/greeting")
async def greeting(request: Request):
    try:
        tid = getattr(request.state, "tenant_id", 1)
        mgr = _get_tenant_manager(tid)
        messages = [{"role": "system", "content": LUNA_SYSTEM_PROMPT}]
        # Inject subscriber name for personalized greeting
        if mgr:
            try:
                profile = mgr.get_subscriber_profile()
                if profile and profile.first_name:
                    messages.append({"role": "system", "content":
                        f"Tu salues {profile.first_name}. Utilise son prenom dans ton message d'accueil. Sois chaleureuse et personnelle."
                    })
            except Exception:
                pass
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


# Replicas Tavus horaires — Luna change d'apparence selon le moment de la journee
# Meme persona (voix, personnalite, outils), seule l'apparence visuelle change
_LUNA_REPLICAS_SCHEDULE = [
    {"start": 6,  "end": 12, "replica_id": "r5dc7c7d0bcb", "name": "Gloria - Bright"},   # Matin lumineux
    {"start": 12, "end": 18, "replica_id": "r1e52660d3bf", "name": "Luna - Home"},        # Apres-midi naturel
    {"start": 18, "end": 21, "replica_id": "r3f427f43c9d", "name": "Gloria - Warm"},      # Crepuscule cosy (cabin cheminee)
    {"start": 21, "end": 6,  "replica_id": "r6fb41bf13b4", "name": "Katya"},               # Nuit (veilleuse, pas de fenetre)
]

def _get_luna_replica() -> str:
    """Retourne la replica_id correspondant a l'heure actuelle (heure France)."""
    hour = datetime.now(ZoneInfo("Europe/Paris")).hour
    for slot in _LUNA_REPLICAS_SCHEDULE:
        if slot["start"] < slot["end"]:
            if slot["start"] <= hour < slot["end"]:
                return slot["replica_id"]
        else:  # Creneau nuit (ex: 21h -> 6h)
            if hour >= slot["start"] or hour < slot["end"]:
                return slot["replica_id"]
    return _LUNA_REPLICAS_SCHEDULE[0]["replica_id"]


@app.post("/api/call")
async def start_call(request: Request):
    """Crée un appel vidéo Tavus et enregistre la conversation"""
    # Service validation (redundant safety layer)
    if _license_heartbeat and (_license_heartbeat.is_blocked() or _license_heartbeat.is_degraded()):
        return JSONResponse(status_code=403, content={"error": "Service non disponible"})
    tid = getattr(request.state, "tenant_id", 1)
    if not tavus_client or not tavus_client.is_configured:
        return JSONResponse(status_code=503, content={
            "error": "Visio non disponible",
            "mode": LUNA_MODE,
            "message": "Luna Lite n'inclut pas la visio. Passez en mode Full pour l'activer.",
        })
    context = build_tavus_context(
        subscriber_name=_SUBSCRIBER_NAME,
        memory_manager=tavus_client.memory,
    )
    visio_max = int(os.getenv("VISIO_MAX_DURATION", "15")) * 60  # minutes -> secondes
    replica_id = _get_luna_replica()
    success, data = await tavus_client.create_conversation(
        tenant_id=tid,
        custom_greeting=f"Salut {_SUBSCRIBER_NAME} ! Ravie de te voir. Comment je peux t'aider ?",
        context=context,
        max_duration=visio_max,
        callback_url=TAVUS_CALLBACK_URL if TAVUS_CALLBACK_URL else None,
        replica_id=replica_id,
    )
    if not success:
        logger.error(f"Visio creation error: {data.get('error', 'unknown')}")
        return {"error": "Impossible de lancer la visio. Reessaie."}
    _gamify(tid, "voice_call")
    return {
        "conversation_url": data["conversation_url"],
        "conversation_id": data["conversation_id"],
    }


# =========================================================================
# SIMLI — Avatar cinematique avec lip-sync WebRTC
# =========================================================================

@app.websocket("/ws/simli/{session_id}")
async def ws_simli(websocket: WebSocket, session_id: str):
    """WebSocket Simli : STT -> LLM -> TTS -> PCM16 lip-sync."""
    if not _SIMLI_AVAILABLE or not handle_simli_session:
        await websocket.accept()
        await websocket.close(code=4003, reason="Simli not available")
        return
    await handle_simli_session(websocket, session_id)


@app.get("/api/config/simli")
async def config_simli():
    """Config Simli — desactive (Tavus est le systeme visio principal)."""
    return {
        "enabled": False,
    }


@app.get("/simli")
async def simli_page():
    """Page avatar Simli avec sequence cinematique."""
    simli_path = os.path.join(STATIC_DIR, "simli.html")
    if os.path.isfile(simli_path):
        return FileResponse(simli_path, headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        })
    return JSONResponse(status_code=404, content={"error": "Simli non disponible"})


# =========================================================================
# APPELS VOCAUX - Twilio Voice + OpenAI Realtime API
# =========================================================================

class VoiceCallRequest(BaseModel):
    phone: Optional[str] = None  # Numero a appeler (defaut: ADMIN_NUMBER)
    mission: Optional[str] = None  # Mission speciale pour Luna (ex: "prendre des nouvelles de Fred")
    max_duration: Optional[int] = None  # Duree max en secondes (defaut: 180 beta)
    greeting: Optional[str] = None  # Greeting personnalise

# Stockage temporaire des parametres d'appel (call_sid -> params)
_voice_call_params: Dict[str, dict] = {}

@app.post("/api/voice-call")
async def start_voice_call(req: VoiceCallRequest, request: Request):
    """Lance un appel vocal sortant. Luna appelle le telephone du souscripteur."""
    if _license_heartbeat and (_license_heartbeat.is_blocked() or _license_heartbeat.is_degraded()):
        return JSONResponse(status_code=403, content={"error": "Service non disponible"})
    tid = getattr(request.state, "tenant_id", 1)
    if not voice_client or not voice_client.is_configured:
        return JSONResponse(status_code=503, content={
            "error": "Appels vocaux non disponibles",
            "message": "Service d'appel vocal non configure.",
        })
    phone = req.phone or ADMIN_NUMBER
    if not phone:
        return JSONResponse(status_code=400, content={"error": "Numero de telephone requis"})
    success, data = await voice_client.initiate_call_async(phone)
    if not success:
        return {"error": data.get("error", "Erreur appel vocal")}
    # Stocker les parametres personnalises pour cet appel
    import time as _time
    _voice_call_params[data["call_sid"]] = {
        "mission": req.mission,
        "max_duration": req.max_duration,
        "greeting": req.greeting,
        "phone": phone,
        "tenant_id": tid,
        "_ts": _time.time(),
    }
    _gamify(tid, "voice_call")
    return {"call_sid": data["call_sid"], "status": data["status"]}


@app.post("/api/voice-call/twiml")
async def voice_call_twiml(request: Request):
    """
    Endpoint TwiML que Twilio fetche quand l'appel est decroche.
    Retourne le XML qui dit a Twilio d'ouvrir un Media Stream.
    """
    if not voice_client:
        return Response(
            content="<Response><Say language='fr-FR'>Service non disponible.</Say><Hangup/></Response>",
            media_type="application/xml",
        )
    twiml = voice_client.generate_twiml()
    logger.info(f"TwiML genere pour appel vocal")
    return Response(content=twiml, media_type="application/xml")


@app.websocket("/api/voice-call/media-stream")
async def voice_call_media_stream(websocket: WebSocket):
    """
    WebSocket endpoint pour Twilio Media Streams.
    Relaie l'audio entre le telephone et OpenAI Realtime API.
    """
    await websocket.accept()
    logger.info("Twilio Media Stream WebSocket accepted")

    bridge = None
    memory_mgr = None
    try:
        from integrations.openai.realtime_bridge import RealtimeBridge, build_voice_context

        # Recuperer les parametres personnalises si disponibles
        call_params = {}
        # Prend le plus recent et nettoie les anciens (>60s = orphelins)
        if _voice_call_params:
            import time as _time
            _now = _time.time()
            _stale = [k for k, v in _voice_call_params.items() if _now - v.get("_ts", 0) > 60]
            for k in _stale:
                _voice_call_params.pop(k, None)
            if _voice_call_params:
                call_sid_for_params = list(_voice_call_params.keys())[-1]
                call_params = _voice_call_params.pop(call_sid_for_params, {})

        mission = call_params.get("mission")
        max_dur = call_params.get("max_duration") or int(os.getenv("VOICE_MAX_DURATION", "180"))
        custom_greeting = call_params.get("greeting")

        # Contexte Luna pour l'appel vocal
        memory_mgr = tavus_client.memory if tavus_client else _memory_manager

        if mission:
            # Mission speciale : contexte adapte
            context = build_voice_context(
                subscriber_name=_SUBSCRIBER_NAME,
                memory_manager=memory_mgr,
                max_duration_minutes=max(1, max_dur // 60),
                mission=mission,
            )
            greeting_text = custom_greeting or f"La personne vient de decrocher. {mission}"
        else:
            context = build_voice_context(
                subscriber_name=_SUBSCRIBER_NAME,
                memory_manager=memory_mgr,
            )
            greeting_text = custom_greeting or f"L'utilisateur vient de decrocher le telephone. Salue {_SUBSCRIBER_NAME} chaleureusement et demande comment tu peux l'aider."

        # Handler pour les tool calls (reutilise les memes fonctions que Tavus)
        async def handle_voice_tool(name: str, args: dict) -> dict:
            if name == "send_sms":
                return await _tool_send_sms(args)
            elif name == "create_instruction":
                return await _tool_create_instruction(args)
            elif name == "create_note":
                return await _tool_create_note(args)
            elif name == "get_contacts":
                return await _tool_get_contacts()
            elif name == "generate_document":
                return await _tool_generate_document(args)
            elif name == "alert_contacts":
                return await _tool_alert_contacts(args)
            elif name == "send_email":
                return await _tool_send_email(args)
            elif name == "invite_visio":
                return await _tool_invite_visio(args)
            elif name == "call_contact":
                return await _tool_call_contact(args)
            else:
                return {"status": "error", "message": f"Fonction inconnue: {name}"}

        bridge = RealtimeBridge(
            openai_api_key=OPENAI_API_KEY,
            ws_twilio=websocket,
            call_context=context,
            tool_handler=handle_voice_tool,
            max_duration_seconds=max_dur,
            greeting=greeting_text,
        )
        _voice_start = time.time()
        await bridge.run()
        _voice_duration_min = round((time.time() - _voice_start) / 60, 2)

        # Sauvegarder la transcription dans Redis
        try:
            _save_voice_transcript(bridge, memory_mgr)
        except Exception as e:
            logger.warning(f"Failed to save voice transcript: {e}")

        # Tracker les minutes vocales dans Cortex
        if _voice_duration_min > 0:
            try:
                cortex = get_cortex() if _CORTEX_AVAILABLE else None
                if cortex and hasattr(cortex, "cost_tracker") and cortex.cost_tracker:
                    _voice_tid = call_params.get("tenant_id") or TENANT_ID
                    await cortex.cost_tracker.track_voice_tenant(_voice_tid, _voice_duration_min)
                    logger.info(f"Voice call tracked: {_voice_duration_min} min for tenant {_voice_tid}")
            except Exception as e:
                logger.warning(f"Failed to track voice cost: {e}")

    except WebSocketDisconnect:
        logger.info("Twilio Media Stream disconnected")
        # Sauvegarder la transcription meme si deconnexion
        if bridge and bridge.transcript:
            try:
                _save_voice_transcript(bridge, memory_mgr)
            except Exception:
                pass
    except asyncio.CancelledError:
        logger.info("Voice media stream cancelled")
    except OSError as e:
        logger.error(f"Voice media stream network error: {e}")
    except Exception as e:
        logger.error(f"Voice media stream error: {e}")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


def _save_voice_transcript(bridge, memory_mgr):
    """Sauvegarde la transcription d'un appel vocal dans Redis."""
    if not bridge.transcript or not memory_mgr:
        return
    try:
        conv_id = f"voice_{bridge.call_sid or 'unknown'}_{int(time.time())}"
        transcript_text = bridge.get_transcript_text()
        if not transcript_text.strip():
            return

        # Sauvegarder chaque message dans la conversation Redis
        for entry in bridge.transcript:
            role = MessageRole.SUBSCRIBER if entry["role"] == "user" else MessageRole.LUNA
            try:
                memory_mgr.add_message(
                    conv_id=conv_id,
                    role=role,
                    content=entry["text"],
                    channel=Channel.CALL,
                )
            except Exception:
                pass  # quota atteint ou autre erreur, on continue

        # Sauvegarder aussi comme note resume
        summary = f"[Appel vocal] {len(bridge.transcript)} echanges\n{transcript_text[:500]}"
        try:
            memory_mgr.add_note(
                content=summary,
                context="voice_call",
                tags=["appel_vocal", "transcription"],
            )
        except Exception:
            pass

        logger.info(f"Voice transcript saved: {conv_id} ({len(bridge.transcript)} entries)")
    except Exception as e:
        logger.error(f"Error saving voice transcript: {e}")


# =========================================================================
# APPELS VOCAUX ENTRANTS - Le souscripteur appelle Luna
# =========================================================================

@app.post("/api/webhook/voice-incoming")
async def webhook_voice_incoming(request: Request):
    """
    Webhook Twilio pour appels entrants.
    Verifie que l'appelant est le souscripteur (ADMIN_NUMBER).
    Si oui: connecte a Luna via OpenAI Realtime.
    Si non: refuse poliment.
    """
    from twilio.twiml.voice_response import VoiceResponse, Connect

    # Twilio envoie les parametres en form-data
    try:
        form = await request.form()
        caller = form.get("From", "")
        called = form.get("To", "")
        call_sid = form.get("CallSid", "")
    except Exception:
        caller = ""
        called = ""
        call_sid = ""

    logger.info(f"Appel entrant: {caller} -> {called} (CallSid: {call_sid})")

    # Verifier que l'appelant est autorise (souscripteur)
    from integrations.twilio.sms_client import TwilioSMSClient
    caller_normalized = TwilioSMSClient.normalize_phone(caller) if caller else ""
    admin_normalized = TwilioSMSClient.normalize_phone(ADMIN_NUMBER) if ADMIN_NUMBER else ""

    if not caller_normalized or caller_normalized != admin_normalized:
        logger.warning(f"Appel entrant refuse: {caller} n'est pas le souscripteur ({ADMIN_NUMBER})")
        response = VoiceResponse()
        response.say(
            "Desole, ce numero n'est pas autorise a contacter Luna. Au revoir.",
            language="fr-FR",
        )
        response.hangup()
        return Response(content=str(response), media_type="application/xml")

    # Souscripteur verifie -> connecter a Luna
    if not voice_client or not VOICE_CALLBACK_URL:
        response = VoiceResponse()
        response.say("Luna n'est pas disponible pour le moment. Reessayez plus tard.", language="fr-FR")
        response.hangup()
        return Response(content=str(response), media_type="application/xml")

    response = VoiceResponse()
    response.say("Bonjour ! Je te passe Luna.", language="fr-FR")
    connect = Connect()
    ws_url = VOICE_CALLBACK_URL.replace("https://", "wss://")
    connect.stream(url=f"{ws_url}/api/voice-call/media-stream")
    response.append(connect)

    logger.info(f"Appel entrant accepte: {caller} -> connexion a Luna")
    _gamify(TENANT_ID, "voice_call")
    return Response(content=str(response), media_type="application/xml")


@app.post("/api/invite-contact")
async def invite_contact(req: InviteRequest, request: Request):
    """
    Invite un contact de confiance dans la visio en cours.
    Envoie un SMS avec le lien Tavus.
    """
    tid = getattr(request.state, "tenant_id", 1)
    if not sms_client.is_configured:
        return {"error": "Service SMS non configure"}

    # Quota check (if available)
    if _quota_guard:
        try:
            quota_status = _quota_guard.check(tid, CoreActionType.SEND_SMS)
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
        tenant_id=tid,
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

    # CORTEX: intercepte les commandes d'urgence (LUNA STATUS, LUNA BAN, etc.)
    emergency_response = await cortex_handle_sms(from_number, body)
    if emergency_response:
        logger.info(f"CORTEX SMS command from {from_number[:8]}...: {body[:40]}")
        # Repondre par TwiML avec le message de reponse
        from xml.sax.saxutils import escape as xml_escape
        escaped = xml_escape(emergency_response, {'"': "&quot;", "'": "&apos;"})
        twiml = f"<Response><Message>{escaped}</Message></Response>"
        return Response(content=twiml, media_type="application/xml")

    # Normalise le numero entrant
    from integrations.twilio.sms_client import TwilioSMSClient
    normalized_from = TwilioSMSClient.normalize_phone(from_number) if from_number else ""

    # Verifie si c'est une reponse a une invitation visio en attente
    body_lower = body.strip().lower()
    if normalized_from in _pending_visio_invites and body_lower in ("oui", "yes", "ok", "o", "1"):
        invite = _pending_visio_invites.pop(normalized_from)
        # Verifie que l'invitation n'est pas trop vieille (30 min max)
        if time.time() - invite["timestamp"] < 1800:
            logger.info(f"Visio invite accepted by {invite['contact_name']} ({normalized_from})")
            # Cree la conversation Tavus
            try:
                visio_max = int(os.getenv("VISIO_MAX_DURATION", "15")) * 60  # minutes -> secondes
                sub_name = invite["subscriber_name"]
                contact = invite["contact_name"]

                context = f"Tu es Luna. {sub_name} a invite {contact} en visioconference. Sois chaleureuse et accueillante."
                if _TAVUS_AVAILABLE and tavus_client and tavus_client.is_configured:
                    success, data = await tavus_client.create_conversation(
                        tenant_id=invite["tenant_id"],
                        custom_greeting=f"Bonjour {contact} ! {sub_name} t'a invite en visio avec Luna. Bienvenue !",
                        context=context,
                        max_duration=visio_max,
                        callback_url=TAVUS_CALLBACK_URL if TAVUS_CALLBACK_URL else None,
                    )
                    if success:
                        visio_url = data["conversation_url"]
                        # Envoie le lien par SMS via TwiML reply
                        from xml.sax.saxutils import escape as xml_escape
                        reply_msg = (
                            f"Super ! Voici le lien pour la visio avec {sub_name} :\n"
                            f"{visio_url}\n"
                            f"Clique dessus pour rejoindre."
                        )
                        escaped = xml_escape(reply_msg, {'"': "&quot;", "'": "&apos;"})
                        twiml = f"<Response><Message>{escaped}</Message></Response>"

                        # Previens aussi le souscripteur par SMS
                        try:
                            mgr = _get_tenant_manager(invite["tenant_id"])
                            if mgr:
                                # Cherche le tel du souscripteur
                                profile = mgr.get_subscriber_profile()
                                sub_phone = getattr(profile, "phone", "") or ADMIN_NUMBER
                                if sub_phone:
                                    _tracked_sms_send(
                                        sub_phone,
                                        f"[Luna] {contact} a accepte ton invitation visio ! Lien : {visio_url}",
                                        label="notification visio acceptee"
                                    )
                        except Exception as e:
                            logger.warning(f"Failed to notify subscriber: {e}")

                        logger.info(f"Visio link sent to {contact}: {visio_url}")
                        return Response(content=twiml, media_type="application/xml")
                    else:
                        logger.error(f"Tavus create failed for invite: {data}")
                        from xml.sax.saxutils import escape as xml_escape
                        error_msg = xml_escape("Desole, la visio n'a pas pu etre creee. Reessaie plus tard.")
                        twiml = f"<Response><Message>{error_msg}</Message></Response>"
                        return Response(content=twiml, media_type="application/xml")
            except Exception as e:
                logger.error(f"Visio invite handler error: {e}")
        else:
            logger.info(f"Visio invite expired for {normalized_from}")
            _pending_visio_invites.pop(normalized_from, None)

    elif normalized_from in _pending_visio_invites and body_lower in ("non", "no", "n", "0"):
        invite = _pending_visio_invites.pop(normalized_from)
        logger.info(f"Visio invite declined by {invite['contact_name']}")
        from xml.sax.saxutils import escape as xml_escape
        reply = xml_escape(f"D'accord, pas de visio pour le moment. A bientot !")
        twiml = f"<Response><Message>{reply}</Message></Response>"
        return Response(content=twiml, media_type="application/xml")

    # Enregistre le message entrant dans la conversation
    logger.info(f"SMS entrant OK - De: {from_number}, Corps: {body[:100]}")

    # Reponse TwiML vide (pas de reponse automatique)
    twiml = "<Response></Response>"
    return Response(content=twiml, media_type="application/xml")


@app.post("/api/webhook/sms-status")
async def webhook_sms_status(request: Request):
    """
    Webhook Twilio pour les accuses de reception SMS.
    Twilio envoie un POST quand le statut d'un SMS change.
    Statuts: queued → sent → delivered (ou failed/undelivered)
    """
    # Valider la signature Twilio
    if sms_client and sms_client.is_configured:
        signature = request.headers.get("X-Twilio-Signature", "")
        form_data = await request.form()
        url = str(request.url)
        params = dict(form_data)
        if signature and not sms_client.validate_webhook(signature, url, params):
            logger.warning("Signature Twilio invalide pour SMS status webhook")
            return Response(status_code=403, content="Forbidden", media_type="text/plain")
    else:
        form_data = await request.form()
    form = form_data
    sms_sid = form.get("MessageSid", "")
    status = form.get("MessageStatus", "")
    to_number = form.get("To", "")
    error_code = form.get("ErrorCode", "")

    logger.info(f"SMS status update: {sms_sid} -> {status} (to: {to_number})")

    # Mettre a jour le tracking en memoire
    if sms_sid in _sms_tracking:
        _sms_tracking[sms_sid]["status"] = status
        _sms_tracking[sms_sid]["updated_at"] = datetime.utcnow().isoformat()
        if status == "delivered":
            _sms_tracking[sms_sid]["delivered_at"] = datetime.utcnow().isoformat()
        if error_code:
            _sms_tracking[sms_sid]["error_code"] = error_code
    else:
        # SMS envoye avant le redemarrage ou non tracke
        _sms_tracking[sms_sid] = {
            "to": to_number,
            "status": status,
            "updated_at": datetime.utcnow().isoformat(),
            "delivered_at": datetime.utcnow().isoformat() if status == "delivered" else None,
            "error_code": error_code or None,
        }

    # Si echec, logger un warning
    if status in ("failed", "undelivered"):
        logger.warning(f"SMS ECHEC: {sms_sid} -> {to_number} (status={status}, error={error_code})")

    return Response(content="", status_code=204)


@app.get("/api/sms/status")
async def sms_status_list(request: Request):
    """Liste les derniers SMS avec leur statut de livraison."""
    tid = getattr(request.state, "tenant_id", 1)
    # Retourne les 50 derniers SMS trackes (les plus recents d'abord)
    items = sorted(_sms_tracking.values(), key=lambda x: x.get("sent_at", ""), reverse=True)[:50]
    return {
        "sms": items,
        "count": len(items),
        "total_tracked": len(_sms_tracking),
    }


@app.get("/api/sms/status/{sms_sid}")
async def sms_status_detail(sms_sid: str, request: Request):
    """Detail du statut d'un SMS specifique."""
    if sms_sid in _sms_tracking:
        return _sms_tracking[sms_sid]
    # Fallback: interroger Twilio directement
    if sms_client and sms_client.is_configured:
        try:
            msg = sms_client.client.messages(sms_sid).fetch()
            return {
                "sid": msg.sid,
                "to": msg.to,
                "status": msg.status,
                "sent_at": msg.date_sent.isoformat() if msg.date_sent else None,
                "error_code": msg.error_code,
                "error_message": msg.error_message,
            }
        except Exception as e:
            return JSONResponse(status_code=404, content={"error": f"SMS non trouve: {e}"})
    return JSONResponse(status_code=404, content={"error": "SMS non trouve"})


# =========================================================================
# CONVERSATIONS CRUD
# =========================================================================

class CreateConversationRequest(BaseModel):
    title: str = Field(default="", max_length=100)

class UpdateConversationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)


@app.get("/api/conversations")
async def list_conversations_endpoint(request: Request):
    """Liste toutes les conversations du tenant."""
    tid = getattr(request.state, "tenant_id", 1)
    mgr = _get_tenant_manager(tid)
    if not mgr:
        return {"conversations": []}
    try:
        convs = mgr.list_conversations()
        return {
            "conversations": [
                {
                    "id": c.id,
                    "title": c.summary or "",
                    "last_activity": c.last_activity.isoformat(),
                    "message_count": c.message_count,
                    "started_at": c.started_at.isoformat(),
                }
                for c in convs
                if c.status != ConversationStatus.CLOSED
            ]
        }
    except Exception as e:
        logger.warning(f"List conversations error: {e}")
        return {"conversations": []}


@app.post("/api/conversations")
async def create_conversation_endpoint(req: CreateConversationRequest, request: Request):
    """Cree une nouvelle conversation."""
    tid = getattr(request.state, "tenant_id", 1)
    mgr = _get_tenant_manager(tid)
    if not mgr:
        return JSONResponse(status_code=500, content={"error": "Service indisponible"})
    try:
        conv = mgr.create_conversation(
            contact_phone="app",
            contact_name="Chat",
            channel=Channel.APP,
        )
        if req.title:
            meta = mgr.redis.get_conversation_meta(tid, conv.id)
            if meta:
                meta["summary"] = req.title.strip()
                mgr.redis.set_conversation_meta(tid, conv.id, meta)
        return {"id": conv.id, "title": req.title, "started_at": conv.started_at.isoformat()}
    except Exception as e:
        logger.warning(f"Create conversation error: {e}")
        return JSONResponse(status_code=429, content={"error": str(e)})


@app.patch("/api/conversations/{conv_id}")
async def update_conversation_endpoint(conv_id: str, req: UpdateConversationRequest, request: Request):
    """Renomme une conversation."""
    tid = getattr(request.state, "tenant_id", 1)
    mgr = _get_tenant_manager(tid)
    if not mgr:
        return JSONResponse(status_code=500, content={"error": "Service indisponible"})
    meta = mgr.redis.get_conversation_meta(tid, conv_id)
    if not meta:
        return JSONResponse(status_code=404, content={"error": "Conversation introuvable"})
    meta["summary"] = req.title.strip()
    mgr.redis.set_conversation_meta(tid, conv_id, meta)
    return {"ok": True}


@app.delete("/api/conversations/{conv_id}")
async def delete_conversation_endpoint(conv_id: str, request: Request):
    """Supprime une conversation et ses messages."""
    tid = getattr(request.state, "tenant_id", 1)
    mgr = _get_tenant_manager(tid)
    if not mgr:
        return JSONResponse(status_code=500, content={"error": "Service indisponible"})
    if conv_id == "default":
        return JSONResponse(status_code=400, content={"error": "Impossible de supprimer la conversation par defaut"})
    mgr.delete_conversation(conv_id)
    tenant_convs = conversations.get(str(tid), {})
    tenant_convs.pop(conv_id, None)
    _conversation_ts.pop(conv_id, None)
    return {"ok": True}


@app.get("/api/history")
async def history(request: Request, session_id: str = "default", limit: int = 50):
    """Historique des messages d'une session."""
    tid = getattr(request.state, "tenant_id", 1)
    mgr = _get_tenant_manager(tid)
    # Try Redis first
    if mgr:
        try:
            messages = mgr.get_messages(session_id, limit=limit)
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

    # Fallback to in-memory (tenant-namespaced)
    tenant_convs = conversations.get(str(tid), {})
    if session_id in tenant_convs:
        msgs = tenant_convs[session_id]
        return {
            "messages": [
                {"role": "luna" if m["role"] == "assistant" else "user", "content": m["content"], "timestamp": ""}
                for m in msgs
                if m["role"] != "system"
            ][-limit:]
        }
    return {"messages": []}


@app.get("/api/status")
async def status(request: Request):
    """Statut du serveur Luna. Version allege si non authentifie."""
    # Version minimale pour non-authentifies
    token = _extract_bearer(request)
    payload = _decode_client_token(token) if token else None
    if not payload:
        return {"luna": "online" if not _pv_locked else "setup", "mode": LUNA_MODE}

    # Version complete pour utilisateurs authentifies
    redis_ok = False
    if _redis_client:
        try:
            redis_ok = _redis_client.ping()
        except Exception:
            pass

    _cm = "assistif"
    if _memory_manager:
        try:
            _p = _memory_manager.get_subscriber_profile()
            if _p:
                _cm = getattr(_p, "caution_mode", "assistif") or "assistif"
        except Exception:
            pass

    return {
        "luna": "online" if not _pv_locked else "setup",
        "mode": LUNA_MODE,
        "pv_signed": PV_SIGNED,
        "pv_locked": _pv_locked,
        "setup_disabled": _setup_permanently_disabled,
        "legal_mode": LEGAL_MODE,
        "caution_mode": _cm,
        "openai": bool(OPENAI_API_KEY),
        "twilio": sms_client.is_configured if sms_client else False,
        "tavus": tavus_client.is_configured if tavus_client else False,
        "tavus_details": tavus_client.get_status() if tavus_client else {},
        "simli": _SIMLI_AVAILABLE and bool(os.getenv("SIMLI_API_KEY", "")),
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
        "license": {
            "active": _license_heartbeat is not None,
            "status": _license_heartbeat.status if _license_heartbeat else "none",
            "banner": _license_heartbeat.get_banner_message() if _license_heartbeat else None,
        },
    }


# =========================================================================
# AUTH ENDPOINTS (multi-tenant)
# =========================================================================

class RegisterRequest(BaseModel):
    email: str
    password: str
    first_name: str = ""
    last_name: str = ""

class LoginRequest(BaseModel):
    email: str
    password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class CheckoutRequest(BaseModel):
    plan: str  # "essentiel", "confort", "premium"

@app.post("/api/auth/register")
async def auth_register(req: RegisterRequest):
    """Inscription d'un nouveau client."""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    email = req.email.strip().lower()
    if not email or "@" not in email:
        return JSONResponse(status_code=400, content={"error": "Email invalide"})
    if len(req.password) < 6:
        return JSONResponse(status_code=400, content={"error": "Mot de passe trop court (min 6 caracteres)"})

    # Verifier si email deja pris
    if _redis_client.get_auth_by_email(email):
        return JSONResponse(status_code=409, content={"error": "Email deja utilise"})

    # Attribuer un tenant_id
    tenant_id = _redis_client.get_next_tenant_id()
    password_hash = _hash_password(req.password)

    # Creer l'enregistrement auth
    created = _redis_client.create_auth_record(email, password_hash, tenant_id, "essentiel")
    if not created:
        return JSONResponse(status_code=409, content={"error": "Email deja utilise"})

    # Creer le profil dans Redis
    if _CORE_AVAILABLE:
        profile = SubscriberProfile(
            tenant_id=tenant_id,
            first_name=req.first_name or email.split("@")[0],
            last_name=req.last_name,
            email=email,
        )
        mgr = _get_tenant_manager(tenant_id)
        mgr.set_subscriber_profile(profile)

    token = _create_client_token(tenant_id, email, "essentiel")
    # Initialize gamification player
    if _GAMIFICATION_AVAILABLE and _redis_client:
        try:
            gops = GamificationRedisOps(_redis_client)
            asyncio.create_task(initialize_player_safe(gops, tenant_id))
        except Exception:
            pass
    _gamify("admin", "new_client", is_admin=True)
    logger.info(f"AUTH_REGISTER tenant_id={tenant_id} email={email}")
    return {"token": token, "tenant_id": tenant_id, "plan": "essentiel"}


@app.post("/api/auth/login")
async def auth_login(req: LoginRequest):
    """Connexion d'un client existant."""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    email = req.email.strip().lower()
    auth = _redis_client.get_auth_by_email(email)
    if not auth:
        return JSONResponse(status_code=401, content={"error": "Email ou mot de passe incorrect"})

    if not _verify_password(req.password, auth["password_hash"]):
        return JSONResponse(status_code=401, content={"error": "Email ou mot de passe incorrect"})

    if not auth.get("active", True):
        return JSONResponse(status_code=403, content={"error": "Compte desactive"})

    tenant_id = auth["tenant_id"]
    plan = auth.get("plan", "essentiel")

    # Recuperer le prenom depuis le profil
    first_name = ""
    if _redis_client:
        profile = _redis_client.get_profile(tenant_id)
        if profile:
            first_name = profile.get("first_name", "")

    token = _create_client_token(tenant_id, email, plan)
    _gamify(tenant_id, "daily_login")
    logger.info(f"AUTH_LOGIN tenant_id={tenant_id} email={email}")
    return {"token": token, "tenant_id": tenant_id, "plan": plan, "first_name": first_name}


@app.get("/api/auth/me")
async def auth_me(request: Request):
    """Profil du client connecte."""
    token = _extract_bearer(request)
    payload = _decode_client_token(token)
    if not payload:
        return JSONResponse(status_code=401, content={"error": "Token invalide"})

    tenant_id = payload["tenant_id"]
    email = payload["email"]
    plan = payload["plan"]

    first_name = ""
    last_name = ""
    if _redis_client:
        profile = _redis_client.get_profile(tenant_id)
        if profile:
            first_name = profile.get("first_name", "")
            last_name = profile.get("last_name", "")

    return {
        "tenant_id": tenant_id,
        "email": email,
        "plan": plan,
        "first_name": first_name,
        "last_name": last_name,
    }


@app.post("/api/auth/change-password")
async def auth_change_password(req: ChangePasswordRequest, request: Request):
    """Changement de mot de passe."""
    token = _extract_bearer(request)
    payload = _decode_client_token(token)
    if not payload:
        return JSONResponse(status_code=401, content={"error": "Token invalide"})

    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    email = payload["email"]
    auth = _redis_client.get_auth_by_email(email)
    if not auth:
        return JSONResponse(status_code=404, content={"error": "Compte introuvable"})

    if not _verify_password(req.old_password, auth["password_hash"]):
        return JSONResponse(status_code=401, content={"error": "Ancien mot de passe incorrect"})

    if len(req.new_password) < 6:
        return JSONResponse(status_code=400, content={"error": "Nouveau mot de passe trop court (min 6)"})

    new_hash = _hash_password(req.new_password)
    _redis_client.update_auth_record(email, {"password_hash": new_hash})
    logger.info(f"AUTH_CHANGE_PASSWORD tenant_id={payload['tenant_id']} email={email}")
    return {"ok": True}


@app.post("/api/auth/checkout")
async def auth_checkout(req: CheckoutRequest, request: Request):
    """Cree une session Stripe Checkout pour upgrade/souscription."""
    token = _extract_bearer(request)
    payload = _decode_client_token(token)
    if not payload:
        return JSONResponse(status_code=401, content={"error": "Token invalide"})

    plan = req.plan.lower()
    price_map = {
        "essentiel": os.getenv("STRIPE_PRICE_ESSENTIEL", ""),
        "confort": os.getenv("STRIPE_PRICE_CONFORT", ""),
        "premium": os.getenv("STRIPE_PRICE_PREMIUM", ""),
    }
    price_id = price_map.get(plan)
    if not price_id:
        return JSONResponse(status_code=400, content={"error": f"Plan invalide ou STRIPE_PRICE non configure: {plan}"})

    stripe_key = os.getenv("STRIPE_API_KEY", "")
    if not stripe_key:
        return JSONResponse(status_code=500, content={"error": "STRIPE_API_KEY non configure"})

    try:
        import stripe
        stripe.api_key = stripe_key
        # Determine URLs
        host = request.headers.get("host", "localhost:8888")
        scheme = "https"
        base_url = f"{scheme}://{host}"

        # Creer ou recuperer le customer Stripe avec metadata tenant_id
        tid = payload["tenant_id"]
        email = payload["email"]
        customer_id = None
        if _redis_client:
            rec = _redis_client.get_auth_by_email(email)
            if rec:
                customer_id = rec.get("stripe_customer_id", "")
        if not customer_id:
            customer = stripe.Customer.create(
                email=email,
                metadata={"tenant_id": str(tid), "yawatch": "true"},
            )
            customer_id = customer.id
            if _redis_client:
                _redis_client.update_auth_record(email, {"stripe_customer_id": customer_id})

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            metadata={
                "tenant_id": str(tid),
                "email": email,
                "plan": plan,
            },
            success_url=f"{base_url}/?checkout=success",
            cancel_url=f"{base_url}/?checkout=cancel",
        )
        logger.info(f"STRIPE_CHECKOUT tenant_id={payload['tenant_id']} plan={plan}")
        return {"checkout_url": session.url}
    except ImportError:
        return JSONResponse(status_code=500, content={"error": "Service de paiement non disponible"})
    except Exception as e:
        logger.error(f"Checkout error: {e}")
        return JSONResponse(status_code=500, content={"error": "Erreur lors du paiement. Reessaie."})


# =========================================================================
# STRIPE WEBHOOK (accessible en setup ET en production)
# =========================================================================

def _price_id_to_plan(price_id: str) -> str:
    """Mappe un Stripe price_id vers un nom de plan."""
    mapping = {
        os.getenv("STRIPE_PRICE_ESSENTIEL", ""): "essentiel",
        os.getenv("STRIPE_PRICE_CONFORT", ""): "confort",
        os.getenv("STRIPE_PRICE_PREMIUM", ""): "premium",
    }
    return mapping.get(price_id, "")

_stripe_webhook_received: dict = {}  # {timestamp, event_type, verified}

@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    """Recoit les webhooks Stripe avec verification de signature."""
    global _stripe_webhook_received
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    if not webhook_secret:
        return JSONResponse(status_code=500, content={"error": "STRIPE_WEBHOOK_SECRET non configure"})

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        import stripe
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        _stripe_webhook_received = {
            "timestamp": time.time(),
            "event_type": event["type"],
            "verified": True,
        }
        logger.info(f"Stripe webhook recu: {event['type']} (verifie)")

        event_type = event["type"]
        data = event.get("data", {}).get("object", {})

        # --- checkout.session.completed ---
        if event_type == "checkout.session.completed":
            metadata = data.get("metadata", {})
            email = metadata.get("email", "")
            plan = metadata.get("plan", "")
            tenant_id_str = metadata.get("tenant_id", "")
            if email and plan and _redis_client:
                _redis_client.update_auth_record(email, {
                    "plan": plan,
                    "active": True,
                    "stripe_customer_id": data.get("customer", ""),
                    "stripe_subscription_id": data.get("subscription", ""),
                })
                # Evict from tenant manager cache to reload with new plan
                tid = int(tenant_id_str) if tenant_id_str else 0
                if tid and tid in _tenant_managers:
                    del _tenant_managers[tid]
                logger.info(f"STRIPE_CHECKOUT_COMPLETE email={email} plan={plan} tenant_id={tenant_id_str}")

            # --- World premium item purchase ---
            if metadata.get("type") == "world_premium" and _redis_client:
                world_item_id = metadata.get("world_item_id", "")
                tenant_id_str = metadata.get("tenant_id", "")
                if world_item_id and tenant_id_str:
                    try:
                        from core.gamification.redis_ops import GamificationRedisOps
                        from core.gamification.constants import SHOP_ITEMS
                        gops = GamificationRedisOps(_redis_client)
                        tid = int(tenant_id_str)
                        item = SHOP_ITEMS.get(world_item_id)
                        if item:
                            from datetime import datetime as dt_import
                            gops.add_to_inventory(tid, world_item_id, {
                                "purchased_at": dt_import.utcnow().isoformat(),
                                "category": item["category"],
                                "stripe_payment": data.get("payment_intent", ""),
                            })
                            logger.info(f"WORLD_PREMIUM_PURCHASED tenant_id={tid} item={world_item_id}")
                    except Exception as e:
                        logger.error(f"Error delivering premium item: {e}")

        # --- customer.subscription.updated ---
        elif event_type == "customer.subscription.updated":
            # Map price_id back to plan name
            items = data.get("items", {}).get("data", [])
            if items and _redis_client:
                price_id = items[0].get("price", {}).get("id", "")
                plan = _price_id_to_plan(price_id)
                customer_id = data.get("customer", "")
                if plan and customer_id:
                    # Find auth record by stripe_customer_id
                    records = _redis_client.get_all_auth_records()
                    for rec in records:
                        if rec.get("stripe_customer_id") == customer_id:
                            _redis_client.update_auth_record(rec["email"], {"plan": plan})
                            tid = rec.get("tenant_id", 0)
                            if tid and tid in _tenant_managers:
                                del _tenant_managers[tid]
                            logger.info(f"STRIPE_SUB_UPDATED email={rec['email']} plan={plan}")
                            break

        # --- customer.subscription.deleted ---
        elif event_type == "customer.subscription.deleted":
            customer_id = data.get("customer", "")
            if customer_id and _redis_client:
                records = _redis_client.get_all_auth_records()
                for rec in records:
                    if rec.get("stripe_customer_id") == customer_id:
                        _redis_client.update_auth_record(rec["email"], {"active": False})
                        logger.info(f"STRIPE_SUB_DELETED email={rec['email']}")
                        break

        # --- invoice.payment_failed ---
        elif event_type == "invoice.payment_failed":
            customer_email = data.get("customer_email", "")
            logger.warning(f"STRIPE_PAYMENT_FAILED email={customer_email}")

        # --- invoice.payment_succeeded ---
        elif event_type == "invoice.payment_succeeded":
            customer_email = data.get("customer_email", "")
            amount = data.get("amount_paid", 0) / 100
            logger.info(f"STRIPE_PAYMENT_SUCCESS email={customer_email} amount={amount:.2f}EUR")

        # --- charge.refunded ---
        elif event_type == "charge.refunded":
            customer_email = data.get("billing_details", {}).get("email", "")
            amount = data.get("amount_refunded", 0) / 100
            logger.warning(f"STRIPE_REFUND email={customer_email} amount={amount:.2f}EUR")

        # --- customer.subscription.created ---
        elif event_type == "customer.subscription.created":
            customer_id = data.get("customer", "")
            items = data.get("items", {}).get("data", [])
            if items:
                price_id = items[0].get("price", {}).get("id", "")
                plan = _price_id_to_plan(price_id)
                logger.info(f"STRIPE_SUB_CREATED customer={customer_id} plan={plan}")

        return {"received": True}
    except ImportError:
        return JSONResponse(status_code=500, content={"error": "Service de paiement non disponible"})
    except Exception as e:
        logger.warning(f"Stripe webhook invalide: {e}")
        return JSONResponse(status_code=400, content={"error": f"Signature invalide: {e}"})


@app.get("/api/setup/stripe-webhook-status")
async def setup_stripe_webhook_status():
    """Retourne si un webhook Stripe a ete recu et verifie."""
    if not _stripe_webhook_received:
        return {"received": False, "message": "Aucun evenement de paiement recu. Envoyez un test depuis le tableau de bord."}
    return {
        "received": True,
        "verified": _stripe_webhook_received.get("verified", False),
        "event_type": _stripe_webhook_received.get("event_type", ""),
        "timestamp": _stripe_webhook_received.get("timestamp", 0),
    }


# =========================================================================
# SETUP ENDPOINTS (accessibles meme si PV non signe)
# =========================================================================

@app.get("/api/setup/status")
async def setup_status():
    """Etat du processus de setup et du PV de recette."""
    try:
        from pv_recette import PVRecette
        pv = PVRecette()
        return {
            "pv_signed": PV_SIGNED,
            "pv_locked": _pv_locked,
            "luna_mode": LUNA_MODE,
            "phases": {
                "A": "Verifications techniques (automatisees)",
                "B": "Verifications legales (declarations exploitant)",
                "C": "Verifications operationnelles",
            },
        }
    except ImportError:
        return {"error": "Module pv_recette non disponible", "pv_locked": _pv_locked}


@app.post("/api/setup/check-phase-a")
async def setup_check_phase_a():
    """Lance les verifications techniques automatiques (Phase A)."""
    try:
        from pv_recette import PVRecette
        pv = PVRecette()
        results = pv.check_phase_a()
        return {"phase": "A", "results": results}
    except ImportError:
        return JSONResponse(status_code=500, content={"error": "Module pv_recette non disponible"})


@app.post("/api/setup/check-phase-b")
async def setup_check_phase_b(request: Request):
    """Soumettre les declarations legales (Phase B)."""
    try:
        from pv_recette import PVRecette
        pv = PVRecette()
        data = await request.json()
        declarations = data.get("declarations", {})
        results = pv.validate_phase_b(declarations)
        return {"phase": "B", "results": results}
    except ImportError:
        return JSONResponse(status_code=500, content={"error": "Module pv_recette non disponible"})


@app.post("/api/setup/check-phase-c")
async def setup_check_phase_c():
    """Lance les verifications operationnelles (Phase C)."""
    try:
        from pv_recette import PVRecette
        pv = PVRecette()
        results = pv.check_phase_c()
        return {"phase": "C", "results": results}
    except ImportError:
        return JSONResponse(status_code=500, content={"error": "Module pv_recette non disponible"})


@app.post("/api/setup/check-siret")
async def setup_check_siret(request: Request):
    """Verifie un SIRET via l'API gouvernementale (gratuit, sans cle)."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"status": "fail", "message": "JSON invalide"})

    siret = str(body.get("siret", "")).strip().replace(" ", "")

    # Validation format
    if len(siret) != 14 or not siret.isdigit():
        return JSONResponse(content={"status": "fail", "message": "SIRET invalide (14 chiffres requis)"})

    # Appel API gouv.fr (gratuit, pas de cle)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://recherche-entreprises.api.gouv.fr/search?q={siret}&per_page=1",
                timeout=10.0,
            )
    except Exception as e:
        logger.warning(f"API INSEE indisponible: {e}")
        return JSONResponse(content={"status": "warn", "message": "Service INSEE indisponible, continuez manuellement"})

    if resp.status_code != 200:
        return JSONResponse(content={"status": "warn", "message": "Service INSEE indisponible, continuez manuellement"})

    data = resp.json()
    results = data.get("results", [])
    if not results:
        return JSONResponse(content={"status": "fail", "message": "SIRET introuvable dans le registre INSEE"})

    company = results[0]
    siege = company.get("siege", {})

    # Verifier que le SIRET retourne correspond bien a celui demande
    returned_siret = siege.get("siret", "")
    if returned_siret != siret:
        return JSONResponse(content={"status": "fail", "message": "SIRET introuvable dans le registre INSEE"})

    # Verifier que l'entreprise est active
    if company.get("etat_administratif") != "A":
        return JSONResponse(content={"status": "fail", "message": "Entreprise fermee ou radiee"})

    # Code APE — liste des codes compatibles avec l'exploitation Luna
    ape = company.get("activite_principale", "")
    ape_compatible_codes = [
        "62.01Z", "62.02A", "62.02B", "62.03Z", "62.09Z",  # Informatique
        "63.11Z", "63.12Z", "63.99Z",                       # Traitement donnees
        "58.29C", "58.29A",                                   # Edition logiciels
        "70.22Z", "74.90B",                                   # Conseil
        "85.59B", "88.10C", "88.99B",                        # Aide a la personne
        "47.41Z", "47.42Z",                                   # Commerce electronique
    ]

    return JSONResponse(content={
        "status": "ok",
        "company": {
            "nom": company.get("nom_complet", ""),
            "siren": company.get("siren", ""),
            "siret": siege.get("siret", siret),
            "adresse": siege.get("adresse", ""),
            "code_postal": siege.get("code_postal", ""),
            "commune": siege.get("libelle_commune", ""),
            "ape": ape,
            "ape_compatible": ape in ape_compatible_codes,
            "nature_juridique": company.get("nature_juridique", ""),
            "etat": company.get("etat_administratif", ""),
            "dirigeants": [
                {"nom": d.get("nom", ""), "prenoms": d.get("prenoms", ""), "qualite": d.get("qualite", "")}
                for d in company.get("dirigeants", [])[:3]
                if d.get("type_dirigeant") == "personne physique"
            ],
        },
        "message": "Entreprise verifiee",
    })


@app.post("/api/setup/sign-pv")
async def setup_sign_pv(request: Request):
    """Signe le PV de recette et deverrouille le serveur."""
    global PV_SIGNED, _pv_locked, _setup_permanently_disabled, SETUP_OPENAI_API_KEY
    global _setup_chat_history, _setup_message_count

    async with _sign_pv_lock:
        if _setup_permanently_disabled:
            return JSONResponse(status_code=410, content={
                "error": "Installation terminee",
                "message": "Le PV a deja ete signe. Impossible de re-signer.",
            })
        try:
            import json as _json_pv
            from pv_recette import PVRecette
            pv = PVRecette()
            data = await request.json()

            # Fallback: si exploitant_name/siret vides, lire depuis wizard_state.json
            exploitant_name = data.get("exploitant_name", "").strip()
            exploitant_siret = data.get("exploitant_siret", "").strip()
            if not exploitant_name or not exploitant_siret:
                ws_path = os.path.join(os.path.dirname(__file__), ".wizard_state.json")
                if os.path.exists(ws_path):
                    ws = _json_pv.loads(open(ws_path, encoding="utf-8").read())
                    ws_config = ws.get("config", {})
                    if not exploitant_name:
                        exploitant_name = ws_config.get("EXPLOITANT_NAME", "")
                    if not exploitant_siret:
                        exploitant_siret = ws_config.get("EXPLOITANT_SIRET", "")

            result = pv.sign(
                exploitant_name=exploitant_name,
                exploitant_siret=exploitant_siret,
                declarations_b=data.get("declarations", {}),
            )
            if "error" in result:
                return JSONResponse(status_code=400, content=result)

            # Mettre a jour le .env automatiquement
            env_path = os.path.join(os.path.dirname(__file__), ".env")
            pv.update_env_file(env_path, result["env_updates"])

            # Mise a jour des globals runtime (pas besoin de restart)
            PV_SIGNED = True
            _pv_locked = False
            _setup_permanently_disabled = True

            # Feature 1: Destruction cle fondateur
            SETUP_OPENAI_API_KEY = None
            _setup_chat_history.clear()
            _setup_message_count = _SETUP_MAX_MESSAGES

            # Feature 2: Generer le certificat d'autonomie
            cert_path = None
            reset_code = result.get("reset_code", "")
            try:
                cert_path = _generate_autonomy_certificate(result["pv_data"], reset_code)
            except Exception as e:
                logger.error(f"Erreur generation certificat: {e}")

            logger.info(f"PV signe — setup DESACTIVE, cle fondateur detruite")

            return {
                "success": True,
                "reset_code": reset_code,
                "certificate_url": "/api/admin/certificate" if cert_path else None,
                "message": "PV signe. CONSERVEZ le reset code. Telechargez le certificat.",
                "pv_data": result["pv_data"],
            }
        except ImportError:
            return JSONResponse(status_code=500, content={"error": "Module pv_recette non disponible"})


@app.get("/api/setup/phase-b-checklist")
async def setup_phase_b_checklist():
    """Retourne la checklist des declarations legales a remplir."""
    try:
        from pv_recette import PVRecette
        pv = PVRecette()
        return {"checklist": pv.get_phase_b_checklist()}
    except ImportError:
        return JSONResponse(status_code=500, content={"error": "Module pv_recette non disponible"})


# =========================================================================
# SETUP AI + WEB WIZARD ENDPOINTS
# =========================================================================

# Luna Setup AI state (in-memory, pas besoin de Redis en setup)
_setup_chat_history: list = []
_setup_message_count: int = 0
_SETUP_MAX_MESSAGES = 50

_SETUP_SYSTEM_PROMPT = """Tu es Luna Setup, l'assistante d'installation YAWatch Luna.
Tu guides un exploitant (potentiellement non-technicien) a travers la configuration.
Tu parles en francais, de maniere simple et encourageante.

CONTEXTE:
- L'exploitant configure une instance de Luna pour ses propres clients
- Il doit creer des comptes: OpenAI, Twilio, Stripe, optionnellement Tavus
- Chaque service a ses propres cles API a copier
- Apres la config, il y a un PV de recette en 3 phases (technique, legal, operationnel)

SERVICES:
- OpenAI: intelligence de Luna, cle commence par 'sk-', https://platform.openai.com
- Twilio: SMS, Account SID commence par 'AC', https://twilio.com
- Stripe: paiements, cle commence par 'sk_test_' ou 'sk_live_', https://stripe.com
- Tavus: visio avatar (mode Full seulement), https://tavus.io
- Redis: memoire cache, redis://localhost:6379/0

PLANS LUNA:
- Essentiel (79 EUR/mois): Chat illimite + 60 min voix + 20 min visio + 50 SMS
- Confort (149 EUR/mois): Chat illimite + 180 min voix + 60 min visio + 200 SMS
- Premium (249 EUR/mois): Chat illimite + 300 min voix + 180 min visio + 200 SMS

TROUBLESHOOTING COURANT:
- "cle ne fonctionne pas" -> verifier copier-coller, espaces en trop, cle expiree
- "Redis non connecte" -> sudo systemctl start redis-server ou docker run -d redis
- "SSL erreur" -> certificats auto-signes OK pour dev, Let's Encrypt pour prod
- "Stripe webhook" -> URL doit etre publique HTTPS, utiliser Stripe CLI en dev

REGLES:
- Sois patient et encourage
- Explique en langage simple, evite le jargon technique
- Si tu ne sais pas, dis-le et suggere de contacter le support YAWatch
- Ne donne JAMAIS de cles API, tokens ou secrets
- Ne modifie rien toi-meme, guide l'exploitant a le faire via l'interface

MODELE ECONOMIQUE 70/30:
- Le fondateur recoit 70% du CA brut TTC encaisse par l'exploitant
- L'exploitant conserve 30% brut
- Sur ces 30%, l'exploitant reverse 6% du CA brut a Ambre (communication) + 300 EUR fixe/mois
- Les couts API (OpenAI, Twilio, Tavus, Stripe) sont a la charge de l'exploitant sur ses 30%
- Budget API estime pour 100 clients: ~1 200 EUR/mois

CONSEILS ADMINISTRATIFS:
- RC Professionnelle obligatoire (minimum recommande: 500 000 EUR). Assureurs: Hiscox, AXA Pro, MMA Pro
- SIRET doit etre actif et le code APE compatible (informatique, conseil, aide a la personne)
- Hebergement serveur obligatoirement en UE (RGPD). Recommandes: OVH, Scaleway, Hetzner
- DPO necessaire si plus de 250 salaries ou traitement de donnees sensibles a grande echelle

AVERTISSEMENTS JURIDIQUES CRITIQUES:
- Luna n'est PAS un dispositif medical. Toute confusion = exercice illegal medecine (Art. L4161-1 CSP, 2 ans + 30K EUR)
- Detection de detresse = best-effort UNIQUEMENT. Promettre une garantie = mise en danger d'autrui (Art. 223-1 Code penal)
- Non-conformite RGPD = amende jusqu'a 20M EUR ou 4% du CA mondial (Art. 83 RGPD)
- Toujours recommander d'appeler le 15/112 avant tout, Luna ne remplace PAS les secours

HEBERGEMENT RECOMMANDE:
- OVH VPS (France): a partir de 6 EUR/mois, Docker compatible
- Scaleway (France): a partir de 8 EUR/mois, GPU optionnel
- Hetzner (Allemagne): a partir de 5 EUR/mois, excellent rapport qualite/prix
- AWS/GCP: OK si region eu-west-1 / europe-west1
"""


@app.post("/api/setup/ai-chat")
async def setup_ai_chat(request: Request):
    """Chat avec Luna Setup AI pendant la configuration."""
    global _setup_message_count

    if not SETUP_OPENAI_API_KEY:
        return JSONResponse(status_code=400, content={
            "error": "SETUP_OPENAI_API_KEY non configuree",
            "message": "Demandez une cle de setup a votre referent YAWatch.",
        })

    if _setup_message_count >= _SETUP_MAX_MESSAGES:
        return JSONResponse(status_code=429, content={
            "error": "Quota setup epuise",
            "message": f"Vous avez utilise vos {_SETUP_MAX_MESSAGES} messages. Contactez support@yawatch.fr.",
            "count": _setup_message_count,
            "max": _SETUP_MAX_MESSAGES,
        })

    data = await request.json()
    user_msg = data.get("message", "").strip()
    if not user_msg:
        return JSONResponse(status_code=400, content={"error": "Message vide"})

    _setup_chat_history.append({"role": "user", "content": user_msg})

    try:
        setup_client = OpenAI(api_key=SETUP_OPENAI_API_KEY)
        messages = [{"role": "system", "content": _SETUP_SYSTEM_PROMPT}] + _setup_chat_history[-20:]
        resp = setup_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=500,
            temperature=0.7,
        )
        assistant_msg = resp.choices[0].message.content
        _setup_chat_history.append({"role": "assistant", "content": assistant_msg})
        _setup_message_count += 1

        return {
            "response": assistant_msg,
            "count": _setup_message_count,
            "max": _SETUP_MAX_MESSAGES,
            "remaining": _SETUP_MAX_MESSAGES - _setup_message_count,
        }
    except Exception as e:
        logger.error(f"Setup AI error: {e}")
        return JSONResponse(status_code=500, content={
            "error": "Erreur Luna Setup",
            "message": str(e),
        })


@app.post("/api/setup/save-config")
async def setup_save_config(request: Request):
    """Sauvegarde une etape de configuration dans le .env."""
    import json as _json

    data = await request.json()
    step = data.get("step", "")
    config = data.get("config", {})

    # Phase B envoie des declarations sans config — ne pas rejeter
    if not config and step != "phase_b":
        return JSONResponse(status_code=400, content={"error": "Configuration vide"})

    env_path = os.path.join(os.path.dirname(__file__), ".env")

    # Bootstrap: creer .env minimal si inexistant
    if not os.path.exists(env_path):
        from pathlib import Path
        Path(env_path).write_text("PV_SIGNED=false\nLUNA_MODE=lite\n", encoding="utf-8")

    # Mettre a jour les cles dans .env
    try:
        from pv_recette import PVRecette
        pv = PVRecette()
        pv.update_env_file(env_path, config)
    except ImportError:
        # Fallback: ecriture directe
        from pathlib import Path
        content = Path(env_path).read_text(encoding="utf-8")
        for k, v in config.items():
            if f"{k}=" in content:
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if line.startswith(f"{k}="):
                        lines[i] = f"{k}={v}"
                        break
                content = "\n".join(lines)
            else:
                content += f"\n{k}={v}"
        Path(env_path).write_text(content, encoding="utf-8")

    # Recharger le .env dans le processus pour que os.getenv() retourne les nouvelles valeurs
    _reload_env()

    # Sauvegarder l'etat du wizard
    state_path = os.path.join(os.path.dirname(__file__), ".wizard_state.json")
    state = {}
    if os.path.exists(state_path):
        state = _json.loads(open(state_path, encoding="utf-8").read())
    state.setdefault("completed_steps", [])
    if step and step not in state["completed_steps"]:
        state["completed_steps"].append(step)
    state["config"] = {**state.get("config", {}), **config}
    state["saved_at"] = datetime.now().isoformat()

    # Sauvegarder les declarations Phase B dans le wizard state
    if step == "phase_b":
        declarations = data.get("phase_b_declarations", data.get("declarations", data.get("config", {})))
        state["phase_b_declarations"] = declarations

    with open(state_path, "w", encoding="utf-8") as f:
        _json.dump(state, f, indent=2, ensure_ascii=False)

    return {"success": True, "step": step, "saved_keys": list(config.keys())}


@app.get("/api/setup/wizard-state")
async def setup_wizard_state():
    """Retourne l'etat du wizard pour reprendre."""
    import json as _json

    state_path = os.path.join(os.path.dirname(__file__), ".wizard_state.json")
    if os.path.exists(state_path):
        state = _json.loads(open(state_path, encoding="utf-8").read())
        # Masquer les valeurs sensibles
        safe_config = {}
        for k, v in state.get("config", {}).items():
            if isinstance(v, str) and any(s in k.upper() for s in ["KEY", "TOKEN", "SECRET", "PASSWORD"]):
                safe_config[k] = ("***" + v[-4:]) if len(v) > 4 else "****"
            else:
                safe_config[k] = v
        state["config"] = safe_config
        # Inclure les declarations Phase B si presentes
        if "phase_b_declarations" not in state:
            state["phase_b_declarations"] = {}
        return state
    return {"completed_steps": [], "config": {}, "phase_b_declarations": {}}


@app.post("/api/setup/test-service")
async def setup_test_service(request: Request):
    """Teste un service specifique avec les credentials fournis."""
    data = await request.json()
    service = data.get("service", "")
    creds = data.get("credentials", {})

    try:
        from pv_recette import PVRecette
        pv = PVRecette()

        if hasattr(pv, "test_service"):
            result = pv.test_service(service, creds)
        else:
            # Fallback: utiliser les checks existants (depuis env vars)
            check_map = {
                "openai": pv._check_openai,
                "twilio": pv._check_twilio,
                "stripe": pv._check_stripe,
                "redis": pv._check_redis,
                "tavus": pv._check_tavus,
            }
            if service not in check_map:
                return JSONResponse(status_code=400, content={"error": f"Service inconnu: {service}"})
            result = check_map[service]()

        return {"service": service, "result": result}
    except ImportError:
        return JSONResponse(status_code=500, content={"error": "Module pv_recette non disponible"})


@app.post("/api/setup/generate-security")
async def setup_generate_security():
    """Genere JWT secret et certificats SSL automatiquement."""
    import secrets as _secrets
    import subprocess

    results = {}

    # JWT
    jwt_key = _secrets.token_hex(32)
    results["jwt"] = {"status": "ok", "message": f"Cle JWT generee ({len(jwt_key)} chars)"}

    # SSL
    ssl_dir = os.path.dirname(__file__)
    cert_path = os.path.join(ssl_dir, "cert.pem")
    key_path = os.path.join(ssl_dir, "key.pem")

    if os.path.exists(cert_path) and os.path.exists(key_path):
        results["ssl"] = {"status": "ok", "message": "Certificats SSL deja presents"}
    else:
        try:
            subprocess.run([
                "openssl", "req", "-x509", "-newkey", "rsa:4096",
                "-keyout", key_path, "-out", cert_path,
                "-days", "365", "-nodes",
                "-subj", "/CN=localhost/O=YAWatch-Luna",
            ], check=True, capture_output=True)
            results["ssl"] = {"status": "ok", "message": "Certificats SSL generes (1 an)"}
        except Exception as e:
            results["ssl"] = {"status": "fail", "message": f"Erreur SSL: {e}"}

    # Sauvegarder dans .env
    env_path = os.path.join(ssl_dir, ".env")
    config_updates = {
        "JWT_SECRET_KEY": jwt_key,
        "JWT_ALGORITHM": "HS256",
        "SSL_CERTFILE": "./cert.pem",
        "SSL_KEYFILE": "./key.pem",
    }
    try:
        from pv_recette import PVRecette
        pv = PVRecette()
        pv.update_env_file(env_path, config_updates)
    except ImportError:
        pass

    return {"success": True, "results": results, "saved_keys": list(config_updates.keys())}


@app.post("/api/setup/stripe-auto")
async def setup_stripe_auto(request: Request):
    """Cree automatiquement les 3 produits Stripe."""
    data = await request.json()
    stripe_key = data.get("stripe_api_key", "")
    if not stripe_key:
        return JSONResponse(status_code=400, content={"error": "STRIPE_API_KEY requis"})

    try:
        import stripe
        stripe.api_key = stripe_key
        from stripe_setup import create_products_and_prices
        results = create_products_and_prices(stripe)
        return {"success": True, "prices": results}
    except ImportError as e:
        logger.error(f"Stripe setup import error: {e}")
        return JSONResponse(status_code=500, content={"error": "Service de paiement non disponible"})
    except Exception as e:
        logger.error(f"Stripe setup error: {e}")
        return JSONResponse(status_code=500, content={"error": "Erreur de configuration des paiements."})


# =========================================================================
# PROFILE ENDPOINTS
# =========================================================================

@app.get("/api/profile")
async def get_profile(request: Request):
    """Retourne le profil souscripteur"""
    tid = getattr(request.state, "tenant_id", 1)
    mgr = _get_tenant_manager(tid)
    if not mgr:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    profile = mgr.get_subscriber_profile()
    if not profile:
        return {"profile": None}
    return {"profile": profile.model_dump()}


@app.post("/api/profile")
async def set_profile(req: ProfileRequest, request: Request):
    """Cree ou remplace le profil souscripteur"""
    tid = getattr(request.state, "tenant_id", 1)
    mgr = _get_tenant_manager(tid)
    if not mgr:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    profile = SubscriberProfile(tenant_id=tid, **req.model_dump())
    mgr.set_subscriber_profile(profile)
    _gamify(tid, "profile_update")
    return {"success": True, "profile": profile.model_dump()}


@app.patch("/api/profile")
async def update_profile(request: Request):
    """Mise a jour partielle du profil"""
    tid = getattr(request.state, "tenant_id", 1)
    mgr = _get_tenant_manager(tid)
    if not mgr:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    body = await request.json()
    if not body:
        return JSONResponse(status_code=400, content={"error": "Corps vide"})
    profile = mgr.update_subscriber_profile(body)
    if not profile:
        return JSONResponse(status_code=404, content={"error": "Profil non trouve"})
    _gamify(tid, "profile_update")
    return {"success": True, "profile": profile.model_dump()}


# =========================================================================
# NOTIFICATIONS & SETTINGS ENDPOINTS
# =========================================================================

@app.get("/api/notifications/prefs")
async def get_notification_prefs(request: Request):
    """Get notification preferences for the current user."""
    tid = getattr(request.state, "tenant_id", 1)
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service indisponible"})
    from core.notifications.redis_ops import NotificationRedisOps
    nops = NotificationRedisOps(_redis_client)
    prefs = nops.get_prefs(tid)
    return {"prefs": prefs}


@app.post("/api/notifications/prefs")
async def set_notification_prefs(request: Request):
    """Update notification preferences."""
    tid = getattr(request.state, "tenant_id", 1)
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service indisponible"})
    body = await request.json()
    from core.notifications.redis_ops import NotificationRedisOps
    nops = NotificationRedisOps(_redis_client)
    allowed_fields = {
        "enabled", "streak_risk", "comeback", "mission_reminder",
        "level_up", "weekly_summary", "sound",
        "quiet_hours_start", "quiet_hours_end",
    }
    for k, v in body.items():
        if k in allowed_fields:
            nops.update_pref(tid, k, str(v))
    return {"success": True, "prefs": nops.get_prefs(tid)}


@app.get("/api/notifications/pending")
async def get_pending_notifications(request: Request):
    """Poll for pending notifications. Returns up to 5 and removes them."""
    tid = getattr(request.state, "tenant_id", 1)
    if not _redis_client:
        return {"notifications": []}
    from core.notifications.redis_ops import NotificationRedisOps
    nops = NotificationRedisOps(_redis_client)
    pending = nops.pop_pending(tid, limit=5)
    return {"notifications": pending}


@app.get("/api/notifications/count")
async def get_notification_count(request: Request):
    """Returns count of pending notifications (for badge display)."""
    tid = getattr(request.state, "tenant_id", 1)
    if not _redis_client:
        return {"count": 0}
    from core.notifications.redis_ops import NotificationRedisOps
    nops = NotificationRedisOps(_redis_client)
    return {"count": nops.peek_pending(tid)}


@app.get("/api/settings")
async def get_settings(request: Request):
    """Get all user settings (appearance, sound, etc.)."""
    tid = getattr(request.state, "tenant_id", 1)
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service indisponible"})
    key = _redis_client._key(tid, "settings")
    data = _redis_client.client.hgetall(key)
    defaults = {
        "dark_mode": "1",
        "font_size": "normal",
        "language": "fr",
        "notification_sound": "1",
    }
    defaults.update(data)
    return {"settings": defaults}


@app.post("/api/settings")
async def update_settings(request: Request):
    """Update user settings."""
    tid = getattr(request.state, "tenant_id", 1)
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service indisponible"})
    body = await request.json()
    allowed = {"dark_mode", "font_size", "language", "notification_sound"}
    updates = {k: str(v) for k, v in body.items() if k in allowed}
    if updates:
        key = _redis_client._key(tid, "settings")
        _redis_client.client.hset(key, mapping=updates)
    return {"success": True}


# =========================================================================
# CONTACTS ENDPOINTS
# =========================================================================

_MAX_CONTACTS_PROPRIO = 30
_MAX_CONTACTS_DEFAULT = 5

def _get_max_contacts(tid: int) -> int:
    return _MAX_CONTACTS_PROPRIO if tid == _PROPRIO_TENANT_ID else _MAX_CONTACTS_DEFAULT

@app.get("/api/contacts")
async def list_contacts(request: Request):
    """Liste les contacts de confiance"""
    tid = getattr(request.state, "tenant_id", 1)
    mgr = _get_tenant_manager(tid)
    if not mgr:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    contacts = mgr.list_trusted_contacts()
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
        "max": _get_max_contacts(tid),
    }


@app.post("/api/contacts")
async def add_contact(req: ContactRequest, request: Request):
    """Ajoute un contact de confiance (max 5)"""
    tid = getattr(request.state, "tenant_id", 1)
    mgr = _get_tenant_manager(tid)
    if not mgr:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    try:
        channel = Channel(req.preferred_channel) if req.preferred_channel in [c.value for c in Channel] else Channel.SMS
        contact = mgr.add_trusted_contact(
            phone=req.phone,
            name=req.name,
            relation=req.relation,
            preferred_channel=channel,
            emergency_only=req.emergency_only,
        )
        _gamify(tid, "add_contact")
        return {"success": True, "contact": {
            "phone": contact.phone,
            "name": contact.name,
            "relation": contact.relation,
        }}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@app.delete("/api/contacts/{phone}")
async def delete_contact(phone: str, request: Request):
    """Supprime un contact de confiance"""
    tid = getattr(request.state, "tenant_id", 1)
    mgr = _get_tenant_manager(tid)
    if not mgr:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    removed = mgr.remove_trusted_contact(phone)
    if not removed:
        return JSONResponse(status_code=404, content={"error": "Contact introuvable"})
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
                      details: dict = None, severity: str = "info",
                      tenant_id: int = None):
    """Log une action dans l'audit famille"""
    if not _redis_client:
        return
    tid = tenant_id if tenant_id is not None else TENANT_ID
    import json
    from datetime import datetime
    audit = FamilyAuditLog(
        tenant_id=tid,
        actor_phone=actor_phone,
        actor_name=actor_name,
        action=action,
        target_phone=target_phone,
        target_name=target_name,
        details=details or {},
        severity=severity,
    )
    _redis_client.add_family_audit(tid, json.dumps(audit.to_redis()))


# --- Family Group ---

@app.get("/api/family")
async def get_family(request: Request):
    """Recupere le groupe familial et ses membres"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)

    group_data = _redis_client.get_family_group(tid)
    if not group_data:
        return {"group": None, "members": [], "count": 0}

    group = FamilyGroup.from_redis(group_data)
    members = []
    for phone in _redis_client.get_family_members(tid):
        member_data = _redis_client.get_family_member(tid, phone)
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
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)
    data = await request.json()
    from datetime import datetime

    # Verifier si groupe existe deja
    existing = _redis_client.get_family_group(tid)
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
            tenant_id=tid,
            name=data.get("name", "Ma famille"),
            description=data.get("description", ""),
        )

    _redis_client.set_family_group(tid, group.to_redis())
    _log_family_audit("family_group_created" if not existing else "family_group_updated",
                      "system", "Luna", details={"name": group.name}, tenant_id=tid)

    if not existing:
        _gamify(tid, "family_setup")

    return {"success": True, "group_id": group.id}


# --- Family Members ---

@app.get("/api/family/members")
async def list_family_members(request: Request):
    """Liste tous les membres de la famille"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)

    members = []
    for phone in _redis_client.get_family_members(tid):
        member_data = _redis_client.get_family_member(tid, phone)
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
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)
    data = await request.json()

    # Validation
    phone = data.get("phone", "").strip()
    name = data.get("name", "").strip()
    relation = data.get("relation", "").strip()

    if not phone or not name:
        return JSONResponse(status_code=400, content={"error": "phone et name requis"})

    # Verifier si deja membre
    if _redis_client.get_family_member(tid, phone):
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
        tenant_id=tid,
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
    success = _redis_client.add_family_member(tid, phone, member.to_redis())
    if not success:
        return JSONResponse(status_code=400, content={"error": "Quota de membres atteint (max 15)"})

    # Envoyer SMS avec OTP
    sms_sent = False
    if sms_client:
        message = f"Luna Family: {name}, votre code de verification est {otp}. Valide 10 min."
        sms_sent, _ = _tracked_sms_send(phone, message, label=f"OTP famille {name}")

    _log_family_audit("member_invited", "system", "Luna",
                      target_phone=phone, target_name=name,
                      details={"role": member.role.value, "sms_sent": sms_sent},
                      tenant_id=tid)

    _gamify(tid, "family_member_added")

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
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)
    data = await request.json()
    otp = data.get("code", "").strip()

    if not otp:
        return JSONResponse(status_code=400, content={"error": "Code requis"})

    # Verifier OTP
    if not _redis_client.verify_otp(phone, otp):
        return JSONResponse(status_code=400, content={"error": "Code invalide ou expire"})

    # Marquer comme verifie
    from datetime import datetime
    _redis_client.update_family_member(tid, phone, {
        "is_verified": "1",
        "verified_at": datetime.utcnow().isoformat(),
        "verification_code": "",
    })

    member_data = _redis_client.get_family_member(tid, phone)
    name = member_data.get("name", "Membre") if member_data else "Membre"

    _log_family_audit("member_verified", phone, name, tenant_id=tid)

    _gamify(tid, "family_member_verified")

    return {"success": True, "message": f"{name} verifie avec succes"}


@app.patch("/api/family/members/{phone}")
async def update_family_member(phone: str, request: Request):
    """Met a jour un membre de la famille"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)
    data = await request.json()

    member_data = _redis_client.get_family_member(tid, phone)
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

    _redis_client.update_family_member(tid, phone, updates)

    _log_family_audit("member_updated", "system", "Luna",
                      target_phone=phone, target_name=member_data.get("name"),
                      details=updates, tenant_id=tid)

    return {"success": True}


@app.delete("/api/family/members/{phone}")
async def remove_family_member(phone: str, request: Request):
    """Supprime un membre de la famille"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)

    member_data = _redis_client.get_family_member(tid, phone)
    if not member_data:
        return JSONResponse(status_code=404, content={"error": "Membre non trouve"})

    name = member_data.get("name", "Membre")
    _redis_client.remove_family_member(tid, phone)

    _log_family_audit("member_removed", "system", "Luna",
                      target_phone=phone, target_name=name, tenant_id=tid)

    return {"success": True}


# --- Family Messages (Internal Messaging) ---

@app.get("/api/family/messages")
async def get_family_messages(request: Request, limit: int = 50, phone: str = None):
    """Recupere les messages famille (optionnel: filtre par destinataire)"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)

    messages = []
    for msg_id in _redis_client.get_family_messages(tid, limit=limit):
        msg_data = _redis_client.get_family_message(tid, msg_id)
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
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)
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
        tenant_id=tid,
        from_phone=from_phone,
        from_name=from_name,
        to_phone=to_phone,
        to_name=data.get("to_name"),
        content=content,
        message_type=FamilyMessageType(message_type),
        requires_response=data.get("requires_response", False),
    )

    _redis_client.add_family_message(tid, msg.id, msg.to_redis())

    # Notifier les destinataires (push ou SMS selon config)
    notified = []
    if to_phone:
        # Message direct
        member_data = _redis_client.get_family_member(tid, to_phone)
        if member_data and member_data.get("can_receive_alerts") == "1":
            notified.append(to_phone)
    else:
        # Message groupe - notifier tous les membres actifs
        for phone in _redis_client.get_family_members(tid):
            if phone != from_phone:  # Ne pas notifier l'expediteur
                member_data = _redis_client.get_family_member(tid, phone)
                if member_data and member_data.get("is_active") == "1":
                    notified.append(phone)

    _log_family_audit("message_sent", from_phone, from_name,
                      target_phone=to_phone,
                      details={"type": message_type, "notified": len(notified)},
                      tenant_id=tid)

    _gamify(tid, "family_message_sent")

    return {
        "success": True,
        "message_id": msg.id,
        "notified_count": len(notified),
    }


@app.post("/api/family/messages/{msg_id}/read")
async def mark_message_read(msg_id: str, request: Request):
    """Marque un message comme lu par un membre"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)
    data = await request.json()
    phone = data.get("phone", "") or data.get("reader_phone", "")
    phone = phone.strip() if phone else ""

    if not phone:
        return JSONResponse(status_code=400, content={"error": "phone requis"})

    msg_data = _redis_client.get_family_message(tid, msg_id)
    if not msg_data:
        return JSONResponse(status_code=404, content={"error": "Message non trouve"})

    import json
    from datetime import datetime
    read_by = json.loads(msg_data.get("read_by", "[]"))
    if phone not in read_by:
        read_by.append(phone)
        _redis_client.update_family_message(tid, msg_id, {
            "read_by": json.dumps(read_by),
            "is_read": "1" if len(read_by) > 0 else "0",
            "read_at": datetime.utcnow().isoformat(),
        })

    return {"success": True}


# --- Escalation Rules ---

@app.get("/api/family/escalation")
async def get_escalation_rules(request: Request):
    """Recupere les regles d'escalade"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)

    rules = []
    for rule_id in _redis_client.get_escalation_rules(tid):
        rule_data = _redis_client.get_escalation_rule(tid, rule_id)
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
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)
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
        tenant_id=tid,
        name=data.get("name", "Regle d'escalade"),
        description=data.get("description", ""),
        trigger_distress_level=DistressLevel(data.get("trigger_distress_level", "high")),
        trigger_member_types=[FamilyMemberType(t) for t in data.get("trigger_member_types", [])],
        trigger_keywords=data.get("trigger_keywords", []),
        stages=stages,
        enabled=data.get("enabled", True),
    )

    _redis_client.add_escalation_rule(tid, rule.id, rule.to_redis())

    _log_family_audit("escalation_rule_created", "system", "Luna",
                      details={"name": rule.name, "stages": len(stages)},
                      tenant_id=tid)

    _gamify(tid, "escalation_rule_created")

    return {"success": True, "rule_id": rule.id}


@app.delete("/api/family/escalation/{rule_id}")
async def delete_escalation_rule(rule_id: str, request: Request):
    """Supprime une regle d'escalade"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)

    _redis_client.delete_escalation_rule(tid, rule_id)

    _log_family_audit("escalation_rule_deleted", "system", "Luna",
                      details={"rule_id": rule_id}, tenant_id=tid)

    return {"success": True}


# --- Distress Detection (for Family Pack) ---

@app.post("/api/family/detect-distress")
async def detect_distress(request: Request):
    """Analyse un texte pour detecter la detresse (ados/enfants)"""
    tid = getattr(request.state, "tenant_id", 1)
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
        member_data = _redis_client.get_family_member(tid, from_phone) if _redis_client else None
        if member_data:
            member_name = member_data.get("name", "Membre")
            result["escalation_triggered"] = True
            result["message"] = f"Alerte detresse detectee pour {member_name}"

            # Log et notifier
            _log_family_audit("distress_detected", from_phone, member_name,
                              details={"level": level.value, "category": category},
                              severity="critical" if level == DistressLevel.CRITICAL else "alert",
                              tenant_id=tid)

    return result


# --- Family Audit Log ---

@app.get("/api/family/audit")
async def get_family_audit(request: Request, limit: int = 50):
    """Recupere le journal d'audit famille"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)

    import json
    entries = []
    for entry_json in _redis_client.get_family_audit(tid, limit=limit):
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
        except Exception as e:
            logger.warning(f"Audit entry parse error: {e}")

    return {"entries": entries, "count": len(entries)}


# --- Default Escalation Rule for Teens (Bullying/Distress) ---

@app.post("/api/family/setup-teen-protection")
async def setup_teen_protection(request: Request):
    """Configure automatiquement la protection ados (harcelement, detresse)"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)

    # Creer un groupe famille si pas existant
    if not _redis_client.get_family_group(tid):
        group = FamilyGroup(tenant_id=tid, name="Ma famille")
        _redis_client.set_family_group(tid, group.to_redis())

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
        tenant_id=tid,
        name="Protection ados - harcelement/detresse",
        description="Detection automatique du harcelement et de la detresse chez les adolescents",
        trigger_distress_level=DistressLevel.MEDIUM,
        trigger_member_types=[FamilyMemberType.TEEN, FamilyMemberType.CHILD],
        stages=stages,
        enabled=True,
    )

    _redis_client.add_escalation_rule(tid, rule.id, rule.to_redis())

    _log_family_audit("teen_protection_enabled", "system", "Luna",
                      details={"rule_id": rule.id}, tenant_id=tid)

    return {
        "success": True,
        "rule_id": rule.id,
        "message": "Protection ados configuree avec succes. Luna va maintenant detecter les signes de harcelement et de detresse.",
    }


# --- SOS Famille ---

@app.post("/api/family/sos")
async def family_sos(request: Request):
    """
    Bouton SOS famille - Alerte tous les membres de la famille.
    N'appelle PAS les services d'urgence (interdit).
    """
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)
    data = await request.json()
    from_phone = data.get("from_phone", "").strip()
    message = data.get("message", "").strip() or "J'ai besoin d'aide!"
    location = data.get("location")  # {lat, lng, address} optionnel
    trigger_visio = data.get("trigger_visio", False)

    if not from_phone:
        return JSONResponse(status_code=400, content={"error": "from_phone requis"})

    # Trouver le membre qui déclenche
    sender = _redis_client.get_family_member(tid, from_phone)
    sender_name = sender.get("name", "Un membre") if sender else "Un membre"

    # Récupérer tous les membres de la famille (sauf l'émetteur)
    all_members = _redis_client.get_all_family_members(tid)
    recipients = [m for m in all_members if m.get("phone") != from_phone]

    if not recipients:
        return JSONResponse(status_code=400, content={"error": "Aucun autre membre dans la famille"})

    # Construire le message SOS
    timestamp = datetime.utcnow().strftime("%H:%M")
    sos_message = f"🆘 ALERTE FAMILLE - {timestamp}\n\n"
    sos_message += f"{sender_name} a besoin d'aide!\n"
    if message != "J'ai besoin d'aide!":
        sos_message += f"Message: {message}\n"
    if location:
        if location.get("address"):
            sos_message += f"📍 {location['address']}\n"
        elif location.get("lat") and location.get("lng"):
            sos_message += f"📍 Position: {location['lat']}, {location['lng']}\n"

    # Créer un message prioritaire dans la messagerie interne
    from core.memory.schemas import FamilyMessage, FamilyMessageType
    sos_msg = FamilyMessage(
        tenant_id=tid,
        from_phone=from_phone,
        from_name=sender_name,
        to_phone="all",  # Broadcast
        content=sos_message,
        message_type=FamilyMessageType.ALERT,
        requires_response=True,
    )
    _redis_client.add_family_message(tid, sos_msg.id, sos_msg.to_redis())

    # Notifier par SMS les membres qui peuvent recevoir des alertes
    sms_sent = 0
    sms_failed = 0
    if sms_client and sms_client.is_configured:
        for member in recipients:
            if member.get("can_receive_alerts") in ["1", "true", True]:
                phone = member.get("phone")
                if phone:
                    success, _ = _tracked_sms_send(phone, sos_message, label=f"Alerte SOS")
                    if success:
                        sms_sent += 1
                    else:
                        sms_failed += 1

    # Publier événement temps réel pour l'app
    _redis_client.publish_event(tid, "sos_alert", {
        "from_phone": from_phone,
        "from_name": sender_name,
        "message": message,
        "location": location,
        "timestamp": datetime.utcnow().isoformat(),
    })

    # Log dans l'audit
    _log_family_audit("sos_triggered", from_phone, sender_name,
                      details={
                          "message": message,
                          "location": location,
                          "recipients_count": len(recipients),
                          "sms_sent": sms_sent,
                      },
                      severity="critical",
                      tenant_id=tid)

    _gamify(tid, "family_sos")

    # Optionnel: déclencher une visio avec Luna
    visio_url = None
    if trigger_visio and tavus_client and tavus_client.is_configured:
        context = f"ALERTE SOS de {sender_name}. Message: {message}"
        success, conv_data = await tavus_client.create_conversation(
            tenant_id=tid,
            custom_greeting=f"{sender_name}, je suis là. Dis-moi ce qui se passe.",
            context=context,
        )
        if success:
            visio_url = conv_data.get("conversation_url")

    return {
        "success": True,
        "message_id": sos_msg.id,
        "alerted_members": len(recipients),
        "sms_sent": sms_sent,
        "sms_failed": sms_failed,
        "visio_url": visio_url,
        "message": f"Alerte envoyee a {len(recipients)} membre(s) de la famille",
    }


@app.get("/api/family/sos/status")
async def family_sos_status(request: Request):
    """Vérifie si le SOS est disponible et récupère les dernières alertes"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)

    # Récupérer les alertes récentes depuis l'audit (les entrées sont des JSON strings)
    import json
    audit_entries_raw = _redis_client.get_family_audit(tid, limit=20)
    recent_sos = []
    for entry_str in audit_entries_raw:
        try:
            entry = json.loads(entry_str)
            if entry.get("action") == "sos_triggered":
                recent_sos.append(entry)
        except (json.JSONDecodeError, TypeError):
            continue

    # Compter les membres qui peuvent recevoir des alertes
    all_members = _redis_client.get_all_family_members(tid)
    alert_receivers = len([m for m in all_members if m.get("can_receive_alerts") in ["1", "true", True]])

    return {
        "available": True,
        "sms_enabled": sms_client.is_configured if sms_client else False,
        "visio_enabled": tavus_client.is_configured if tavus_client else False,
        "members_count": len(all_members),
        "alert_receivers": alert_receivers,
        "recent_alerts": recent_sos[:5],
    }


# =========================================================================
# INSTRUCTIONS ENDPOINTS
# =========================================================================

@app.get("/api/instructions")
async def list_instructions(request: Request):
    """Liste les instructions actives"""
    tid = getattr(request.state, "tenant_id", 1)
    mgr = _get_tenant_manager(tid)
    if not mgr:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    instructions = mgr.list_active_instructions()
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
async def create_instruction(req: InstructionRequest, request: Request):
    """Cree une instruction a partir de texte naturel (francais)"""
    tid = getattr(request.state, "tenant_id", 1)
    mgr = _get_tenant_manager(tid)
    if not mgr:
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
            "visio_contact": SchemaActionType.VISIO,
            "wake_up": SchemaActionType.CALL,
            "check_in": SchemaActionType.REMINDER,
            "surveillance": SchemaActionType.ALERT,
            "note": SchemaActionType.NOTE,
            "daily_routine": SchemaActionType.REMINDER,
            "information": SchemaActionType.REMINDER,
            "reading": SchemaActionType.REMINDER,
            "game": SchemaActionType.REMINDER,
            "music": SchemaActionType.REMINDER,
            "gratitude": SchemaActionType.REMINDER,
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

        instr = mgr.add_instruction(
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
                    tenant_id=tid,
                    instruction=parsed,
                )
            except Exception as e:
                logger.warning(f"Scheduler schedule failed: {e}")

        # Confirmation text
        confirmation = InstructionParser.format_confirmation(parsed)

        _gamify(tid, "create_instruction")
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
async def delete_instruction(instr_id: str, request: Request):
    """Desactive une instruction"""
    tid = getattr(request.state, "tenant_id", 1)
    mgr = _get_tenant_manager(tid)
    if not mgr:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    mgr.disable_instruction(instr_id)
    return {"success": True}


@app.post("/api/instructions/{instr_id}/execute")
async def execute_instruction(instr_id: str, request: Request):
    """Execute immediatement une instruction"""
    tid = getattr(request.state, "tenant_id", 1)
    mgr = _get_tenant_manager(tid)
    if not mgr:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    instr = mgr.get_instruction(instr_id)
    if not instr:
        return JSONResponse(status_code=404, content={"error": "Instruction non trouvee"})

    # Executer reellement l'instruction via l'executor
    if _executor and _CORE_AVAILABLE:
        try:
            task = ScheduledTask(
                scheduled_at=datetime.utcnow(),
                instruction_id=instr_id,
                tenant_id=tid,
                instruction=instr,
            )
            result = await _executor.execute(task)
            mgr.mark_instruction_executed(instr_id)
            return {
                "success": result.success if hasattr(result, "success") else True,
                "message": f"Instruction '{instr.description[:50]}' executee",
                "result": str(result) if result else None,
            }
        except Exception as e:
            logger.error(f"Instruction execution error: {e}")
            return JSONResponse(status_code=500, content={"error": f"Erreur execution: {str(e)}"})
    else:
        # Fallback: marquer comme executee sans executor
        mgr.mark_instruction_executed(instr_id)
        return {"success": True, "message": f"Instruction '{instr.description[:50]}' marquee executee (executor non disponible)"}


# =========================================================================
# NOTES ENDPOINTS
# =========================================================================

@app.get("/api/notes")
async def list_notes(request: Request, limit: int = 50):
    """Liste les notes recentes"""
    tid = getattr(request.state, "tenant_id", 1)
    mgr = _get_tenant_manager(tid)
    if not mgr:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    notes = mgr.list_notes(limit=min(limit, 200))
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
async def add_note(req: NoteRequest, request: Request):
    """Ajoute une note"""
    tid = getattr(request.state, "tenant_id", 1)
    mgr = _get_tenant_manager(tid)
    if not mgr:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    try:
        note = mgr.add_note(
            content=req.content,
            context=req.context,
            tags=req.tags,
        )
        _gamify(tid, "create_note")
        return {"success": True, "note": {"id": note.id, "content": note.content}}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


# =========================================================================
# EVENT LOG ENDPOINTS
# =========================================================================

@app.get("/api/events")
async def get_events(request: Request, limit: int = 50, offset: int = 0):
    """Retourne le journal d'evenements chronologique."""
    tid = getattr(request.state, "tenant_id", 1)
    mgr = _get_tenant_manager(tid)
    if not mgr:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    try:
        events = mgr.get_event_log(limit=min(limit, 200), offset=offset)
        return {"events": events, "count": len(events)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/events/export")
async def export_events(request: Request, limit: int = 200):
    """Exporte le journal d'evenements en texte brut."""
    tid = getattr(request.state, "tenant_id", 1)
    mgr = _get_tenant_manager(tid)
    if not mgr:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    try:
        events = mgr.get_event_log(limit=min(limit, 500))
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

# Limites par plan (par mois) — source unique depuis quota_guard
try:
    from core.actions.quota_guard import PLAN_SMS_LIMITS, PLAN_VOICE_LIMITS, PLAN_VISIO_LIMITS, PlanType
    _PLAN_LIMITS = {
        "essentiel": {"sms": PLAN_SMS_LIMITS[PlanType.ESSENTIEL], "voice_min": PLAN_VOICE_LIMITS[PlanType.ESSENTIEL], "visio_min": PLAN_VISIO_LIMITS[PlanType.ESSENTIEL]},
        "confort":   {"sms": PLAN_SMS_LIMITS[PlanType.CONFORT],   "voice_min": PLAN_VOICE_LIMITS[PlanType.CONFORT],   "visio_min": PLAN_VISIO_LIMITS[PlanType.CONFORT]},
        "premium":   {"sms": PLAN_SMS_LIMITS[PlanType.PREMIUM],   "voice_min": PLAN_VOICE_LIMITS[PlanType.PREMIUM],   "visio_min": PLAN_VISIO_LIMITS[PlanType.PREMIUM]},
    }
except ImportError:
    _PLAN_LIMITS = {
        "essentiel": {"sms": 25, "voice_min": 40, "visio_min": 12},
        "confort":   {"sms": 50, "voice_min": 100, "visio_min": 28},
        "premium":   {"sms": 100, "voice_min": 180, "visio_min": 55},
    }


@app.get("/api/quota")
async def get_quota(request: Request):
    """Retourne quotas reels (stockage + usage SMS/voix/visio depuis Redis)."""
    tid = getattr(request.state, "tenant_id", 1)
    mgr = _get_tenant_manager(tid)
    if not mgr:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})
    try:
        # --- Quotas stockage (memoire, conversations, etc.) ---
        quota_status = mgr.get_quota_status()

        # --- Usage reel depuis Cortex Redis ---
        plan_name = (quota_status.get("plan") or "essentiel").lower()
        limits = _PLAN_LIMITS.get(plan_name, _PLAN_LIMITS["essentiel"])

        real_usage = {"sms_count": 0, "voice_minutes": 0.0, "tavus_minutes": 0.0}
        cortex = get_cortex() if _CORTEX_AVAILABLE else None
        if cortex and hasattr(cortex, "cost_tracker") and cortex.cost_tracker:
            real_usage = await cortex.cost_tracker.get_tenant_month_usage(tid)

        sms_used = real_usage["sms_count"]
        sms_limit = limits["sms"]
        voice_used = real_usage["voice_minutes"]
        voice_limit = limits["voice_min"]
        visio_used = real_usage["tavus_minutes"]
        visio_limit = limits["visio_min"]

        quota_status["sms"] = {
            "used": sms_used,
            "limit": sms_limit,
            "percentage": round((sms_used / sms_limit) * 100, 1) if sms_limit else 0,
        }
        quota_status["voice"] = {
            "used": round(voice_used, 1),
            "limit": voice_limit,
            "unit": "min",
            "percentage": round((voice_used / voice_limit) * 100, 1) if voice_limit else 0,
        }
        quota_status["visio"] = {
            "used": round(visio_used, 1),
            "limit": visio_limit,
            "unit": "min",
            "percentage": round((visio_used / visio_limit) * 100, 1) if visio_limit else 0,
        }
        quota_status["plan_limits"] = limits

        daily_stats = mgr.get_daily_stats()
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
    if not tavus_client or not tavus_client.is_configured:
        return JSONResponse(status_code=503, content={"error": "Service visio non disponible"})
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    # Validation: verifier que la conversation_id est connue
    conversation_id = body.get("conversation_id", "")
    if conversation_id and hasattr(tavus_client, "_active_conversations"):
        if conversation_id not in tavus_client._active_conversations:
            logger.warning(f"Tavus webhook: conversation_id inconnue {conversation_id}")

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

    # Trouve le tenant_id depuis la conversation Tavus active
    tid = TENANT_ID
    if tavus_client and conversation_id:
        conv = tavus_client._active_conversations.get(conversation_id)
        if conv:
            tid = conv.tenant_id

    logger.info(f"Tavus tool_call: {tool_name}({args}) [conv={conversation_id}, tenant={tid}]")

    result = {"status": "error", "message": "Fonction inconnue"}

    try:
        if tool_name == "send_sms":
            result = await _tool_send_sms(args, tenant_id=tid)
        elif tool_name == "create_instruction":
            result = await _tool_create_instruction(args, tenant_id=tid)
        elif tool_name == "create_note":
            result = await _tool_create_note(args, tenant_id=tid)
        elif tool_name == "get_contacts":
            result = await _tool_get_contacts(tenant_id=tid)
        elif tool_name == "generate_document":
            result = await _tool_generate_document(args, tenant_id=tid)
        elif tool_name == "alert_contacts":
            result = await _tool_alert_contacts(args, tenant_id=tid)
        elif tool_name == "report_observation":
            result = await _tool_report_observation(args)
        elif tool_name == "send_email":
            result = await _tool_send_email(args, tenant_id=tid)
        elif tool_name == "invite_visio":
            result = await _tool_invite_visio(args, tenant_id=tid)
        else:
            logger.warning(f"Tavus tool inconnu: {tool_name}")
    except Exception as e:
        logger.error(f"Tavus tool_call error ({tool_name}): {e}")
        result = {"status": "error", "message": str(e)}

    # Poste le resultat dans le fil de discussion du tenant
    if _redis_client and tid and tool_name not in ("get_contacts", "report_observation"):
        try:
            mgr = _get_tenant_manager(tid)
            if mgr:
                status_icon = "ok" if result.get("status") == "success" else "erreur"
                action_msg = f"[Visio] {tool_name}: {result.get('message', '')}"
                mgr.add_message(
                    conv_id="visio",
                    role=MessageRole.LUNA,
                    content=action_msg,
                    channel=Channel.APP,
                )
        except Exception as e:
            logger.warning(f"Failed to post visio result to chat: {e}")

    return result


async def _tool_send_sms(args: Dict, tenant_id: int = 0) -> Dict:
    """Envoie un SMS a un contact de confiance."""
    # Service validation (redundant safety layer)
    if _license_heartbeat and (_license_heartbeat.is_blocked() or _license_heartbeat.is_degraded()):
        return {"status": "error", "message": "Service non disponible"}
    mgr = _get_tenant_manager(tenant_id) if tenant_id else _memory_manager
    if not mgr or not sms_client.is_configured:
        return {"status": "error", "message": "Service SMS non disponible"}
    # Quota pre-check
    if _quota_guard:
        try:
            qs = _quota_guard.check(tenant_id or TENANT_ID, CoreActionType.SEND_SMS)
            if not qs.allowed:
                return {"status": "error", "message": qs.warning_message or "Quota SMS atteint pour ce mois"}
        except Exception:
            pass

    contact_name = args.get("contact_name", "")
    message = args.get("message", "")
    if not contact_name or not message:
        return {"status": "error", "message": "Nom du contact et message requis"}

    # Cherche le contact par nom
    contacts = mgr.list_trusted_contacts()
    phone = None
    matched_name = ""
    for c in contacts:
        if contact_name.lower() in c.name.lower() or contact_name.lower() in (c.relation or "").lower():
            phone = c.phone
            matched_name = c.name
            break

    if not phone:
        return {"status": "error", "message": f"Contact '{contact_name}' non trouve parmi les contacts de confiance"}

    # Recupere le prenom du souscripteur
    sub_name = _SUBSCRIBER_NAME
    if mgr and tenant_id:
        try:
            profile = mgr.get_subscriber_profile()
            if profile and profile.first_name:
                sub_name = profile.first_name
        except Exception:
            pass

    success, details = _tracked_sms_send(phone, f"[Luna pour {sub_name}] {message}", label=f"Chat SMS a {matched_name}")
    reasoning = f"Luna envoie un SMS a {matched_name} car le souscripteur l'a demande"
    if success:
        # Track cout SMS par tenant via Cortex
        try:
            cortex = get_cortex() if _CORTEX_AVAILABLE else None
            if cortex and hasattr(cortex, 'cost_tracker') and cortex.cost_tracker:
                import asyncio
                await cortex.cost_tracker.track_sms_tenant(tenant_id or 0)
        except Exception:
            pass
        try:
            mgr.add_note(
                content=f"[Action SMS] {reasoning} | Contenu: {message[:100]}",
                context="tool_call",
                tags=["sms", matched_name, "reasoning"],
            )
        except Exception:
            pass
        try:
            mgr.log_event(
                category="action",
                description=f"SMS envoye a {matched_name}: {message[:60]}",
                reasoning=reasoning,
                source="tool_call",
            )
        except Exception:
            pass
        return {"status": "success", "message": f"SMS envoye a {matched_name}", "reasoning": reasoning}
    return {"status": "error", "message": f"Echec envoi SMS: {details.get('error', 'inconnu')}"}


async def _tool_send_email(args: Dict, tenant_id: int = 0) -> Dict:
    """Envoie un email a un contact de confiance."""
    if _license_heartbeat and (_license_heartbeat.is_blocked() or _license_heartbeat.is_degraded()):
        return {"status": "error", "message": "Service non disponible"}
    tid = tenant_id or TENANT_ID
    mgr = _get_tenant_manager(tid) if tid else _memory_manager
    if not mgr:
        return {"status": "error", "message": "Service memoire non disponible"}

    # Verifie qu'au moins un service email est dispo
    has_gmail = gmail_client and gmail_client.is_configured and _redis_client and _redis_client.get_email_integration(tid)
    if not has_gmail and not email_client.is_configured:
        return {"status": "error", "message": "Aucun service email configure. Connectez Gmail ou configurez SendGrid."}

    contact_name = args.get("contact_name", "")
    subject = args.get("subject", "")
    body = args.get("body", "")
    if not contact_name or not body:
        return {"status": "error", "message": "Nom du contact et contenu requis"}

    # Recupere le prenom du souscripteur
    sub_name = _SUBSCRIBER_NAME
    if mgr and tenant_id:
        try:
            profile = mgr.get_subscriber_profile()
            if profile and profile.first_name:
                sub_name = profile.first_name
        except Exception:
            pass

    if not subject:
        subject = f"Message de {sub_name} via Luna"

    # Cherche le contact par nom
    contacts = mgr.list_trusted_contacts()
    contact_email = None
    matched_name = ""
    for c in contacts:
        if contact_name.lower() in c.name.lower() or contact_name.lower() in (c.relation or "").lower():
            contact_email = getattr(c, "email", None)
            matched_name = c.name
            break

    if not matched_name:
        return {"status": "error", "message": f"Contact '{contact_name}' non trouve parmi les contacts de confiance"}
    if not contact_email:
        return {"status": "error", "message": f"{matched_name} n'a pas d'adresse email enregistree. Ajoutez-la via le dashboard admin."}

    # Utilise send_for_tenant (Gmail OAuth d'abord, puis SendGrid fallback)
    success, details = await email_client.send_for_tenant(
        tenant_id=tid,
        redis_client=_redis_client,
        gmail_client=gmail_client,
        to=contact_email,
        subject=subject,
        body_text=body,
        subscriber_name=sub_name,
    )
    reasoning = f"Luna envoie un email a {matched_name} car le souscripteur l'a demande"
    if success:
        try:
            mgr.add_note(
                content=f"[Action Email] {reasoning} | Objet: {subject[:80]} | Dest: {matched_name}",
                context="tool_call",
                tags=["email", matched_name, "reasoning"],
            )
        except Exception:
            pass
        try:
            mgr.log_event(
                category="action",
                description=f"Email envoye a {matched_name}: {subject[:60]}",
                reasoning=reasoning,
                source="tool_call",
            )
        except Exception:
            pass
        return {"status": "success", "message": f"Email envoye a {matched_name} ({contact_email})", "reasoning": reasoning}
    return {"status": "error", "message": f"Echec envoi email: {details.get('error', 'inconnu')}"}


async def _tool_invite_visio(args: Dict, tenant_id: int = 0) -> Dict:
    """Invite un contact en visioconference : cree la visio + envoie le lien par SMS."""
    if _license_heartbeat and (_license_heartbeat.is_blocked() or _license_heartbeat.is_degraded()):
        return {"status": "error", "message": "Service non disponible"}
    tid = tenant_id or TENANT_ID
    mgr = _get_tenant_manager(tid) if tid else _memory_manager
    if not mgr:
        return {"status": "error", "message": "Memoire non disponible"}
    if not tavus_client or not tavus_client.is_configured:
        return {"status": "error", "message": "Service visio non disponible"}
    if not sms_client or not sms_client.is_configured:
        return {"status": "error", "message": "Service SMS non disponible"}

    contact_name = args.get("contact_name", "")
    if not contact_name:
        return {"status": "error", "message": "Nom du contact requis"}

    # Cherche le contact
    contacts = mgr.list_trusted_contacts()
    phone = None
    matched_name = ""
    for c in contacts:
        if contact_name.lower() in c.name.lower() or contact_name.lower() in (c.relation or "").lower():
            phone = c.phone
            matched_name = c.name
            break

    if not phone:
        return {"status": "error", "message": f"Contact '{contact_name}' non trouve parmi les contacts de confiance"}

    # Recupere le prenom du souscripteur
    sub_name = _SUBSCRIBER_NAME
    if mgr:
        try:
            profile = mgr.get_subscriber_profile()
            if profile and profile.first_name:
                sub_name = profile.first_name
        except Exception:
            pass

    # Cree la conversation Tavus immediatement
    visio_max = int(os.getenv("VISIO_MAX_DURATION", "15")) * 60  # minutes -> secondes
    context = f"Tu es Luna. {sub_name} a invite {matched_name} en visioconference. Sois chaleureuse et accueillante."
    success_tavus, data = await tavus_client.create_conversation(
        tenant_id=tid,
        custom_greeting=f"Bonjour {matched_name} ! {sub_name} t'a invite en visio. Bienvenue !",
        context=context,
        max_duration=visio_max,
        callback_url=TAVUS_CALLBACK_URL if TAVUS_CALLBACK_URL else None,
    )
    if not success_tavus:
        return {"status": "error", "message": f"Impossible de creer la visio: {data.get('error', 'inconnu')}"}

    visio_url = data["conversation_url"]

    # Envoie le lien par SMS directement (pas de OUI/NON — le contact clique s'il veut)
    invite_msg = (
        f"[Luna] {sub_name} t'invite en visioconference ! "
        f"Clique ici pour rejoindre : {visio_url}"
    )
    from integrations.twilio.sms_client import TwilioSMSClient
    normalized_phone = TwilioSMSClient.normalize_phone(phone)
    success_sms, sms_details = _tracked_sms_send(normalized_phone, invite_msg, label=f"Invitation visio a {matched_name}")

    if success_sms:
        # Track cout SMS par tenant via Cortex
        try:
            cortex = get_cortex() if _CORTEX_AVAILABLE else None
            if cortex and hasattr(cortex, 'cost_tracker') and cortex.cost_tracker:
                await cortex.cost_tracker.track_sms_tenant(tenant_id or 0)
        except Exception:
            pass

    if not success_sms:
        # La visio est creee mais le SMS a echoue — donne quand meme le lien
        logger.error(f"SMS invite failed but visio created: {visio_url}")
        return {
            "status": "partial",
            "message": f"Visio creee mais echec envoi SMS a {matched_name}. Voici le lien : {visio_url}",
            "visio_url": visio_url,
        }

    logger.info(f"Visio invite sent: {matched_name} ({normalized_phone}) -> {visio_url}")

    try:
        mgr.log_event(
            category="action",
            description=f"Invitation visio envoyee a {matched_name} avec lien {visio_url}",
            reasoning=f"Luna invite {matched_name} en visio a la demande de {sub_name}",
            source="tool_call",
        )
    except Exception:
        pass

    return {
        "status": "success",
        "message": f"Lien visio envoye a {matched_name} par SMS ! Toi aussi tu peux rejoindre la visio avec ce lien : {visio_url}",
        "visio_url": visio_url,
    }


async def _tool_call_contact(args: Dict, tenant_id: int = 0) -> Dict:
    """Appelle un contact de confiance en audio via Twilio. Luna parle au contact et transmet un message."""
    if _license_heartbeat and (_license_heartbeat.is_blocked() or _license_heartbeat.is_degraded()):
        return {"status": "error", "message": "Service non disponible"}
    tid = tenant_id or TENANT_ID
    mgr = _get_tenant_manager(tid) if tid else _memory_manager
    if not mgr:
        return {"status": "error", "message": "Memoire non disponible"}
    if not voice_client or not voice_client.is_configured:
        return {"status": "error", "message": "Service d'appels vocaux non configure"}
    if not VOICE_CALLBACK_URL:
        return {"status": "error", "message": "URL de callback vocal non configuree"}

    contact_name = args.get("contact_name", "")
    message = args.get("message", "")
    direct_phone = args.get("phone_number", "")
    if not contact_name:
        return {"status": "error", "message": "Nom du contact requis"}

    # Numeros d'urgence interdits (Luna ne doit pas appeler le 15, 17, 18, 112)
    _EMERGENCY_NUMBERS = {"15", "17", "18", "112", "114", "115", "119", "3114", "3977"}
    if direct_phone and direct_phone.strip().replace(" ", "") in _EMERGENCY_NUMBERS:
        return {"status": "error", "message": f"Luna ne peut pas appeler les numeros d'urgence. Suggere au souscripteur de composer le {direct_phone} lui-meme."}

    phone = None
    matched_name = contact_name
    is_admin_call = False

    if direct_phone:
        # Appel administration/service : numero fourni directement par le souscripteur
        phone = direct_phone
        matched_name = contact_name or "Administration"
        is_admin_call = True
    else:
        # Cherche dans les contacts de confiance
        contacts = mgr.list_trusted_contacts()
        for c in contacts:
            if contact_name.lower() in c.name.lower() or contact_name.lower() in (c.relation or "").lower():
                phone = c.phone
                matched_name = c.name
                break

    if not phone:
        return {"status": "error", "message": f"Contact '{contact_name}' non trouve parmi les contacts de confiance. Pour appeler un service/administration, demande le numero au souscripteur."}

    # Recupere le prenom du souscripteur
    sub_name = _SUBSCRIBER_NAME
    if mgr:
        try:
            profile = mgr.get_subscriber_profile()
            if profile and profile.first_name:
                sub_name = profile.first_name
        except Exception:
            pass

    # Normaliser le numero
    from integrations.twilio.sms_client import TwilioSMSClient
    normalized_phone = TwilioSMSClient.normalize_phone(phone)

    # Mission pour Luna pendant l'appel
    if is_admin_call:
        mission = f"Tu appelles {matched_name} pour {sub_name}. "
        if message:
            mission += f"Voici la demande de {sub_name} : {message}"
        else:
            mission += f"{sub_name} souhaite obtenir des informations."
        greeting = f"Bonjour ! Je suis Luna, l'assistante de {sub_name}. "
        if message:
            greeting += f"J'appelle de la part de {sub_name}. {message}"
        else:
            greeting += f"J'appelle de la part de {sub_name} pour obtenir des renseignements."
    else:
        mission = f"Tu appelles {matched_name} de la part de {sub_name}. "
        if message:
            mission += f"Voici ce que {sub_name} veut que tu transmettes : {message}"
        else:
            mission += f"{sub_name} voulait prendre des nouvelles."
        greeting = f"Bonjour {matched_name} ! C'est Luna, l'assistante de {sub_name}. "
        if message:
            greeting += f"{sub_name} m'a demande de t'appeler pour te dire : {message}"
        else:
            greeting += f"{sub_name} m'a demande de t'appeler pour prendre de tes nouvelles."

    # Lancer l'appel via Twilio
    success, data = await voice_client.initiate_call_async(normalized_phone)
    if not success:
        return {"status": "error", "message": f"Impossible d'appeler {matched_name}: {data.get('error', 'erreur inconnue')}"}

    call_sid = data.get("call_sid", "")
    # Stocker les parametres pour le bridge
    _voice_call_params[call_sid] = {
        "mission": mission,
        "max_duration": 180,
        "greeting": greeting,
    }

    logger.info(f"Voice call initiated to {matched_name} ({normalized_phone}) call_sid={call_sid}")

    try:
        mgr.log_event(
            category="action",
            description=f"Appel audio lance vers {matched_name} ({normalized_phone})",
            reasoning=f"Luna appelle {matched_name} a la demande de {sub_name}: {message[:80]}",
            source="tool_call",
        )
    except Exception:
        pass

    return {
        "status": "success",
        "message": f"J'appelle {matched_name} maintenant ! L'appel est en cours. Je vais lui transmettre ton message.",
        "call_sid": call_sid,
    }


async def _tool_create_instruction(args: Dict, tenant_id: int = 0) -> Dict:
    """Cree une instruction depuis la visio."""
    tid = tenant_id or TENANT_ID
    mgr = _get_tenant_manager(tid) if tid else _memory_manager
    if not mgr or not _CORE_AVAILABLE:
        return {"status": "error", "message": "Memoire non disponible"}

    text = args.get("text", "")
    if not text:
        return {"status": "error", "message": "Texte de l'instruction requis"}

    parsed = InstructionParser.parse(text)

    action_map = {
        "reminder": SchemaActionType.REMINDER,
        "sms_contact": SchemaActionType.SMS,
        "call_contact": SchemaActionType.CALL,
        "visio_contact": SchemaActionType.VISIO,
        "wake_up": SchemaActionType.CALL,
        "check_in": SchemaActionType.REMINDER,
        "surveillance": SchemaActionType.ALERT,
        "note": SchemaActionType.NOTE,
        "daily_routine": SchemaActionType.REMINDER,
        "information": SchemaActionType.REMINDER,
        "reading": SchemaActionType.REMINDER,
        "game": SchemaActionType.REMINDER,
        "music": SchemaActionType.REMINDER,
        "gratitude": SchemaActionType.REMINDER,
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

    instr = mgr.add_instruction(
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
            _scheduler.schedule(instruction_id=instr.id, tenant_id=tid, instruction=parsed)
        except Exception:
            pass

    confirmation = InstructionParser.format_confirmation(parsed)
    return {"status": "success", "message": confirmation, "instruction_id": instr.id}


async def _tool_create_note(args: Dict, tenant_id: int = 0) -> Dict:
    """Prend une note depuis la visio."""
    mgr = _get_tenant_manager(tenant_id) if tenant_id else _memory_manager
    if not mgr:
        return {"status": "error", "message": "Memoire non disponible"}

    content = args.get("content", "")
    if not content:
        return {"status": "error", "message": "Contenu de la note requis"}

    reasoning = f"Luna prend une note a la demande du souscripteur"
    mgr.add_note(
        content=f"{content}\n[Raison: {reasoning}]",
        context="tool_call",
        tags=["note", "reasoning"],
    )
    return {"status": "success", "message": f"Note enregistree: {content[:50]}", "reasoning": reasoning}


async def _tool_get_contacts(tenant_id: int = 0) -> Dict:
    """Liste les contacts de confiance."""
    mgr = _get_tenant_manager(tenant_id) if tenant_id else _memory_manager
    if not mgr:
        return {"status": "error", "message": "Memoire non disponible"}

    contacts = mgr.list_trusted_contacts()
    if not contacts:
        return {"status": "success", "message": "Aucun contact de confiance enregistre.", "contacts": []}

    contact_list = [{"name": c.name, "relation": c.relation} for c in contacts]
    names = ", ".join([f"{c.name} ({c.relation})" for c in contacts])
    return {"status": "success", "message": f"Contacts de confiance: {names}", "contacts": contact_list}


async def _tool_generate_document(args: Dict, tenant_id: int = 0) -> Dict:
    """Genere un document depuis la visio."""
    tid = tenant_id or TENANT_ID
    mgr = _get_tenant_manager(tid) if tid else _memory_manager
    if not _doc_generator or not mgr:
        return {"status": "error", "message": "Generateur de documents non disponible"}

    doc_type = args.get("doc_type", "courrier_admin")
    subject = args.get("subject", "")
    details = args.get("details", "")

    if not subject:
        return {"status": "error", "message": "Sujet du document requis"}

    # Genere le contenu avec GPT
    profile = mgr.get_subscriber_profile()
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
        logger.error(f"Document generation LLM error: {e}")
        return {"status": "error", "message": "Erreur lors de la generation du document. Reessaie."}

    if doc_type == "fiche_sante" and profile_dict:
        filename = _doc_generator.generate_health_sheet(profile_dict)
    else:
        filename = _doc_generator.generate_letter(
            doc_type=doc_type,
            subject=subject,
            body_text=body_text,
            profile=profile_dict,
        )

    url = f"/api/documents/download/{filename}"

    try:
        mgr.add_note(
            content=f"Document genere: {subject} ({doc_type}) → {filename}",
            context="document",
            tags=["document", doc_type],
        )
    except Exception:
        pass

    # Envoie automatiquement le contenu par email au souscripteur si email dispo
    email_sent = False
    if profile_dict.get("email") and body_text:
        try:
            sub_email = profile_dict["email"]
            sub_name = profile_dict.get("first_name", "")
            email_subject = f"Document Luna : {subject}"
            email_body = f"Bonjour {sub_name},\n\nVoici le document que tu m'as demande :\n\n---\n{body_text}\n---\n\nBien a toi,\nLuna"
            ok, _ = await email_client.send_for_tenant(
                tenant_id=tid,
                redis_client=_redis_client,
                gmail_client=gmail_client,
                to=sub_email,
                subject=email_subject,
                body_text=email_body,
                subscriber_name=sub_name,
            )
            if ok:
                email_sent = True
                logger.info(f"Document envoye par email a {sub_email}")
        except Exception as e:
            logger.warning(f"Failed to email document: {e}")

    msg = f"Document genere : {subject}."
    if email_sent:
        msg += f" Je te l'ai aussi envoye par email a {profile_dict['email']}."
    msg += f" Tu peux le retrouver dans l'onglet Documents."

    return {"status": "success", "message": msg, "url": url, "filename": filename}


async def _tool_alert_contacts(args: Dict, tenant_id: int = 0) -> Dict:
    """Alerte tous les contacts de confiance."""
    mgr = _get_tenant_manager(tenant_id) if tenant_id else _memory_manager
    if not mgr or not sms_client.is_configured:
        return {"status": "error", "message": "Service SMS non disponible"}

    reason = args.get("reason", "situation preoccupante")
    contacts = mgr.list_trusted_contacts()

    if not contacts:
        return {"status": "error", "message": "Aucun contact de confiance enregistre"}

    profile = mgr.get_subscriber_profile()
    name = profile.first_name if profile else "votre proche"

    sent = 0
    for c in contacts:
        msg = f"[ALERTE Luna] {name} a besoin d'aide. Raison: {reason}. Merci de verifier qu'il va bien. En cas d'urgence, appelez le 112."
        success, _ = _tracked_sms_send(c.phone, msg, label="Alerte contacts urgence")
        if success:
            sent += 1
            # Track cout SMS par tenant via Cortex
            try:
                cortex = get_cortex() if _CORTEX_AVAILABLE else None
                if cortex and hasattr(cortex, 'cost_tracker') and cortex.cost_tracker:
                    await cortex.cost_tracker.track_sms_tenant(tenant_id or 0)
            except Exception:
                pass

    reasoning = f"Luna alerte les contacts car: {reason}"
    try:
        mgr.add_note(
            content=f"[Action ALERTE] {reasoning} | {sent} contact(s) alertes",
            context="alerte_urgence",
            tags=["urgence", "alerte", "reasoning"],
        )
    except Exception:
        pass
    try:
        mgr.log_event(
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
async def generate_document(req: DocumentRequest, request: Request):
    """Genere un document DOCX via GPT + python-docx"""
    if not _doc_generator:
        return JSONResponse(status_code=503, content={"error": "Generateur non disponible"})

    tid = getattr(request.state, "tenant_id", 1)
    mgr = _get_tenant_manager(tid)

    profile_dict = {}
    if mgr:
        profile = mgr.get_subscriber_profile()
        if profile:
            profile_dict = profile.model_dump()

    # Special case: fiche sante (from profile directly)
    if req.doc_type == "fiche_sante" and profile_dict:
        filename = _doc_generator.generate_health_sheet(profile_dict)
        return {
            "success": True,
            "filename": filename,
            "download_url": f"/api/documents/download/{filename}",
            "type": "fiche_sante",
        }

    # Special case: export notes
    if req.doc_type == "export_notes" and mgr:
        notes = mgr.list_notes(limit=200)
        note_dicts = [{"content": n.content, "context": n.context, "created_at": n.created_at.isoformat() if n.created_at else "", "tags": n.tags} for n in notes]
        filename = _doc_generator.generate_notes_export(note_dicts)
        return {
            "success": True,
            "filename": filename,
            "download_url": f"/api/documents/download/{filename}",
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
        logger.error(f"Document generation error: {e}")
        return JSONResponse(status_code=500, content={"error": "Erreur lors de la generation du document."})

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
        "download_url": f"/api/documents/download/{filename}",
        "type": req.doc_type,
        "preview": body_text[:300],
    }


@app.get("/api/documents")
async def list_documents(request: Request):
    """Liste les documents generes"""
    if not _doc_generator:
        return JSONResponse(status_code=503, content={"error": "Generateur non disponible"})
    tid = getattr(request.state, "tenant_id", 1)
    docs = _doc_generator.list_documents()
    for d in docs:
        d["download_url"] = f"/api/documents/download/{d['filename']}"
    return {"documents": docs, "count": len(docs)}


@app.get("/api/documents/download/{filename}")
async def serve_document(filename: str, request: Request):
    """Sert un document genere au telechargement (auth requise, tenant verifie)"""
    tid = getattr(request.state, "tenant_id", 1)
    # Securite : empeche path traversal
    if ".." in filename or "/" in filename:
        return JSONResponse(status_code=400, content={"error": "Nom de fichier invalide"})
    filepath = os.path.join(os.path.dirname(__file__), "static", "documents", str(tid), filename)
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

@app.post("/api/perception/start")
async def start_perception():
    """Active la perception (camera navigateur, analyse OpenAI Vision)."""
    if not _memory_manager:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})

    # Init le detector si pas encore fait
    if _perception_detector and not _perception_detector._initialized:
        _perception_detector.initialize()

    if not _perception_detector or not _perception_detector._initialized:
        return JSONResponse(status_code=503, content={
            "error": "Module perception non disponible"
        })

    _memory_manager.set_perception_enabled(True)
    _perception_detector.set_remote_camera_active(True)
    logger.info("Perception activated (browser camera mode)")
    return {"success": True, "message": "Perception activee - ouvre ta camera"}


@app.post("/api/perception/stop")
async def stop_perception():
    """Desactive la perception camera."""
    if not _memory_manager:
        return JSONResponse(status_code=503, content={"error": "Memoire non disponible"})

    _memory_manager.set_perception_enabled(False)
    if _perception_detector:
        _perception_detector.set_remote_camera_active(False)
    if _perception_analyzer:
        _perception_analyzer.reset()

    logger.info("Perception deactivated by user")
    return {"success": True, "message": "Perception desactivee"}


@app.post("/api/perception/frame")
async def receive_perception_frame(request: Request):
    """
    Recoit une frame JPEG base64 depuis le navigateur et l'analyse.
    Le navigateur capture via getUserMedia et envoie toutes les ~10 secondes.
    """
    if not _perception_detector or not _perception_analyzer or not _memory_manager:
        return JSONResponse(status_code=503, content={"error": "Perception non disponible"})

    if not _memory_manager.is_perception_enabled():
        return JSONResponse(status_code=400, content={"error": "Perception non activee"})

    try:
        body = await request.json()
        image_b64 = body.get("image")
        if not image_b64:
            return JSONResponse(status_code=400, content={"error": "Image manquante"})

        # Limiter la taille (max ~500KB base64 = ~375KB image)
        if len(image_b64) > 700_000:
            return JSONResponse(status_code=400, content={"error": "Image trop grande (max 500KB)"})

    except Exception:
        return JSONResponse(status_code=400, content={"error": "Body JSON invalide"})

    # Analyse via OpenAI Vision (bloquant -> executor)
    loop = asyncio.get_event_loop()
    frame_analysis = await loop.run_in_executor(
        None, _perception_detector.analyze_frame_b64, image_b64
    )

    if not frame_analysis:
        return {"success": False, "error": "Analyse echouee"}

    # Analyse temporelle (postures, anomalies)
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
                    source="perception_frame",
                    details={"severity": abn["severity"], "type": abn["type"]},
                )
            except Exception:
                pass

    return {
        "success": True,
        "scene": scene_state.to_dict(),
        "inference_ms": round(frame_analysis.inference_time_ms),
    }


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
        "available": _perception_detector is not None and (
            _perception_detector._initialized if _perception_detector else False
        ),
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


_last_heartbeat_time = 0  # timestamp du dernier heartbeat

async def _instruction_loop():
    """Boucle de fond : verifie les taches dues toutes les 30s et les execute"""
    global _last_heartbeat_time
    logger.info("Instruction loop started (30s interval)")
    while True:
        try:
            await asyncio.sleep(30)

            # License heartbeat toutes les 6 heures
            if _license_heartbeat:
                now = time.time()
                if now - _last_heartbeat_time > 21600:  # 6h = 21600s
                    try:
                        result = await _license_heartbeat.check()
                        _last_heartbeat_time = now
                        action = result.get("action", "unknown")
                        logger.info(f"License heartbeat: action={action}")
                        if _license_heartbeat.is_blocked():
                            logger.critical("LICENSE BLOQUEE par le backend")
                        elif _license_heartbeat.is_degraded():
                            logger.warning("LICENSE DEGRADEE - chat seul")
                    except Exception as e:
                        logger.error(f"License heartbeat error: {e}")

            # Notification engine check (self rate-limited to every 5 min)
            if _notification_engine:
                try:
                    from core.gamification.redis_ops import GamificationRedisOps
                    await _notification_engine.check_all_tenants(GamificationRedisOps)
                except Exception as e:
                    logger.warning(f"Notification engine error: {e}")

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
            # Backoff progressif en cas d'erreurs repetees
            await asyncio.sleep(30)


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


# =============================================================================
# UNIFIED API - Memoire temps reel multi-canal
# =============================================================================

def _get_or_create_session(tid: int = None) -> Optional[Dict]:
    """Recupere ou cree une session unifiee"""
    if not _redis_client:
        return None
    tid = tid if tid is not None else TENANT_ID
    session = _redis_client.get_session(tid)
    if not session:
        new_session = UnifiedSession(tenant_id=tid)
        _redis_client.set_session(tid, new_session.to_redis())
        return new_session.to_redis()
    return session


def _update_session_activity(channel: str = None, topic: str = None, mood: str = None,
                             tid: int = None):
    """Met a jour l'activite de la session"""
    if not _redis_client:
        return
    tid = tid if tid is not None else TENANT_ID
    updates = {"last_activity": datetime.utcnow().isoformat(), "status": "active"}
    if channel:
        updates["active_channel"] = channel
    if topic:
        updates["current_topic"] = topic
    if mood:
        updates["current_mood"] = mood
    _redis_client.update_session(tid, updates)


def _add_unified_message(channel: str, role: str, content: str,
                         audio_duration: float = None, mood: str = None,
                         intent: str = None, tool_calls: list = None,
                         tid: int = None):
    """Ajoute un message a l'historique unifie"""
    if not _redis_client:
        return None
    tid = tid if tid is not None else TENANT_ID
    msg = UnifiedMessage(
        tenant_id=tid,
        channel=Channel(channel),
        role=MessageRole(role),
        content=content,
        audio_duration_sec=audio_duration,
        detected_mood=MoodIndicator(mood) if mood else None,
        detected_intent=intent,
        tool_calls=tool_calls,
    )
    _redis_client.add_unified_message(tid, msg.id, msg.to_redis())
    # Publier evenement temps reel
    _redis_client.publish_event(tid, "new_message", {
        "id": msg.id, "channel": channel, "role": role, "content": content[:100]
    })
    return msg.id


@app.get("/api/unified/session")
async def get_unified_session(request: Request):
    """Recupere l'etat de la session active"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)

    session = _get_or_create_session(tid)
    context = _redis_client.get_context(tid) or {}

    return {
        "session": session,
        "context": context,
        "channels": {
            "app": True,
            "voice": True,
            "sms": sms_client.is_configured if sms_client else False,
            "visio": tavus_client.is_configured if tavus_client else False,
        }
    }


@app.post("/api/unified/send")
async def unified_send(request: Request):
    """Envoie un message unifie (detecte le canal automatiquement ou specifie)"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)
    data = await request.json()
    content = data.get("content", "").strip()
    channel = data.get("channel", "app")
    role = data.get("role", "subscriber")

    if not content:
        return JSONResponse(status_code=400, content={"error": "content requis"})

    # Valider le canal
    valid_channels = ["app", "voice", "sms", "call", "visio"]
    if channel not in valid_channels:
        return JSONResponse(status_code=400, content={
            "error": f"Canal invalide. Valides: {', '.join(valid_channels)}"
        })

    # Mettre a jour la session
    _update_session_activity(channel=channel, tid=tid)

    # Ajouter le message a l'historique unifie
    msg_id = _add_unified_message(channel, role, content, tid=tid)

    # Si c'est un message du subscriber, generer une reponse Luna
    response_content = None
    if role == "subscriber":
        # Recuperer le contexte recent
        recent_messages = _redis_client.get_recent_context_messages(tid, count=15)

        # Construire l'historique pour OpenAI
        messages = [{"role": "system", "content": LUNA_SYSTEM_PROMPT}]
        for msg in reversed(recent_messages):
            msg_role = "assistant" if msg.get("role") == "luna" else "user"
            messages.append({"role": msg_role, "content": msg.get("content", "")})

        # Appel OpenAI
        try:
            response = openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                max_tokens=500,
            )
            response_content = response.choices[0].message.content

            # Ajouter la reponse Luna
            luna_msg_id = _add_unified_message(channel, "luna", response_content, tid=tid)

            # Mettre a jour le contexte
            _redis_client.update_context(tid, {
                "last_topic": content[:50],
                "last_response": response_content[:100],
                "last_channel": channel,
                "updated_at": datetime.utcnow().isoformat(),
            })

        except Exception as e:
            logger.error(f"Unified send error: {e}")
            response_content = "Je suis desolee, j'ai eu un petit souci. Pouvez-vous repeter?"

    return {
        "success": True,
        "message_id": msg_id,
        "channel": channel,
        "response": response_content,
    }


@app.get("/api/unified/history")
async def get_unified_history(request: Request, limit: int = 50, channel: str = None):
    """Recupere l'historique unifie de tous les canaux"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)

    messages = _redis_client.get_unified_messages(tid, limit=limit, channel=channel)

    return {
        "messages": messages,
        "count": len(messages),
        "filter_channel": channel,
    }


@app.get("/api/unified/context")
async def get_realtime_context(request: Request):
    """Recupere le contexte temps reel (pour affichage app)"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)

    session = _redis_client.get_session(tid)
    context = _redis_client.get_context(tid)
    last_handoff = _redis_client.get_last_handoff(tid)

    # Dernier message par canal
    last_by_channel = {}
    for ch in ["app", "voice", "sms", "visio"]:
        msgs = _redis_client.get_unified_messages(tid, limit=1, channel=ch)
        if msgs:
            last_by_channel[ch] = msgs[0]

    return {
        "session": session,
        "context": context,
        "last_handoff": last_handoff,
        "last_by_channel": last_by_channel,
    }


@app.post("/api/unified/handoff")
async def channel_handoff(request: Request):
    """Change de canal avec transfert de contexte"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)
    data = await request.json()
    from_channel = data.get("from_channel", "app")
    to_channel = data.get("to_channel")
    reason = data.get("reason", "user_request")

    if not to_channel:
        return JSONResponse(status_code=400, content={"error": "to_channel requis"})

    # Recuperer le contexte actuel
    context = _redis_client.get_context(tid) or {}
    recent_messages = _redis_client.get_recent_context_messages(tid, count=5)

    # Creer un resume du contexte
    context_summary = f"Sujet: {context.get('last_topic', 'aucun')}. "
    if recent_messages:
        last_msg = recent_messages[0]
        context_summary += f"Dernier message ({last_msg.get('channel', 'app')}): {last_msg.get('content', '')[:50]}..."

    # Enregistrer le handoff
    handoff = ChannelHandoff(
        tenant_id=tid,
        from_channel=Channel(from_channel),
        to_channel=Channel(to_channel),
        reason=reason,
        context_summary=context_summary,
    )
    _redis_client.add_handoff(tid, handoff.id, handoff.to_redis())

    # Mettre a jour la session
    _redis_client.update_session(tid, {
        "active_channel": to_channel,
        "last_activity": datetime.utcnow().isoformat(),
    })

    # Publier l'evenement
    _redis_client.publish_event(tid, "channel_handoff", {
        "from": from_channel, "to": to_channel, "reason": reason
    })

    return {
        "success": True,
        "handoff_id": handoff.id,
        "context_transferred": context_summary,
    }


# =============================================================================
# VOICE MODE - WebSocket temps reel (sans video)
# =============================================================================

# Pipeline voix legacy (/api/voice/stream) supprime — utiliser /api/voice-call (Twilio Realtime)


# =============================================================================
# SALONS FAMILLE (Rooms) — Chat, Cinema, Karaoke, Jeux
# =============================================================================

from core.rooms.models import (
    ROOM_TYPES, GAME_TYPES, QUIZ_SETS,
    generate_member_token, verify_member_token,
    new_room_data,
)
from core.rooms.redis_ops import RoomRedisOps
from core.rooms.manager import room_manager

_room_ops: Optional[RoomRedisOps] = None


def _get_room_ops() -> Optional[RoomRedisOps]:
    global _room_ops
    if _room_ops is None and _redis_client:
        _room_ops = RoomRedisOps(_redis_client)
    return _room_ops


def _get_member_name(tid: int, phone: str) -> str:
    """Lookup member name from family data or profile (if email)."""
    if not _redis_client:
        return phone
    # If phone looks like an email, lookup profile instead
    if "@" in phone:
        prof = _redis_client.get_profile(tid)
        if prof and prof.get("first_name"):
            return prof["first_name"]
        return phone.split("@")[0]
    m = _redis_client.get_family_member(tid, phone)
    if m:
        return m.get("name", phone)
    return phone


@app.get("/salon")
async def salon_page():
    """Page des salons famille."""
    salon_path = os.path.join(STATIC_DIR, "salon.html")
    if os.path.exists(salon_path):
        return FileResponse(salon_path)
    return JSONResponse(status_code=404, content={"error": "Salon non disponible"})


@app.get("/api/rooms")
async def list_rooms(request: Request):
    """Lister les salons actifs."""
    rops = _get_room_ops()
    if not rops:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})
    tid = getattr(request.state, "tenant_id", TENANT_ID)
    rooms = rops.list_rooms(tid)
    result = []
    for r in rooms:
        result.append({
            "id": r.get("id"),
            "name": r.get("name"),
            "type": r.get("type"),
            "host_name": r.get("host_name"),
            "status": r.get("status", "open"),
            "participants": rops.count_participants(tid, r["id"]),
            "youtube_url": r.get("youtube_url", ""),
            "game_type": r.get("game_type", ""),
            "created_at": r.get("created_at"),
        })
    return result


@app.post("/api/rooms")
async def create_room(request: Request):
    """Créer un salon (souscripteur uniquement)."""
    rops = _get_room_ops()
    if not rops:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})
    tid = getattr(request.state, "tenant_id", TENANT_ID)
    data = await request.json()
    name = data.get("name", "Salon Famille").strip()[:50]
    room_type = data.get("type", "chat")
    if room_type not in ROOM_TYPES:
        return JSONResponse(status_code=400, content={"error": f"Type invalide. Valides: {ROOM_TYPES}"})

    # Get subscriber info
    host_phone = data.get("phone", "subscriber")
    host_name = data.get("host_name", "Hôte")

    room = new_room_data(name, room_type, host_phone, host_name, tid)
    room_id = rops.create_room(tid, room)
    _gamify(tid, "room_created")

    # Auto-join host
    rops.join_room(tid, room_id, host_phone)

    # Generate invite links for family members
    invite_links = {}
    if _redis_client:
        members = _redis_client.get_all_family_members(tid)
        secret = _JWT_SECRET
        for m in members:
            phone = m.get("phone", "")
            if phone and m.get("is_active") in ("1", "True", "true"):
                token = generate_member_token(phone, tid, secret)
                invite_links[m.get("name", phone)] = {
                    "phone": phone,
                    "token": token,
                    "url": f"/salon?room={room_id}&phone={phone}&token={token}",
                }

    return {
        "success": True,
        "room_id": room_id,
        "name": name,
        "type": room_type,
        "invite_links": invite_links,
    }


@app.get("/api/rooms/{room_id}")
async def get_room(room_id: str, request: Request):
    """Détails d'un salon."""
    import json as _json
    rops = _get_room_ops()
    if not rops:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})
    tid = getattr(request.state, "tenant_id", TENANT_ID)
    room = rops.get_room(tid, room_id)
    if not room:
        return JSONResponse(status_code=404, content={"error": "Salon introuvable"})

    participants = rops.get_participants(tid, room_id)
    members_info = []
    for p in participants:
        name = _get_member_name(tid, p)
        members_info.append({"phone": p, "name": name})

    messages = rops.get_messages(tid, room_id, limit=50)
    parsed_msgs = []
    for m in reversed(messages):
        try:
            parsed_msgs.append(_json.loads(m))
        except (_json.JSONDecodeError, TypeError):
            pass

    # Parse game_state JSON string to object
    result = dict(room)
    if result.get("game_state"):
        try:
            result["game_state"] = _json.loads(result["game_state"])
        except (_json.JSONDecodeError, TypeError):
            result["game_state"] = {}
    # Convert playback_time to number
    try:
        result["playback_time"] = float(result.get("playback_time", 0))
    except (ValueError, TypeError):
        result["playback_time"] = 0

    return {
        **result,
        "participants": members_info,
        "participant_count": len(participants),
        "messages": parsed_msgs,
    }


@app.post("/api/rooms/{room_id}/join")
async def join_room(room_id: str, request: Request):
    """Rejoindre un salon."""
    rops = _get_room_ops()
    if not rops:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})
    tid = getattr(request.state, "tenant_id", TENANT_ID)
    data = await request.json()
    phone = data.get("phone", "")

    room = rops.get_room(tid, room_id)
    if not room:
        return JSONResponse(status_code=404, content={"error": "Salon introuvable"})

    if not rops.join_room(tid, room_id, phone):
        return JSONResponse(status_code=400, content={"error": "Salon plein"})

    return {"success": True, "room_id": room_id}


@app.delete("/api/rooms/{room_id}")
async def delete_room(room_id: str, request: Request):
    """Fermer un salon (host uniquement)."""
    rops = _get_room_ops()
    if not rops:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})
    tid = getattr(request.state, "tenant_id", TENANT_ID)
    room = rops.get_room(tid, room_id)
    if not room:
        return JSONResponse(status_code=404, content={"error": "Salon introuvable"})

    # Verifier que le tenant est bien le proprietaire du salon
    room_tenant = int(room.get("tenant_id", 0))
    if room_tenant != tid:
        return JSONResponse(status_code=403, content={"error": "Seul le createur du salon peut le fermer"})

    rops.delete_room(tid, room_id)

    # Notify all connected
    await room_manager.broadcast(room_id, {
        "type": "system", "content": "Le salon a été fermé par l'hôte.",
    })

    return {"success": True}


@app.post("/api/rooms/{room_id}/invite")
async def invite_to_room(room_id: str, request: Request):
    """Invite un membre famille dans le salon par SMS."""
    rops = _get_room_ops()
    if not rops:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})
    tid = getattr(request.state, "tenant_id", TENANT_ID)
    room = rops.get_room(tid, room_id)
    if not room:
        return JSONResponse(status_code=404, content={"error": "Salon introuvable"})

    data = await request.json()
    phone = data.get("phone", "")
    member_name = data.get("name", "")
    if not phone:
        return JSONResponse(status_code=400, content={"error": "Numero requis"})

    if not sms_client or not sms_client.is_configured:
        return JSONResponse(status_code=503, content={"error": "Service SMS non disponible"})

    # Generate invite link
    secret = _JWT_SECRET
    token = generate_member_token(phone, tid, secret)
    base_url = os.getenv("LUNA_BASE_URL", "https://luna-beta-674304336025.europe-west1.run.app")
    invite_url = f"{base_url}/salon?room={room_id}&phone={phone}&token={token}"

    room_name = room.get("name", "Salon")
    host_name = room.get("host_name", "ton proche")
    sms_msg = f"[Luna] {host_name} t'invite dans le salon \"{room_name}\" ! Rejoins ici : {invite_url}"

    from integrations.twilio.sms_client import TwilioSMSClient
    normalized = TwilioSMSClient.normalize_phone(phone)
    success, details = _tracked_sms_send(normalized, sms_msg, label=f"Invitation salon a {member_name or phone}")

    if success:
        return {"success": True, "message": f"Invitation envoyee a {member_name or phone}"}
    else:
        logger.error(f"Room invite SMS failed: {details}")
        return JSONResponse(status_code=500, content={"error": "Echec de l'envoi du SMS"})


@app.get("/api/rooms/member-token")
async def get_member_token(request: Request):
    """Génère un token d'accès pour un membre famille (souscripteur only)."""
    tid = getattr(request.state, "tenant_id", TENANT_ID)
    phone = request.query_params.get("phone", "")
    if not phone:
        return JSONResponse(status_code=400, content={"error": "phone requis"})
    secret = _JWT_SECRET
    token = generate_member_token(phone, tid, secret)
    return {"phone": phone, "token": token}


@app.websocket("/api/rooms/{room_id}/ws")
async def room_websocket(websocket: WebSocket, room_id: str):
    """WebSocket temps réel pour un salon famille."""
    import json as _json
    await websocket.accept()

    rops = _get_room_ops()
    if not rops:
        await websocket.close(code=1011, reason="Redis non disponible")
        return

    tid = getattr(websocket.state, "tenant_id", TENANT_ID)

    # Auth: get phone + token from query params
    phone = websocket.query_params.get("phone", "")
    token = websocket.query_params.get("token", "")

    # Detect token type: JWT (contains dots) vs HMAC member token
    jwt_payload = None
    if token and "." in token:
        # Try JWT client token first
        jwt_payload = _decode_client_token(token)
        if jwt_payload:
            tid = jwt_payload.get("tenant_id", tid)
            # Use phone from query param, or email from JWT
            if not phone:
                phone = jwt_payload.get("email", "subscriber")
        else:
            await websocket.close(code=4001, reason="Token JWT invalide")
            return
    elif token:
        # HMAC member token
        if not phone:
            phone = "subscriber"
        secret = _JWT_SECRET
        if not verify_member_token(phone, tid, token, secret):
            await websocket.close(code=4001, reason="Token membre invalide")
            return
    else:
        # No token at all
        if not phone:
            phone = "subscriber"

    # Verify room exists
    room = rops.get_room(tid, room_id)
    if not room:
        await websocket.close(code=4004, reason="Salon introuvable")
        return

    # Get member name
    if jwt_payload:
        # For JWT-authenticated users, get name from profile
        _name = ""
        if _redis_client:
            _prof = _redis_client.get_profile(tid)
            if _prof:
                _name = _prof.get("first_name", "")
        name = _name or jwt_payload.get("email", "").split("@")[0] or "Hôte"
    else:
        name = _get_member_name(tid, phone) if phone != "subscriber" else "Hôte"

    # Join
    rops.join_room(tid, room_id, phone)
    await room_manager.connect(room_id, phone, websocket)

    # Announce join
    count = rops.count_participants(tid, room_id)
    await room_manager.broadcast(room_id, {
        "type": "join", "name": name, "phone": phone, "count": count,
    }, exclude_phone=phone)
    await room_manager.broadcast(room_id, {
        "type": "system", "content": f"{name} a rejoint le salon",
    }, exclude_phone=phone)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = _json.loads(raw)
            except (_json.JSONDecodeError, TypeError):
                continue

            # Refresh room data for each message
            current_room = rops.get_room(tid, room_id)
            if not current_room:
                await websocket.close(code=4004, reason="Salon fermé")
                break

            events = await room_manager.handle_message(
                room_id, phone, name, data, rops, tid, current_room
            )
            for ev in events:
                _gamify(tid, ev)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"Room WS error: {e}")
    finally:
        rops.leave_room(tid, room_id, phone)
        await room_manager.disconnect(room_id, phone)
        count = rops.count_participants(tid, room_id)
        await room_manager.broadcast(room_id, {
            "type": "leave", "name": name, "phone": phone, "count": count,
        })
        await room_manager.broadcast(room_id, {
            "type": "system", "content": f"{name} a quitté le salon",
        })


# =============================================================================
# SYNC - Notifications des autres canaux
# =============================================================================

@app.post("/api/sync/tavus")
async def sync_from_tavus(request: Request):
    """Tavus notifie la fin d'un appel visio"""
    if not tavus_client or not tavus_client.is_configured:
        return JSONResponse(status_code=503, content={"error": "Service visio non disponible"})
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    data = await request.json()
    # Le tenant_id peut venir du JWT (si appel client) ou du body (si callback serveur)
    tid = getattr(request.state, "tenant_id", None) or data.get("tenant_id", TENANT_ID)
    event = data.get("event", "")
    conversation_id = data.get("conversation_id", "")
    transcript = data.get("transcript", [])

    if event == "conversation.ended":
        # Ajouter les messages du transcript a l'historique unifie
        for entry in transcript:
            role = "luna" if entry.get("speaker") == "replica" else "subscriber"
            content = entry.get("text", "")
            if content:
                _add_unified_message("visio", role, content)

        # Mettre a jour la session
        _redis_client.update_session(tid, {
            "is_video_active": "0",
            "channel_session_id": "",
            "last_activity": datetime.utcnow().isoformat(),
        })

        # Track cout visio Tavus par tenant
        duration_sec = data.get("duration", 0)
        if not duration_sec and transcript:
            # Estimer la duree par le nombre de messages (~10s par message)
            duration_sec = len(transcript) * 10
        duration_min = max(1, duration_sec / 60)  # minimum 1 minute facturee
        try:
            cortex = get_cortex() if _CORTEX_AVAILABLE else None
            if cortex and hasattr(cortex, 'cost_tracker') and cortex.cost_tracker:
                await cortex.cost_tracker.track_tavus_tenant(tid, duration_min)
        except Exception:
            pass

        logger.info(f"Tavus conversation ended: {conversation_id}, {len(transcript)} messages synced")
        _gamify(tid, "visio_session")

    return {"success": True}


@app.post("/api/sync/twilio")
async def sync_from_twilio(request: Request):
    """Twilio notifie la fin d'un appel"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    data = await request.json()
    tid = getattr(request.state, "tenant_id", None) or data.get("tenant_id", TENANT_ID)
    call_sid = data.get("CallSid", "")
    call_status = data.get("CallStatus", "")
    from_number = data.get("From", "")
    transcript = data.get("transcript", "")

    if call_status == "completed":
        if transcript:
            _add_unified_message("call", "subscriber", f"[Appel Twilio] {transcript}")

        _redis_client.update_session(tid, {
            "active_channel": "app",
            "last_activity": datetime.utcnow().isoformat(),
        })

        logger.info(f"Twilio call ended: {call_sid}")

    return {"success": True}


# =============================================================================
# THEMES & PERSONNALISATION
# =============================================================================

# Import des presets de themes
try:
    from core.memory.schemas import (
        THEME_PRESETS, ThemePreset, UserThemePreferences,
        ThemeStyle, LunaAvatarStyle, FontSize, VoiceStyle
    )
    _THEMES_AVAILABLE = True
except ImportError:
    _THEMES_AVAILABLE = False
    THEME_PRESETS = {}


@app.get("/api/themes")
async def list_themes(age: int = None, gender: str = None):
    """Liste tous les themes disponibles, filtres optionnellement par age/genre"""
    themes = []
    for preset_id, preset in THEME_PRESETS.items():
        # Filtrage par age
        if age is not None:
            if preset.target_age_min and age < preset.target_age_min:
                continue
            if preset.target_age_max and age > preset.target_age_max:
                continue
        # Filtrage par genre
        if gender and preset.target_gender and preset.target_gender != gender:
            continue

        themes.append({
            "id": preset.id,
            "name": preset.name,
            "description": preset.description,
            "style": preset.style.value,
            "preview": {
                "primary_color": preset.primary_color,
                "secondary_color": preset.secondary_color,
                "accent_color": preset.accent_color,
                "background_type": preset.background_type,
                "background_value": preset.background_value,
                "dark_mode": preset.dark_mode,
            },
            "target": {
                "age_min": preset.target_age_min,
                "age_max": preset.target_age_max,
                "gender": preset.target_gender,
            }
        })

    return {
        "themes": themes,
        "count": len(themes),
        "filters_applied": {"age": age, "gender": gender},
    }


@app.get("/api/themes/suggest")
async def suggest_theme(age: int = None, gender: str = None):
    """Suggere le meilleur theme selon le profil"""
    best_match = None
    best_score = -1

    for preset_id, preset in THEME_PRESETS.items():
        score = 0

        # Score par age
        if age is not None:
            if preset.target_age_min and preset.target_age_max:
                if preset.target_age_min <= age <= preset.target_age_max:
                    score += 10
            elif preset.target_age_min and age >= preset.target_age_min:
                score += 5
            elif not preset.target_age_min and not preset.target_age_max:
                score += 2  # Theme universel

        # Score par genre
        if gender:
            if preset.target_gender == gender:
                score += 8
            elif not preset.target_gender:
                score += 3  # Theme unisexe

        if score > best_score:
            best_score = score
            best_match = preset

    if not best_match:
        best_match = THEME_PRESETS.get("zen")  # Default

    return {
        "suggested_theme": best_match.id if best_match else "zen",
        "theme_name": best_match.name if best_match else "Zen",
        "match_score": best_score,
        "profile": {"age": age, "gender": gender},
    }


@app.get("/api/themes/options")
async def get_theme_options():
    """Liste toutes les options de personnalisation disponibles"""
    return {
        "styles": [{"id": s.value, "name": s.value.title()} for s in ThemeStyle],
        "avatar_styles": [{"id": a.value, "name": a.value.replace("_", " ").title()} for a in LunaAvatarStyle],
        "voice_styles": [{"id": v.value, "name": v.value.title()} for v in VoiceStyle],
        "font_sizes": [{"id": f.value, "name": f.value.title()} for f in FontSize],
        "background_types": ["solid", "gradient", "image", "pattern"],
        "suggested_colors": {
            "primary": ["#6366F1", "#EC4899", "#0EA5E9", "#10B981", "#F59E0B", "#8B5CF6"],
            "secondary": ["#A5B4FC", "#F9A8D4", "#7DD3FC", "#6EE7B7", "#FCD34D", "#C4B5FD"],
            "accent": ["#F472B6", "#22D3EE", "#FACC15", "#A78BFA", "#FB923C", "#34D399"],
        }
    }


@app.get("/api/themes/{theme_id}")
async def get_theme_details(theme_id: str):
    """Recupere les details complets d'un theme"""
    preset = THEME_PRESETS.get(theme_id)
    if not preset:
        return JSONResponse(status_code=404, content={"error": "Theme non trouve"})

    return {
        "id": preset.id,
        "name": preset.name,
        "description": preset.description,
        "style": preset.style.value,
        "colors": {
            "primary": preset.primary_color,
            "secondary": preset.secondary_color,
            "accent": preset.accent_color,
        },
        "background": {
            "type": preset.background_type,
            "value": preset.background_value,
        },
        "dark_mode": preset.dark_mode,
        "avatar": {
            "style": preset.avatar_style.value,
        },
        "voice": {
            "style": preset.voice_style.value,
        },
        "typography": {
            "font_family": preset.font_family,
            "font_size": preset.font_size.value,
        },
        "assets": {
            "icon_pack": preset.icon_pack,
            "sounds_pack": preset.sounds_pack,
        },
        "target": {
            "age_min": preset.target_age_min,
            "age_max": preset.target_age_max,
            "gender": preset.target_gender,
        }
    }


@app.get("/api/profile/theme")
async def get_user_theme(request: Request, phone: str = None):
    """Recupere le theme actuel d'un utilisateur"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)

    user_phone = phone or ADMIN_NUMBER
    theme_data = _redis_client.get_user_theme(tid, user_phone)

    if not theme_data:
        # Retourner le theme par defaut
        default_preset = THEME_PRESETS.get("zen")
        return {
            "user_phone": user_phone,
            "preset_id": "zen",
            "preset_name": "Zen",
            "is_custom": False,
            "theme": {
                "primary_color": default_preset.primary_color,
                "secondary_color": default_preset.secondary_color,
                "accent_color": default_preset.accent_color,
                "background_type": default_preset.background_type,
                "background_value": default_preset.background_value,
                "dark_mode": default_preset.dark_mode,
                "avatar_style": default_preset.avatar_style.value,
                "voice_style": default_preset.voice_style.value,
                "font_size": default_preset.font_size.value,
            }
        }

    # Construire le theme effectif (preset + overrides)
    preset_id = theme_data.get("preset_id")
    preset = THEME_PRESETS.get(preset_id) if preset_id else None

    effective_theme = {}
    if preset:
        effective_theme = {
            "primary_color": preset.primary_color,
            "secondary_color": preset.secondary_color,
            "accent_color": preset.accent_color,
            "background_type": preset.background_type,
            "background_value": preset.background_value,
            "dark_mode": preset.dark_mode,
            "avatar_style": preset.avatar_style.value,
            "voice_style": preset.voice_style.value,
            "font_size": preset.font_size.value,
        }

    # Appliquer les overrides custom
    if theme_data.get("custom_primary_color"):
        effective_theme["primary_color"] = theme_data["custom_primary_color"]
    if theme_data.get("custom_secondary_color"):
        effective_theme["secondary_color"] = theme_data["custom_secondary_color"]
    if theme_data.get("custom_accent_color"):
        effective_theme["accent_color"] = theme_data["custom_accent_color"]
    if theme_data.get("custom_background_type"):
        effective_theme["background_type"] = theme_data["custom_background_type"]
    if theme_data.get("custom_background_value"):
        effective_theme["background_value"] = theme_data["custom_background_value"]
    if theme_data.get("custom_avatar_style"):
        effective_theme["avatar_style"] = theme_data["custom_avatar_style"]
    if theme_data.get("custom_voice_style"):
        effective_theme["voice_style"] = theme_data["custom_voice_style"]
    if theme_data.get("custom_font_size"):
        effective_theme["font_size"] = theme_data["custom_font_size"]
    if theme_data.get("dark_mode"):
        effective_theme["dark_mode"] = theme_data["dark_mode"] == "1"

    has_custom = any(theme_data.get(f"custom_{k}") for k in
                     ["primary_color", "secondary_color", "accent_color",
                      "background_type", "background_value", "avatar_style",
                      "voice_style", "font_size"])

    return {
        "user_phone": user_phone,
        "preset_id": preset_id,
        "preset_name": preset.name if preset else None,
        "is_custom": has_custom,
        "theme": effective_theme,
        "family_photos": theme_data.get("family_photos", "[]"),
    }


@app.post("/api/profile/theme")
async def set_user_theme(request: Request):
    """Definit le theme d'un utilisateur"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)
    data = await request.json()
    user_phone = data.get("phone", ADMIN_NUMBER)
    preset_id = data.get("preset_id")

    # Valider le preset si fourni
    if preset_id and preset_id not in THEME_PRESETS:
        return JSONResponse(status_code=400, content={
            "error": f"Theme inconnu: {preset_id}",
            "available_themes": list(THEME_PRESETS.keys())
        })

    # Construire les preferences
    prefs = UserThemePreferences(
        user_phone=user_phone,
        tenant_id=tid,
        preset_id=preset_id,
        custom_primary_color=data.get("primary_color"),
        custom_secondary_color=data.get("secondary_color"),
        custom_accent_color=data.get("accent_color"),
        custom_background_type=data.get("background_type"),
        custom_background_value=data.get("background_value"),
        custom_avatar_style=LunaAvatarStyle(data["avatar_style"]) if data.get("avatar_style") else None,
        custom_voice_style=VoiceStyle(data["voice_style"]) if data.get("voice_style") else None,
        custom_font_size=FontSize(data["font_size"]) if data.get("font_size") else None,
        dark_mode=data.get("dark_mode"),
        family_photos=data.get("family_photos", []),
    )

    _redis_client.set_user_theme(tid, user_phone, prefs.to_redis())

    # Publier evenement pour mise a jour temps reel
    _redis_client.publish_event(tid, "theme_changed", {
        "user_phone": user_phone,
        "preset_id": preset_id,
    })

    return {
        "success": True,
        "user_phone": user_phone,
        "preset_id": preset_id,
        "message": f"Theme {'personnalise' if not preset_id else THEME_PRESETS[preset_id].name} applique",
    }


@app.delete("/api/profile/theme")
async def reset_user_theme(request: Request, phone: str = None):
    """Remet le theme par defaut"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)

    user_phone = phone or ADMIN_NUMBER
    _redis_client.delete_user_theme(tid, user_phone)

    return {
        "success": True,
        "message": "Theme reinitialise (Zen par defaut)",
    }


# =============================================================================
# ASSISTANT PRO - Analyse, Generation, Iteration
# =============================================================================

# Import des modeles assistant
try:
    from core.memory.schemas import (
        AssistantTask, DocumentType, DocumentStatus, EmailDraft, ADMIN_TEMPLATES
    )
    _ASSISTANT_AVAILABLE = True
except ImportError:
    _ASSISTANT_AVAILABLE = False


@app.post("/api/assistant/analyze")
async def analyze_content(request: Request):
    """Analyse un document ou texte et retourne des insights"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)
    data = await request.json()
    content = data.get("content", "").strip()
    analysis_type = data.get("type", "general")  # general, contract, email, letter, cv

    if not content:
        return JSONResponse(status_code=400, content={"error": "content requis"})

    # Construire le prompt d'analyse
    prompts = {
        "general": "Analyse ce texte et fournis: 1) Resume en 2-3 phrases, 2) Points cles, 3) Suggestions d'amelioration.",
        "contract": "Analyse ce contrat et fournis: 1) Resume des obligations, 2) Points d'attention/risques, 3) Clauses importantes, 4) Recommandations.",
        "email": "Analyse cet email et fournis: 1) Ton utilise, 2) Points cles, 3) Suggestions pour ameliorer la clarte et l'impact.",
        "letter": "Analyse ce courrier et fournis: 1) Objectif du courrier, 2) Ton et formalite, 3) Points forts, 4) Ameliorations possibles.",
        "cv": "Analyse ce CV et fournis: 1) Points forts, 2) Points faibles, 3) Competences mises en avant, 4) Suggestions d'amelioration.",
    }

    prompt = prompts.get(analysis_type, prompts["general"])
    full_prompt = f"{prompt}\n\nTexte a analyser:\n\n{content}"

    try:
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Tu es un assistant d'analyse professionnelle. Reponds en francais de maniere structuree."},
                {"role": "user", "content": full_prompt}
            ],
            max_tokens=1500,
            temperature=0.3,
        )
        analysis = response.choices[0].message.content

        # Sauvegarder la tache
        task = AssistantTask(
            tenant_id=tid,
            task_type="analyze",
            input_text=content[:5000],
            analysis_result={"type": analysis_type, "analysis": analysis},
            status=DocumentStatus.APPROVED,
        )
        _redis_client.add_assistant_task(tid, task.id, task.to_redis())

        return {
            "success": True,
            "task_id": task.id,
            "analysis_type": analysis_type,
            "analysis": analysis,
        }

    except Exception as e:
        logger.error(f"Analysis error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/assistant/generate")
async def assistant_generate_document(request: Request):
    """Genere un document professionnel"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)
    data = await request.json()
    doc_type = data.get("type", "email")
    subject = data.get("subject", "")
    recipient = data.get("recipient", "")
    context = data.get("context", "")
    tone = data.get("tone", "professional")
    additional = data.get("additional_instructions", "")

    # Recuperer le profil pour personnalisation
    mgr = _get_tenant_manager(tid)
    profile = {}
    if mgr:
        p = mgr.get_subscriber_profile()
        if p:
            profile = p.model_dump()

    sender_name = f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip() or "L'expediteur"

    # Construire le prompt selon le type
    tone_map = {
        "professional": "professionnel et courtois",
        "formal": "tres formel et respectueux",
        "friendly": "amical mais professionnel",
        "casual": "decontracte",
    }
    tone_desc = tone_map.get(tone, "professionnel")

    if doc_type == "email":
        prompt = f"""Redige un email {tone_desc} en francais.
Sujet: {subject}
Destinataire: {recipient}
Contexte: {context}
{f'Instructions supplementaires: {additional}' if additional else ''}

Fournis:
1. L'objet de l'email (court)
2. Le corps de l'email (avec salutation et signature de {sender_name})"""

    elif doc_type == "cover_letter":
        prompt = f"""Redige une lettre de motivation {tone_desc} en francais.
Poste vise: {subject}
Entreprise: {recipient}
Contexte du candidat: {context}
{f'Instructions: {additional}' if additional else ''}

La lettre doit etre percutante et personnalisee."""

    elif doc_type == "cv":
        prompt = f"""Aide a rediger/ameliorer un CV en francais.
Poste cible: {subject}
Informations fournies: {context}
{f'Instructions: {additional}' if additional else ''}

Fournis un CV structure avec: Coordonnees, Profil, Experiences, Formation, Competences."""

    elif doc_type in ADMIN_TEMPLATES:
        template = ADMIN_TEMPLATES[doc_type]
        prompt = f"""Redige un(e) {template['name']} {tone_desc} en francais.
Destinataire: {template['recipient']}
Objet: {subject}
Details: {context}
{f'Instructions: {additional}' if additional else ''}

Utilise un format officiel et respectueux."""

    else:
        prompt = f"""Redige un document {tone_desc} en francais.
Type: {doc_type}
Sujet: {subject}
Destinataire: {recipient}
Contexte: {context}
{f'Instructions: {additional}' if additional else ''}"""

    try:
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Tu es un assistant de redaction professionnelle. Tu rediges des documents clairs, bien structures et adaptes au contexte."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7,
        )
        generated_text = response.choices[0].message.content

        # Sauvegarder la tache
        task = AssistantTask(
            tenant_id=tid,
            task_type="generate",
            document_type=DocumentType(doc_type) if doc_type in [e.value for e in DocumentType] else None,
            subject=subject,
            recipient=recipient,
            tone=tone,
            additional_instructions=additional,
            output_text=generated_text,
            status=DocumentStatus.DRAFT,
        )
        _redis_client.add_assistant_task(tid, task.id, task.to_redis())

        return {
            "success": True,
            "task_id": task.id,
            "document_type": doc_type,
            "version": 1,
            "status": "draft",
            "content": generated_text,
            "message": "Document genere. Utilisez /api/assistant/improve pour l'ameliorer.",
        }

    except Exception as e:
        logger.error(f"Generate error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/assistant/improve")
async def improve_document(request: Request):
    """Ameliore un document existant avec feedback"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)
    data = await request.json()
    task_id = data.get("task_id")
    feedback = data.get("feedback", "").strip()
    content = data.get("content")  # Optionnel: contenu modifie manuellement

    if not task_id:
        return JSONResponse(status_code=400, content={"error": "task_id requis"})

    if not feedback and not content:
        return JSONResponse(status_code=400, content={"error": "feedback ou content requis"})

    # Recuperer la tache originale
    original = _redis_client.get_assistant_task(tid, task_id)
    if not original:
        return JSONResponse(status_code=404, content={"error": "Tache non trouvee"})

    original_content = content or original.get("output_text", "")
    original_version = int(original.get("version", 1))

    prompt = f"""Voici un document a ameliorer:

---
{original_content}
---

Feedback de l'utilisateur: {feedback}

Ameliore le document en tenant compte du feedback. Garde le meme format et le meme ton general, sauf si le feedback demande un changement de ton."""

    try:
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "Tu es un assistant de redaction. Tu ameliores les documents selon le feedback sans changer leur essence."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.5,
        )
        improved_text = response.choices[0].message.content

        # Creer une nouvelle version
        new_task = AssistantTask(
            tenant_id=tid,
            task_type="improve",
            document_type=DocumentType(original["document_type"]) if original.get("document_type") else None,
            subject=original.get("subject"),
            recipient=original.get("recipient"),
            tone=original.get("tone", "professional"),
            input_text=original_content,
            output_text=improved_text,
            feedback=feedback,
            version=original_version + 1,
            parent_task_id=task_id,
            status=DocumentStatus.DRAFT,
        )
        _redis_client.add_assistant_task(tid, new_task.id, new_task.to_redis())

        return {
            "success": True,
            "task_id": new_task.id,
            "parent_task_id": task_id,
            "version": new_task.version,
            "status": "draft",
            "content": improved_text,
            "feedback_applied": feedback,
            "message": f"Version {new_task.version} generee.",
        }

    except Exception as e:
        logger.error(f"Improve error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/assistant/task/{task_id}")
async def get_task(task_id: str, request: Request):
    """Recupere une tache et son contenu"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)

    task = _redis_client.get_assistant_task(tid, task_id)
    if not task:
        return JSONResponse(status_code=404, content={"error": "Tache non trouvee"})

    return {
        "task": task,
        "content": task.get("output_text") or task.get("input_text"),
    }


@app.get("/api/assistant/task/{task_id}/versions")
async def get_task_versions(task_id: str, request: Request):
    """Recupere toutes les versions d'un document"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)

    versions = _redis_client.get_task_versions(tid, task_id)

    return {
        "original_task_id": task_id,
        "versions": versions,
        "count": len(versions),
    }


@app.post("/api/assistant/task/{task_id}/approve")
async def approve_task(task_id: str, request: Request):
    """Approuve un document (pret a envoyer/utiliser)"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)

    task = _redis_client.get_assistant_task(tid, task_id)
    if not task:
        return JSONResponse(status_code=404, content={"error": "Tache non trouvee"})

    _redis_client.update_assistant_task(tid, task_id, {
        "status": DocumentStatus.APPROVED.value,
        "updated_at": datetime.utcnow().isoformat(),
    })

    return {
        "success": True,
        "task_id": task_id,
        "status": "approved",
        "message": "Document approuve et pret a l'emploi.",
    }


@app.get("/api/assistant/tasks")
async def list_tasks(request: Request, limit: int = 20, doc_type: str = None):
    """Liste les dernieres taches"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)

    tasks = _redis_client.get_assistant_tasks(tid, limit=limit)

    if doc_type:
        tasks = [t for t in tasks if t.get("document_type") == doc_type]

    return {
        "tasks": tasks,
        "count": len(tasks),
    }


@app.get("/api/assistant/templates")
async def list_templates():
    """Liste les templates administratifs disponibles"""
    return {
        "templates": ADMIN_TEMPLATES,
        "document_types": [{"id": t.value, "name": t.value.replace("_", " ").title()} for t in DocumentType],
    }


# --- Email sending (placeholder - needs SMTP config) ---

@app.post("/api/email/draft")
async def create_email_draft(request: Request):
    """Cree un brouillon email a partir d'une tache"""
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    tid = getattr(request.state, "tenant_id", 1)
    data = await request.json()
    task_id = data.get("task_id")
    to = data.get("to", [])
    cc = data.get("cc", [])
    subject = data.get("subject", "")

    if not task_id and not data.get("body"):
        return JSONResponse(status_code=400, content={"error": "task_id ou body requis"})

    body = data.get("body", "")
    if task_id:
        task = _redis_client.get_assistant_task(tid, task_id)
        if task:
            body = task.get("output_text", "")
            subject = subject or task.get("subject", "")

    draft = EmailDraft(
        tenant_id=tid,
        to=to if isinstance(to, list) else [to],
        cc=cc if isinstance(cc, list) else [cc] if cc else [],
        subject=subject,
        body_html=body.replace("\n", "<br>"),
        body_text=body,
        task_id=task_id,
    )
    _redis_client.save_email_draft(tid, draft.id, draft.to_redis())

    return {
        "success": True,
        "draft_id": draft.id,
        "subject": subject,
        "to": draft.to,
        "message": "Brouillon cree. Configurez SMTP pour envoyer.",
    }


@app.post("/api/email/send")
async def send_email_endpoint(request: Request):
    """Envoie un email via Gmail OAuth (prioritaire) ou SendGrid (fallback)"""
    tid = getattr(request.state, "tenant_id", 1)

    data = await request.json()
    to = data.get("to", "")
    subject = data.get("subject", "")
    body = data.get("body", "")
    draft_id = data.get("draft_id")

    # Si draft_id fourni, charge le brouillon
    if draft_id and _redis_client:
        draft_data = _redis_client.get_email_draft(tid, draft_id)
        if draft_data:
            to = to or (draft_data.get("to", "") if isinstance(draft_data.get("to"), str) else ",".join(draft_data.get("to", [])))
            subject = subject or draft_data.get("subject", "")
            body = body or draft_data.get("body_text", "")

    if not to or not body:
        return JSONResponse(status_code=400, content={"error": "Destinataire (to) et contenu (body) requis"})

    success, details = await email_client.send_for_tenant(
        tenant_id=tid,
        redis_client=_redis_client,
        gmail_client=gmail_client,
        to=to,
        subject=subject or "Message via Luna",
        body_text=body,
        subscriber_name=_SUBSCRIBER_NAME,
    )

    if success:
        return {"success": True, "to": to, "subject": subject, "message": "Email envoye", "via": details.get("from", "sendgrid")}
    return JSONResponse(status_code=502, content={"error": "Echec envoi", "details": details})


# =========================================================================
# GMAIL OAUTH2 ENDPOINTS (per-tenant email)
# =========================================================================

@app.get("/api/email/oauth/start")
async def gmail_oauth_start(request: Request):
    """Demarre le flow OAuth2 Gmail pour un tenant. Admin only."""
    if not _verify_admin(request):
        return JSONResponse(status_code=401, content={"error": "Admin requis"})
    if not gmail_client.is_configured:
        return JSONResponse(status_code=501, content={
            "error": "Gmail OAuth non configure",
            "message": "Ajoutez GOOGLE_OAUTH_CLIENT_ID et GOOGLE_OAUTH_CLIENT_SECRET aux env vars.",
        })

    tenant_id = request.query_params.get("tenant_id")
    if not tenant_id:
        return JSONResponse(status_code=400, content={"error": "tenant_id requis en query param"})

    auth_url = gmail_client.get_auth_url(int(tenant_id))
    # Redirige directement vers Google
    from starlette.responses import RedirectResponse
    return RedirectResponse(url=auth_url)


@app.get("/api/email/oauth/callback")
async def gmail_oauth_callback(request: Request):
    """Callback OAuth2 Google. Stocke les tokens dans Redis."""
    code = request.query_params.get("code", "")
    state = request.query_params.get("state", "")
    error = request.query_params.get("error", "")

    if error:
        return JSONResponse(content={
            "success": False,
            "error": f"Google OAuth refuse: {error}",
        })

    if not code or not state:
        return JSONResponse(status_code=400, content={"error": "code et state requis"})

    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    result = await gmail_client.handle_callback(code, state, _redis_client)

    if result.get("success"):
        # Affiche une page de succes simple
        email = result.get("email", "")
        tid = result.get("tenant_id", "?")
        html = f"""<!DOCTYPE html><html><head><title>Luna - Gmail connecte</title>
        <style>body{{font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;background:#0a0a1a;color:#e0e0e0;}}
        .card{{background:#1e1e3f;padding:40px;border-radius:16px;text-align:center;}}
        .ok{{color:#4ade80;font-size:2em;}}h2{{color:#a78bfa;}}</style></head>
        <body><div class="card"><div class="ok">&#10003;</div>
        <h2>Gmail connecte !</h2><p>Compte: <strong>{email}</strong></p>
        <p>Tenant ID: {tid}</p>
        <p>Luna peut maintenant envoyer des emails depuis ce compte.</p>
        <p><a href="/admin" style="color:#a78bfa;">Retour au dashboard</a></p>
        </div></body></html>"""
        return HTMLResponse(content=html)
    else:
        error_msg = result.get("error", "Erreur inconnue")
        html = f"""<!DOCTYPE html><html><head><title>Luna - Erreur Gmail</title>
        <style>body{{font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;background:#0a0a1a;color:#e0e0e0;}}
        .card{{background:#1e1e3f;padding:40px;border-radius:16px;text-align:center;}}
        .err{{color:#f87171;font-size:2em;}}h2{{color:#f87171;}}</style></head>
        <body><div class="card"><div class="err">&#10007;</div>
        <h2>Erreur connexion Gmail</h2><p>{error_msg}</p>
        <p><a href="/admin" style="color:#a78bfa;">Retour au dashboard</a></p>
        </div></body></html>"""
        return HTMLResponse(content=html)


@app.get("/api/admin/clients/{tenant_id}/email")
async def admin_get_email_integration(tenant_id: int, request: Request):
    """Statut de l'integration email d'un tenant."""
    if not _verify_admin(request):
        return JSONResponse(status_code=401, content={"error": "Admin requis"})
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    integration = _redis_client.get_email_integration(tenant_id)
    if not integration:
        return {"connected": False, "service": None}

    return {
        "connected": True,
        "service": integration.get("service", "unknown"),
        "email": integration.get("email", ""),
        "connected_at": integration.get("connected_at", ""),
    }


@app.delete("/api/admin/clients/{tenant_id}/email")
async def admin_delete_email_integration(tenant_id: int, request: Request):
    """Deconnecte Gmail d'un tenant."""
    if not _verify_admin(request):
        return JSONResponse(status_code=401, content={"error": "Admin requis"})
    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    _redis_client.delete_email_integration(tenant_id)
    logger.info(f"Email integration deleted: tenant={tenant_id}")
    return {"success": True, "message": f"Integration email supprimee pour tenant {tenant_id}"}


# =========================================================================
# ADMIN DASHBOARD ENDPOINTS
# =========================================================================

_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
_server_start_time = time.time()


def _create_admin_token() -> str:
    """Cree un JWT admin valide 24h."""
    import jwt as pyjwt
    payload = {
        "role": "admin",
        "iat": int(time.time()),
        "exp": int(time.time()) + 86400,
    }
    return pyjwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


def _verify_admin(request: Request) -> bool:
    """Verifie le token admin dans le header Authorization."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    token = auth[7:]
    try:
        import jwt as pyjwt
        payload = pyjwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
        return payload.get("role") == "admin"
    except Exception:
        return False


# --- Certificat d'autonomie ---
_certificate_timestamp: float = 0  # timestamp de generation du certificat

def _generate_autonomy_certificate(pv_data: dict, reset_code: str) -> str:
    """Genere un certificat d'autonomie DOCX apres signature PV."""
    global _certificate_timestamp
    try:
        from docx import Document
        from docx.shared import Pt, Inches, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
    except ImportError:
        logger.error("python-docx non installe")
        return None

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    # Titre
    title = doc.add_heading("CERTIFICAT D'AUTONOMIE", level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle = doc.add_paragraph("YAWatch Luna")
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.runs[0].bold = True
    subtitle.runs[0].font.size = Pt(14)

    doc.add_paragraph("")

    # Identite exploitant
    doc.add_heading("Identite Exploitant", level=2)
    doc.add_paragraph(f"Nom / Raison sociale : {pv_data.get('exploitant_name', 'N/A')}")
    doc.add_paragraph(f"SIRET : {pv_data.get('exploitant_siret', 'N/A')}")

    try:
        from datetime import timezone as _tz
        sig_date = pv_data.get("date_signature", "")
        doc.add_paragraph(f"Date de signature : {sig_date}")
    except Exception:
        doc.add_paragraph(f"Date de signature : {pv_data.get('date_signature', 'N/A')}")

    doc.add_paragraph(f"Mode Luna : {pv_data.get('luna_mode', 'N/A')}")
    doc.add_paragraph(f"Version PV : {pv_data.get('version', 'N/A')}")

    # Resultats des phases
    doc.add_heading("Resultats de Recette", level=2)
    for phase_key, phase_label in [("phase_a", "Phase A - Technique"), ("phase_b", "Phase B - Legal"), ("phase_c", "Phase C - Operationnel")]:
        phase = pv_data.get(phase_key, {})
        passed = phase.get("all_passed", False)
        doc.add_paragraph(f"{phase_label} : {'[OK]' if passed else '[ECHEC]'}")

    # Hash PV
    doc.add_heading("Signature Numerique", level=2)
    doc.add_paragraph(f"SHA-256 : {pv_data.get('signature_hash', 'N/A')}")

    # RESET CODE
    doc.add_heading("CODE DE REINITIALISATION", level=2)
    warning = doc.add_paragraph("CONSERVEZ CE CODE EN LIEU SUR — Il ne sera plus jamais affiche.")
    warning.runs[0].bold = True
    warning.runs[0].font.color.rgb = RGBColor(204, 0, 0)

    code_para = doc.add_paragraph()
    code_run = code_para.add_run(reset_code)
    code_run.bold = True
    code_run.font.size = Pt(16)
    code_run.font.name = "Courier New"
    code_run.font.color.rgb = RGBColor(204, 0, 0)
    code_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph("")
    doc.add_paragraph(
        "Ce code permet de reinitialiser l'instance Luna en cas de besoin. "
        "Sans ce code, la reinitialisation est impossible. "
        "Commande : python tools/factory_reset.py --code <VOTRE_CODE>"
    )

    # Autonomie operationnelle
    doc.add_heading("Autonomie Operationnelle", level=2)
    doc.add_paragraph(
        "Ce certificat atteste que l'instance Luna est desormais autonome. "
        "Le fondateur n'a plus acces technique a cette instance. "
        "L'exploitant gere seul ses comptes API, son serveur et ses clients."
    )

    # Mise a jour
    doc.add_heading("Procedure de Mise a Jour", level=2)
    doc.add_paragraph("docker compose pull && docker compose up -d")
    doc.add_paragraph("Les mises a jour preservent toutes les donnees et la configuration.")

    # Mentions legales
    doc.add_heading("Mentions Legales", level=2)
    doc.add_paragraph(
        "Luna est un compagnon de lien social, PAS un dispositif medical. "
        "La detection de detresse est best-effort uniquement. "
        "L'exploitant doit recommander une teleassistance certifiee en complement."
    )

    # Sauvegarde
    cert_dir = Path(os.path.dirname(__file__)) / "data" / "certificates"
    cert_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"certificat_autonomie_{timestamp}.docx"
    cert_path = cert_dir / filename
    doc.save(str(cert_path))
    _certificate_timestamp = time.time()
    logger.info(f"Certificat d'autonomie genere: {cert_path}")
    return str(cert_path)


@app.get("/api/admin/certificate")
async def admin_certificate(request: Request):
    """Telecharge le certificat d'autonomie DOCX."""
    # Grace period: 10 minutes apres signature, accessible sans auth
    grace_period = _certificate_timestamp > 0 and (time.time() - _certificate_timestamp) < 600
    if not grace_period and not _verify_admin(request):
        return JSONResponse(status_code=401, content={"error": "Non autorise"})

    cert_dir = Path(os.path.dirname(__file__)) / "data" / "certificates"
    if not cert_dir.exists():
        return JSONResponse(status_code=404, content={"error": "Aucun certificat genere"})

    # Trouver le plus recent
    certs = sorted(cert_dir.glob("certificat_autonomie_*.docx"), reverse=True)
    if not certs:
        return JSONResponse(status_code=404, content={"error": "Aucun certificat genere"})

    return FileResponse(
        path=str(certs[0]),
        filename=certs[0].name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@app.post("/api/admin/login")
async def admin_login(request: Request):
    """Login admin avec mot de passe."""
    data = await request.json()
    password = data.get("password", "")

    if not _ADMIN_PASSWORD:
        return JSONResponse(status_code=503, content={
            "error": "ADMIN_PASSWORD non configure dans .env",
        })

    import hmac
    if not hmac.compare_digest(password, _ADMIN_PASSWORD):
        return JSONResponse(status_code=401, content={"error": "Mot de passe incorrect"})

    token = _create_admin_token()
    return {"token": token, "expires_in": 86400}


@app.get("/api/admin/dashboard")
async def admin_dashboard(request: Request):
    """Vue d'ensemble du dashboard admin."""
    if not _verify_admin(request):
        return JSONResponse(status_code=401, content={"error": "Non autorise"})

    uptime = time.time() - _server_start_time
    hours = int(uptime // 3600)
    minutes = int((uptime % 3600) // 60)

    result = {
        "server": {
            "status": "running",
            "uptime_seconds": int(uptime),
            "uptime_human": f"{hours}h {minutes}m",
            "luna_mode": LUNA_MODE,
            "pv_signed": PV_SIGNED,
        },
        "services": {
            "openai": bool(OPENAI_API_KEY),
            "twilio": bool(sms_client and hasattr(sms_client, 'is_configured') and sms_client.is_configured),
            "tavus": bool(tavus_client and tavus_client.is_configured) if tavus_client else False,
            "redis": bool(_redis_client and _redis_client.ping()) if _redis_client else False,
        },
        "clients_count": 0,
        "alerts_today": 0,
    }

    if _memory_manager:
        try:
            result["alerts_today"] = len(_memory_manager.get_alerts(limit=100, category="safety"))
        except Exception:
            pass
    if _redis_client:
        try:
            result["clients_count"] = len(_redis_client.get_all_tenant_ids())
        except Exception:
            pass

    return result


@app.get("/api/admin/clients")
async def admin_clients(request: Request):
    """Liste des clients (tenants) — lecture directe Redis, sans MemoryManager."""
    if not _verify_admin(request):
        return JSONResponse(status_code=401, content={"error": "Non autorise"})

    clients = []
    if _redis_client:
        try:
            tenant_ids = _redis_client.get_all_tenant_ids()
            for tid in tenant_ids:
                profile = _redis_client.get_profile(tid) or {}
                fn = profile.get("first_name", "")
                ln = profile.get("last_name", "")
                name = f"{fn} {ln}".strip() or f"Tenant {tid}"
                plan = profile.get("plan", "essentiel")
                # Lecture auth pour l'email
                auth = _redis_client.get_auth_by_tenant_id(tid)
                email = auth.get("email", "") if auth else ""
                clients.append({
                    "tenant_id": tid,
                    "name": name,
                    "email": email,
                    "plan": plan,
                })
        except Exception as e:
            logger.error(f"Admin clients error: {e}")

    return {"clients": clients, "total": len(clients)}


@app.get("/api/admin/clients/{tenant_id}")
async def admin_client_detail(tenant_id: int, request: Request):
    """Detail d'un client."""
    if not _verify_admin(request):
        return JSONResponse(status_code=401, content={"error": "Non autorise"})

    if not _redis_client or not _CORE_AVAILABLE:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    try:
        mm = MemoryManager(tenant_id=tenant_id, redis_client=_redis_client)
        profile = mm.get_subscriber_profile()
        quota = mm.get_quota_status()
        contacts = mm.list_trusted_contacts()
        stats = mm.get_daily_stats_range(7)
        return {
            "profile": profile.dict() if profile else None,
            "quota": quota,
            "contacts": [c.dict() for c in contacts] if contacts else [],
            "daily_stats": stats,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/admin/clients")
async def admin_create_client(request: Request):
    """Admin: cree un client manuellement."""
    if not _verify_admin(request):
        return JSONResponse(status_code=401, content={"error": "Non autorise"})

    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    data = await request.json()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    first_name = data.get("first_name", "")
    last_name = data.get("last_name", "")
    plan = data.get("plan", "essentiel").lower()

    if not email or "@" not in email:
        return JSONResponse(status_code=400, content={"error": "Email invalide"})
    if len(password) < 6:
        return JSONResponse(status_code=400, content={"error": "Mot de passe trop court (min 6)"})
    if plan not in ("essentiel", "confort", "premium"):
        return JSONResponse(status_code=400, content={"error": "Plan invalide"})

    if _redis_client.get_auth_by_email(email):
        return JSONResponse(status_code=409, content={"error": "Email deja utilise"})

    tenant_id = _redis_client.get_next_tenant_id()
    password_hash = _hash_password(password)

    created = _redis_client.create_auth_record(email, password_hash, tenant_id, plan)
    if not created:
        return JSONResponse(status_code=409, content={"error": "Email deja utilise"})

    # Create profile
    if _CORE_AVAILABLE:
        profile = SubscriberProfile(
            tenant_id=tenant_id,
            first_name=first_name or email.split("@")[0],
            last_name=last_name,
            email=email,
        )
        mgr = _get_tenant_manager(tenant_id)
        mgr.set_subscriber_profile(profile)

    logger.info(f"ADMIN_CREATE_CLIENT tenant_id={tenant_id} email={email} plan={plan}")
    _gamify("admin", "new_client", is_admin=True)

    return {"success": True, "tenant_id": tenant_id, "email": email, "plan": plan}


@app.patch("/api/admin/clients/{tenant_id}")
async def admin_update_client(tenant_id: int, request: Request):
    """Admin: modifie le plan ou le statut d'un client."""
    if not _verify_admin(request):
        return JSONResponse(status_code=401, content={"error": "Non autorise"})

    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    auth = _redis_client.get_auth_by_tenant_id(tenant_id)
    if not auth:
        return JSONResponse(status_code=404, content={"error": "Client introuvable"})

    data = await request.json()
    updates = {}

    if "plan" in data:
        plan = data["plan"].lower()
        if plan not in ("essentiel", "confort", "premium"):
            return JSONResponse(status_code=400, content={"error": "Plan invalide"})
        updates["plan"] = plan
        # Evict from tenant manager cache
        if tenant_id in _tenant_managers:
            del _tenant_managers[tenant_id]

    if "active" in data:
        updates["active"] = bool(data["active"])

    if not updates:
        return JSONResponse(status_code=400, content={"error": "Aucune modification"})

    email = auth.get("email", "")
    _redis_client.update_auth_record(email, updates)
    logger.info(f"ADMIN_UPDATE_CLIENT tenant_id={tenant_id} updates={updates}")
    return {"success": True, "tenant_id": tenant_id, "updates": updates}


@app.delete("/api/admin/clients/{tenant_id}")
async def admin_delete_client(tenant_id: int, request: Request):
    """Admin: supprime un client (purge complete de toutes ses donnees Redis)."""
    if not _verify_admin(request):
        return JSONResponse(status_code=401, content={"error": "Non autorise"})

    if not _redis_client:
        return JSONResponse(status_code=503, content={"error": "Service temporairement indisponible"})

    if tenant_id == _PROPRIO_TENANT_ID:
        return JSONResponse(status_code=403, content={"error": "Impossible de supprimer le compte fondateur"})

    # Supprimer l'auth record
    auth = _redis_client.get_auth_by_tenant_id(tenant_id)
    if auth:
        email = auth.get("email", "")
        auth_key = f"{_redis_client.prefix}:auth:{email}"
        _redis_client.client.delete(auth_key)

    # Purger toutes les cles du tenant
    keys_deleted = _redis_client.purge_tenant(tenant_id)
    logger.info(f"ADMIN_DELETE_CLIENT tenant_id={tenant_id} keys_deleted={keys_deleted}")
    return {"success": True, "tenant_id": tenant_id, "keys_deleted": keys_deleted}


@app.get("/api/admin/quotas")
async def admin_quotas(request: Request):
    """Quotas de tous les clients — lecture legere + usage reel Cortex."""
    if not _verify_admin(request):
        return JSONResponse(status_code=401, content={"error": "Non autorise"})

    quotas = []
    if _redis_client:
        try:
            # Usage reel Cortex (un seul appel pour tous les tenants)
            all_usage = {}
            cortex = get_cortex() if _CORTEX_AVAILABLE else None
            if cortex and hasattr(cortex, "cost_tracker") and cortex.cost_tracker:
                all_usage = await cortex.cost_tracker.get_month_costs_per_tenant()

            for tid in _redis_client.get_all_tenant_ids():
                profile = _redis_client.get_profile(tid) or {}
                name = profile.get("first_name", f"Tenant {tid}")
                plan = profile.get("plan", "essentiel")
                limits = _PLAN_LIMITS.get(plan, _PLAN_LIMITS["essentiel"])
                usage = all_usage.get(str(tid), {"sms_count": 0, "voice_minutes": 0, "tavus_minutes": 0})
                quotas.append({
                    "tenant_id": tid,
                    "name": name,
                    "plan": plan,
                    "sms": {"used": usage.get("sms_count", 0), "limit": limits["sms"]},
                    "voice": {"used": round(usage.get("voice_minutes", 0), 1), "limit": limits["voice_min"]},
                    "visio": {"used": round(usage.get("tavus_minutes", 0), 1), "limit": limits["visio_min"]},
                })
        except Exception as e:
            logger.error(f"Admin quotas error: {e}")

    return {"quotas": quotas}


@app.get("/api/admin/alerts")
async def admin_alerts(request: Request, limit: int = 50, category: str = None):
    """Evenements et alertes."""
    if not _verify_admin(request):
        return JSONResponse(status_code=401, content={"error": "Non autorise"})

    if not _memory_manager:
        return {"alerts": [], "counts": {}}

    alerts = _memory_manager.get_alerts(limit=limit, category=category)

    # Compter par categorie
    counts = {}
    for a in alerts:
        cat = a.get("category", "unknown")
        counts[cat] = counts.get(cat, 0) + 1

    return {"alerts": alerts, "counts": counts, "total": len(alerts)}


@app.get("/api/admin/health")
async def admin_health(request: Request):
    """Sante detaillee du serveur."""
    if not _verify_admin(request):
        return JSONResponse(status_code=401, content={"error": "Non autorise"})

    uptime = time.time() - _server_start_time
    result = {
        "uptime_seconds": int(uptime),
        "luna_mode": LUNA_MODE,
        "pv_signed": PV_SIGNED,
        "services": {
            "openai": {"status": "ok" if OPENAI_API_KEY else "missing", "model": OPENAI_MODEL},
            "twilio": {"status": "ok" if (sms_client and hasattr(sms_client, 'is_configured') and sms_client.is_configured) else "not_configured"},
            "tavus": {"status": "ok" if (tavus_client and tavus_client.is_configured) else "not_configured"} if LUNA_MODE == "full" else {"status": "skipped"},
            "redis": {"status": "offline"},
        },
        "core_modules": {
            "memory": bool(_memory_manager),
            "safety": bool(_safety_guardian),
            "quota": bool(_quota_guard),
            "scheduler": bool(_scheduler),
            "executor": bool(_executor),
        },
    }

    if _redis_client:
        try:
            result["services"]["redis"] = _redis_client.get_info()
        except Exception:
            pass

    return result


@app.get("/api/admin/revenue")
async def admin_revenue(request: Request):
    """Estimation CA — lecture directe Redis."""
    if not _verify_admin(request):
        return JSONResponse(status_code=401, content={"error": "Non autorise"})

    plan_prices = {"essentiel": 79, "confort": 149, "premium": 249}
    by_plan = {p: {"count": 0, "revenue": 0} for p in plan_prices}
    total = 0

    if _redis_client:
        try:
            for tid in _redis_client.get_all_tenant_ids():
                profile = _redis_client.get_profile(tid) or {}
                plan = profile.get("plan", "essentiel")
                if plan in by_plan:
                    by_plan[plan]["count"] += 1
                    by_plan[plan]["revenue"] += plan_prices.get(plan, 0)
                    total += plan_prices.get(plan, 0)
        except Exception as e:
            logger.error(f"Admin revenue error: {e}")

    return {"total_revenue": total, "by_plan": by_plan, "currency": "EUR"}


if __name__ == "__main__":
    import uvicorn
    import subprocess as _sp

    _is_cloudrun = os.getenv("ENVIRONMENT", "").lower() == "cloudrun"
    port = int(os.getenv("PORT", os.getenv("LUNA_PORT", "8080" if _is_cloudrun else "8888")))

    ssl_kwargs = {}
    if not _is_cloudrun:
        # Local/Docker: SSL auto-signe
        ssl_dir = os.path.dirname(__file__)
        cert_file = os.getenv("SSL_CERTFILE", os.path.join(ssl_dir, "cert.pem"))
        key_file = os.getenv("SSL_KEYFILE", os.path.join(ssl_dir, "key.pem"))

        if not os.path.exists(cert_file) or not os.path.exists(key_file):
            logger.info("Certificats SSL absents - generation auto-signee...")
            try:
                _sp.run([
                    "openssl", "req", "-x509", "-newkey", "rsa:4096",
                    "-keyout", key_file, "-out", cert_file,
                    "-days", "365", "-nodes",
                    "-subj", "/CN=localhost/O=YAWatch-Luna",
                ], check=True, capture_output=True)
                logger.info("Certificats SSL generes (auto-signes, 1 an)")
            except Exception as e:
                logger.error(f"Impossible de generer les certificats SSL: {e}")

        ssl_kwargs = {"ssl_keyfile": key_file, "ssl_certfile": cert_file}
    else:
        logger.info("Cloud Run detecte — SSL desactive (gere par Google)")

    logger.info(f"Demarrage Luna Web - YAWatch-Luna (Souscripteur: {_SUBSCRIBER_NAME})")
    logger.info(f"Mode: {LUNA_MODE.upper()}" + (" (chat + voix + SMS)" if LUNA_MODE == "lite" else " (chat + voix + SMS + visio)"))
    logger.info(f"Environnement: {'CLOUD RUN' if _is_cloudrun else 'LOCAL/DOCKER'}")
    logger.info(f"PV Recette: {'SIGNE' if PV_SIGNED else 'NON SIGNE - MODE SETUP'}")
    logger.info(f"OpenAI: {'OK' if OPENAI_API_KEY else 'MANQUANT'}")
    _twilio_ok = sms_client and hasattr(sms_client, 'is_configured') and sms_client.is_configured
    logger.info(f"Twilio: {'OK' if _twilio_ok else 'NON CONFIGURE'}")
    logger.info(f"Tavus: {'OK' if (tavus_client and tavus_client.is_configured) else 'NON CONFIGURE'}" + (" (mode lite - skip)" if LUNA_MODE == "lite" else ""))
    logger.info(f"Simli: {'OK' if (_SIMLI_AVAILABLE and os.getenv('SIMLI_API_KEY')) else 'NON CONFIGURE'}")
    logger.info(f"Redis/Memory: {'OK' if _memory_manager else 'OFFLINE'}")
    logger.info(f"Safety Guardian: {'OK' if _safety_guardian else 'OFFLINE'}")
    logger.info(f"Quota Guard: {'OK' if _quota_guard else 'OFFLINE'}")
    logger.info(f"Scheduler: {'OK' if _scheduler else 'OFFLINE'}")
    logger.info(f"Executor: {'OK' if _executor else 'OFFLINE'}")
    if _pv_locked:
        logger.info(f"Setup AI: {'OK' if SETUP_OPENAI_API_KEY else 'MANQUANT (SETUP_OPENAI_API_KEY)'}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        **ssl_kwargs,
    )
