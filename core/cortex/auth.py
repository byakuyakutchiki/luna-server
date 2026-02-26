"""
CORTEX AUTH — Authentification multi-couche.

3 methodes pour prouver que c'est bien toi:

1. TOTP (Google Authenticator)
   - Secret genere une seule fois, stocke dans data/cortex_totp.secret
   - QR code affiche au premier lancement
   - Code 6 chiffres qui change toutes les 30 secondes
   - Meme si quelqu'un vole ton numero, il peut pas generer le TOTP
     sans avoir ton telephone PHYSIQUE

2. Telegram User ID
   - Ton user_id Telegram est unique et infalsifiable
   - Pas de SIM swap possible sur Telegram
   - Le bot ne repond qu'a TON user_id

3. API Key (pour CLI / VM)
   - Cle pre-partagee stockee dans data/cortex_api.key
   - Utilisee par luna-ctl depuis ta VM
   - Envoyee dans le header X-Cortex-Key

Niveaux d'acces:
   - READ: status, health, clients, logs (TOTP OU Telegram OU API key)
   - WRITE: ban, unban, kill, revive (TOTP obligatoire)
   - CRITICAL: lock, unlock, shield, restart (TOTP + confirmation)
"""

import hashlib
import hmac
import io
import json
import logging
import os
import secrets
import time
from pathlib import Path
from typing import Optional

import pyotp
import qrcode

logger = logging.getLogger("cortex.auth")

# Niveaux de commande
LEVEL_READ = "read"
LEVEL_WRITE = "write"
LEVEL_CRITICAL = "critical"

# Commandes par niveau
COMMAND_LEVELS = {
    # READ — juste consulter
    "STATUS": LEVEL_READ,
    "HEALTH": LEVEL_READ,
    "CLIENTS": LEVEL_READ,
    "QUOTA": LEVEL_READ,
    "THREATS": LEVEL_READ,
    "BANNED": LEVEL_READ,
    "LOGS": LEVEL_READ,
    "ERRORS": LEVEL_READ,
    "CORTEX": LEVEL_READ,
    "HELP": LEVEL_READ,
    "DIGEST": LEVEL_READ,
    "PING": LEVEL_READ,
    "UPTIME": LEVEL_READ,
    "REDIS": LEVEL_READ,
    "CONFIG": LEVEL_READ,
    "WHITELIST": LEVEL_READ,
    "SESSIONS": LEVEL_READ,
    "PROCESSES": LEVEL_READ,
    "NETWORK": LEVEL_READ,
    "DISK": LEVEL_READ,
    "VERSION": LEVEL_READ,
    "AUDIT": LEVEL_READ,
    "COUTS": LEVEL_READ,
    "CLIENT": LEVEL_READ,
    # WRITE — modifier quelque chose
    "EXPORT": LEVEL_WRITE,
    "BAN": LEVEL_WRITE,
    "UNBAN": LEVEL_WRITE,
    "KILL": LEVEL_WRITE,
    "REVIVE": LEVEL_WRITE,
    "BACKUP": LEVEL_WRITE,
    "MAINTENANCE": LEVEL_WRITE,
    "ANNOUNCE": LEVEL_WRITE,
    "WHITELIST_ADD": LEVEL_WRITE,
    "WHITELIST_DEL": LEVEL_WRITE,
    "QUOTA_SET": LEVEL_WRITE,
    "QUOTA_RESET": LEVEL_WRITE,
    "MSG": LEVEL_WRITE,
    "PURGE": LEVEL_WRITE,
    "RATELIMIT": LEVEL_WRITE,
    "REGISTER": LEVEL_WRITE,
    "PLAN_SET": LEVEL_WRITE,
    "BROADCAST": LEVEL_WRITE,
    # CRITICAL — danger, peut casser le serveur
    "LOCK": LEVEL_CRITICAL,
    "UNLOCK": LEVEL_CRITICAL,
    "SHIELD": LEVEL_CRITICAL,
    "RESTART": LEVEL_CRITICAL,
    "STOP": LEVEL_CRITICAL,
    "REKEY": LEVEL_CRITICAL,
    "WIPE": LEVEL_CRITICAL,
}


class CortexAuth:
    """Gestionnaire d'authentification multi-couche du Cortex."""

    # Cles Redis pour persistance Cloud Run
    REDIS_KEY_TOTP = "cortex:auth:totp_secret"
    REDIS_KEY_API_HASH = "cortex:auth:api_key_hash"
    REDIS_KEY_TELEGRAM = "cortex:auth:telegram_users"

    def __init__(self, data_dir: str = ""):
        if not data_dir:
            data_dir = str(Path(__file__).parent.parent.parent / "data")
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)

        # Redis client (injecte via async_init)
        self._redis = None

        # Fichiers secrets
        self._totp_file = self._data_dir / "cortex_totp.secret"
        self._api_key_file = self._data_dir / "cortex_api.key"
        self._telegram_file = self._data_dir / "cortex_telegram.json"

        # TOTP
        self._totp_secret: Optional[str] = None
        self._totp: Optional[pyotp.TOTP] = None

        # API Key
        self._api_key_hash: Optional[str] = None

        # Telegram user IDs autorises {user_id: role}
        self._telegram_users: dict[int, str] = {}

        # Sessions actives (pour SMS: phone -> {auth_time, totp_verified})
        self._sessions: dict[str, dict] = {}

        # Init synchrone (fichiers + env vars)
        self._load_or_create_totp()
        self._load_or_create_api_key()
        self._load_telegram_users()

    async def async_init(self, redis_client=None):
        """
        Init async: charge les secrets depuis Redis (prioritaire).
        Appele par brain.py apres construction.
        Permet de persister TOTP, API key et Telegram users
        sur Cloud Run ou le filesystem est ephemere.
        """
        if not redis_client:
            return
        self._redis = redis_client
        try:
            # 1. TOTP secret depuis Redis
            stored_totp = await redis_client.get(self.REDIS_KEY_TOTP)
            if stored_totp:
                secret = stored_totp if isinstance(stored_totp, str) else stored_totp.decode()
                self._totp_secret = secret.strip()
                self._totp = pyotp.TOTP(self._totp_secret)
                logger.info("TOTP charge depuis Redis (persistant)")
            elif self._totp_secret:
                # Sauver le secret actuel dans Redis
                await redis_client.set(self.REDIS_KEY_TOTP, self._totp_secret)
                logger.info("TOTP sauvegarde dans Redis pour persistance")

            # 2. API key hash depuis Redis
            stored_hash = await redis_client.get(self.REDIS_KEY_API_HASH)
            if stored_hash:
                self._api_key_hash = stored_hash if isinstance(stored_hash, str) else stored_hash.decode()
                logger.info("API key hash charge depuis Redis (persistant)")
            elif self._api_key_hash:
                await redis_client.set(self.REDIS_KEY_API_HASH, self._api_key_hash)
                logger.info("API key hash sauvegarde dans Redis pour persistance")

            # 3. Telegram users depuis Redis
            stored_tg = await redis_client.get(self.REDIS_KEY_TELEGRAM)
            if stored_tg:
                tg_data = stored_tg if isinstance(stored_tg, str) else stored_tg.decode()
                data = json.loads(tg_data)
                self._telegram_users = {
                    int(k): v for k, v in data.get("users", {}).items()
                }
                logger.info(f"Telegram users charges depuis Redis: "
                            f"{len(self._telegram_users)} utilisateurs")
            elif self._telegram_users:
                await self._save_telegram_to_redis()
                logger.info("Telegram users sauvegardes dans Redis")

        except Exception as e:
            logger.error(f"Erreur async_init Redis auth: {e}")

    async def _save_telegram_to_redis(self):
        """Sauvegarde les Telegram users dans Redis."""
        if not self._redis:
            return
        try:
            data = json.dumps({
                "users": {str(k): v for k, v in self._telegram_users.items()},
                "last_updated": time.time(),
            })
            await self._redis.set(self.REDIS_KEY_TELEGRAM, data)
        except Exception as e:
            logger.debug(f"Erreur sauvegarde Telegram Redis: {e}")

    # ──────────────────────────────────────────
    # TOTP (Google Authenticator)
    # ──────────────────────────────────────────

    def _load_or_create_totp(self):
        """Charge ou genere le secret TOTP."""
        # 1. Variable d'environnement (Cloud Run / production)
        env_secret = os.getenv("CORTEX_TOTP_SECRET", "")
        if env_secret:
            self._totp_secret = env_secret.strip()
            self._totp = pyotp.TOTP(self._totp_secret)
            logger.info("TOTP charge depuis env CORTEX_TOTP_SECRET")
            return

        # 2. Fichier local
        if self._totp_file.exists():
            try:
                self._totp_secret = self._totp_file.read_text().strip()
                self._totp = pyotp.TOTP(self._totp_secret)
                logger.info("TOTP charge depuis cortex_totp.secret")
                return
            except Exception as e:
                logger.error(f"Erreur lecture TOTP: {e}")

        # 3. Generer un nouveau secret
        self._totp_secret = pyotp.random_base32()
        self._totp = pyotp.TOTP(self._totp_secret)
        try:
            self._totp_file.write_text(self._totp_secret)
            os.chmod(self._totp_file, 0o600)
        except Exception:
            pass  # Cloud Run: filesystem read-only possible
        logger.warning("NOUVEAU secret TOTP genere — scannez le QR code!")

    def get_totp_uri(self, account_name: str = "Luna Cortex",
                     issuer: str = "YAWatch") -> str:
        """URI pour QR code Google Authenticator."""
        if not self._totp:
            return ""
        return self._totp.provisioning_uri(
            name=account_name, issuer_name=issuer)

    def get_totp_qr_text(self) -> str:
        """QR code en ASCII art pour le terminal."""
        uri = self.get_totp_uri()
        if not uri:
            return "TOTP non configure"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=1,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        # Generer en texte
        buffer = io.StringIO()
        qr.print_ascii(out=buffer)
        return buffer.getvalue()

    def get_totp_qr_png(self) -> Optional[bytes]:
        """QR code en PNG (pour affichage web)."""
        uri = self.get_totp_uri()
        if not uri:
            return None
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def verify_totp(self, code: str) -> bool:
        """Verifie un code TOTP (accepte +-1 fenetre de 30s)."""
        if not self._totp:
            return False
        code = code.strip().replace(" ", "")
        if not code.isdigit() or len(code) != 6:
            return False
        return self._totp.verify(code, valid_window=1)

    def get_current_totp(self) -> str:
        """Code TOTP actuel (pour debug/test seulement)."""
        if not self._totp:
            return ""
        return self._totp.now()

    # ──────────────────────────────────────────
    # API KEY (pour CLI depuis la VM)
    # ──────────────────────────────────────────

    def _load_or_create_api_key(self):
        """Charge ou genere la cle API."""
        # 1. Variable d'environnement (Cloud Run / production)
        env_hash = os.getenv("CORTEX_API_KEY_HASH", "")
        if env_hash:
            self._api_key_hash = env_hash.strip()
            logger.info("API key hash charge depuis env CORTEX_API_KEY_HASH")
            return

        # 2. Fichier local
        if self._api_key_file.exists():
            try:
                data = json.loads(self._api_key_file.read_text())
                self._api_key_hash = data.get("hash")
                logger.info("API key chargee depuis cortex_api.key")
                return
            except Exception as e:
                logger.error(f"Erreur lecture API key: {e}")

        # 3. Generer une nouvelle cle
        raw_key = secrets.token_urlsafe(48)  # 64 chars
        self._api_key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        try:
            self._api_key_file.write_text(json.dumps({
                "hash": self._api_key_hash,
                "created": time.time(),
                "note": "Cle API Cortex — utilisee par luna-ctl",
            }))
            os.chmod(self._api_key_file, 0o600)
        except Exception:
            pass  # Cloud Run: filesystem peut etre read-only
        logger.warning(f"NOUVELLE cle API generee: {raw_key}")
        self._new_api_key = raw_key

    def verify_api_key(self, key: str) -> bool:
        """Verifie une cle API."""
        if not self._api_key_hash or not key:
            return False
        key_hash = hashlib.sha256(key.strip().encode()).hexdigest()
        return hmac.compare_digest(key_hash, self._api_key_hash)

    def get_new_api_key(self) -> Optional[str]:
        """Retourne la cle API si elle vient d'etre generee (affichee 1 fois)."""
        key = getattr(self, "_new_api_key", None)
        if key:
            self._new_api_key = None  # Plus jamais
        return key

    def regenerate_api_key(self) -> str:
        """Regenere la cle API (invalide l'ancienne)."""
        raw_key = secrets.token_urlsafe(48)
        self._api_key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        try:
            self._api_key_file.write_text(json.dumps({
                "hash": self._api_key_hash,
                "created": time.time(),
                "note": "Cle API Cortex regeneree",
            }))
            os.chmod(self._api_key_file, 0o600)
        except Exception:
            pass
        # Persister dans Redis
        if self._redis:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(
                        self._redis.set(self.REDIS_KEY_API_HASH,
                                        self._api_key_hash))
            except Exception:
                pass
        logger.warning("Cle API Cortex REGENEREE")
        return raw_key

    # ──────────────────────────────────────────
    # TELEGRAM USER ID
    # ──────────────────────────────────────────

    def _load_telegram_users(self):
        """Charge les user IDs Telegram autorises."""
        if self._telegram_file.exists():
            try:
                data = json.loads(self._telegram_file.read_text())
                self._telegram_users = {
                    int(k): v for k, v in data.get("users", {}).items()
                }
                logger.info(
                    f"Telegram: {len(self._telegram_users)} utilisateurs autorises")
                return
            except Exception as e:
                logger.error(f"Erreur lecture Telegram users: {e}")
        self._telegram_users = {}
        # Fallback: FOUNDER_TELEGRAM_CHAT_ID env var (Cloud Run)
        founder_id = os.getenv("FOUNDER_TELEGRAM_CHAT_ID", "")
        if founder_id and founder_id.isdigit():
            self._telegram_users[int(founder_id)] = "founder"
            logger.info(f"Telegram founder pre-enregistre: {founder_id}")

    def register_telegram_user(self, user_id: int, role: str = "founder",
                                username: str = "") -> bool:
        """Enregistre un user ID Telegram (necessite TOTP pour confirmer)."""
        self._telegram_users[user_id] = role
        self._save_telegram_users(username)
        # Async: sauver dans Redis aussi (fire-and-forget via event loop)
        if self._redis:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._save_telegram_to_redis())
            except Exception:
                pass
        return True

    def _save_telegram_users(self, last_username: str = ""):
        """Sauvegarde les users Telegram (fichier local)."""
        data = {
            "users": {str(k): v for k, v in self._telegram_users.items()},
            "last_updated": time.time(),
            "last_username": last_username,
        }
        try:
            self._telegram_file.write_text(json.dumps(data, indent=2))
            os.chmod(self._telegram_file, 0o600)
        except Exception:
            pass  # Cloud Run: filesystem peut etre read-only

    def verify_telegram_user(self, user_id: int) -> Optional[str]:
        """
        Verifie un user ID Telegram.
        Retourne le role ('founder', 'exploitant') ou None.
        """
        return self._telegram_users.get(user_id)

    def get_telegram_users(self) -> dict[int, str]:
        return dict(self._telegram_users)

    # ──────────────────────────────────────────
    # SESSIONS (pour SMS)
    # ──────────────────────────────────────────

    def create_session(self, identifier: str, role: str,
                        method: str = "sms") -> dict:
        """Cree une session apres auth reussie."""
        session = {
            "role": role,
            "method": method,
            "auth_time": time.time(),
            "totp_verified": False,
            "totp_time": 0,
        }
        self._sessions[identifier] = session
        return session

    def get_session(self, identifier: str) -> Optional[dict]:
        """Recupere une session."""
        session = self._sessions.get(identifier)
        if not session:
            return None
        # Expiration 1h
        if time.time() - session["auth_time"] > 3600:
            del self._sessions[identifier]
            return None
        return session

    def verify_session_for_command(self, identifier: str,
                                    command: str) -> tuple[bool, str]:
        """
        Verifie si la session permet d'executer la commande.
        Retourne (autorise, message_erreur).
        """
        session = self.get_session(identifier)
        if not session:
            return False, "Session expiree. Renvoyez LUNA AUTH."

        level = COMMAND_LEVELS.get(command, LEVEL_READ)

        # READ → session suffit
        if level == LEVEL_READ:
            return True, ""

        # WRITE → TOTP requis (valide 10 min)
        if level == LEVEL_WRITE:
            if session.get("totp_verified"):
                if time.time() - session.get("totp_time", 0) < 600:
                    return True, ""
            return False, (
                "Commande WRITE: code TOTP requis.\n"
                "Envoyez: LUNA TOTP <code_6_chiffres>\n"
                "puis retentez votre commande."
            )

        # CRITICAL → TOTP requis + recent (< 2 min)
        if level == LEVEL_CRITICAL:
            if session.get("totp_verified"):
                if time.time() - session.get("totp_time", 0) < 120:
                    return True, ""
            return False, (
                "Commande CRITIQUE: code TOTP requis (valide 2 min).\n"
                "Envoyez: LUNA TOTP <code_6_chiffres>\n"
                "puis retentez votre commande IMMEDIATEMENT."
            )

        return False, "Niveau d'acces inconnu."

    def session_verify_totp(self, identifier: str, code: str) -> bool:
        """Verifie un TOTP et marque la session."""
        session = self.get_session(identifier)
        if not session:
            return False
        if self.verify_totp(code):
            session["totp_verified"] = True
            session["totp_time"] = time.time()
            return True
        return False

    # ──────────────────────────────────────────
    # SETUP DISPLAY
    # ──────────────────────────────────────────

    def get_setup_info(self) -> str:
        """Affiche les infos de setup (premier lancement)."""
        lines = [
            "",
            "=" * 50,
            "  LUNA CORTEX — CONFIGURATION SECURITE",
            "=" * 50,
            "",
            "1. GOOGLE AUTHENTICATOR (TOTP)",
            "   Scannez ce QR code avec Google Authenticator",
            "   ou Authy sur votre telephone:",
            "",
        ]
        lines.append(self.get_totp_qr_text())
        lines.append("")
        lines.append(f"   Secret (saisie manuelle): {self._totp_secret}")
        lines.append(f"   Code actuel (test): {self.get_current_totp()}")
        lines.append("")
        lines.append("2. CLE API (pour luna-ctl depuis votre VM)")
        new_key = self.get_new_api_key()
        if new_key:
            lines.append(f"   NOUVELLE CLE: {new_key}")
            lines.append("   ⚠ NOTEZ-LA, elle ne sera plus affichee!")
        else:
            lines.append("   (deja configuree)")
        lines.append("")
        lines.append("3. TELEGRAM")
        if self._telegram_users:
            for uid, role in self._telegram_users.items():
                lines.append(f"   User ID {uid}: {role}")
        else:
            lines.append("   Pas encore configure.")
            lines.append("   Envoyez /start au bot puis LUNA PAIR <totp>")
        lines.append("")
        lines.append("=" * 50)
        return "\n".join(lines)
