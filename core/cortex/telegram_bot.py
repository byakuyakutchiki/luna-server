"""
TELEGRAM BOT — Poste de commandement securise.

POURQUOI TELEGRAM EST PLUS SUR QUE SMS:
- Ton user_id Telegram est cryptographiquement lie a ton compte
- Pas de SIM swap possible (contrairement au SMS)
- Chiffrement TLS bout en bout avec les serveurs Telegram
- L'attaquant devrait voler ton telephone ET ton mot de passe Telegram
- Le bot ne repond qu'aux user_id enregistres

COMMENT CA MARCHE:
1. Tu crees un bot Telegram via @BotFather
2. Tu mets le token dans .env (ALERT_TELEGRAM_BOT_TOKEN)
3. Tu envoies /start au bot
4. Le bot te demande ton code TOTP (Google Authenticator)
5. Si le TOTP est bon → ton user_id est enregistre = tu es verifie
6. Ensuite tu peux envoyer des commandes: /status, /lock, /ban, etc.

COMMANDES:
  /start            → Premier contact + enregistrement
  /pair <totp>      → Associer ton compte (TOTP requis)
  /status           → Etat du serveur
  /health           → Sante systeme detaillee
  /threats          → Rapport securite
  /clients          → Liste clients
  /quota <id>       → Quota d'un client
  /ban <ip>         → Bannir une IP (TOTP requis)
  /unban <ip>       → Debannir
  /banned           → Liste IPs bannies
  /lock <raison>    → Lockdown (TOTP requis)
  /unlock           → Deverrouiller (TOTP requis)
  /shield <on/off>  → Mode bouclier (TOTP requis)
  /kill <id>        → Suspendre client (TOTP requis)
  /revive <id>      → Reactiver client (TOTP requis)
  /backup           → Backup Redis
  /logs             → 10 derniers evenements
  /errors           → 10 dernieres erreurs
  /digest           → Rapport maintenant
  /cortex           → Status du cerveau IA
  /totp <code>      → Valider TOTP (ouvre acces WRITE/CRITICAL 10 min)
  /help             → Liste des commandes
"""

import asyncio
import logging
import time
from typing import Optional

import httpx

from .auth import COMMAND_LEVELS, LEVEL_CRITICAL, LEVEL_READ, LEVEL_WRITE, CortexAuth

logger = logging.getLogger("cortex.telegram_bot")


class CortexTelegramBot:
    """
    Bot Telegram qui recoit des commandes et les route
    vers le systeme d'urgence du Cortex.
    Utilise l'API Telegram HTTP (pas de lib externe lourde).
    """

    def __init__(self, bot_token: str, auth: CortexAuth,
                 cortex_brain=None):
        self.bot_token = bot_token
        self.auth = auth
        self.brain = cortex_brain
        self._base_url = f"https://api.telegram.org/bot{bot_token}"
        self._last_update_id = 0
        self._running = False
        self._http: Optional[httpx.AsyncClient] = None
        # TOTP validations temporaires par user_id
        self._totp_sessions: dict[int, float] = {}

    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(timeout=35.0)
        return self._http

    async def close(self):
        if self._http and not self._http.is_closed:
            await self._http.aclose()

    # ──────────────────────────────────────────
    # POLLING LOOP
    # ──────────────────────────────────────────

    async def start_polling(self):
        """Demarre le polling des updates Telegram."""
        if not self.bot_token:
            logger.info("Telegram bot: pas de token, desactive")
            return
        # Supprimer tout webhook existant avant de lancer le polling
        try:
            http = await self._get_http()
            await http.post(f"{self._base_url}/deleteWebhook")
        except Exception:
            pass
        self._running = True
        logger.info("Telegram bot: polling demarre")
        while self._running:
            try:
                await self._poll_updates()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Telegram polling erreur: {e}")
                await asyncio.sleep(5)

    async def stop_polling(self):
        self._running = False
        await self.close()

    # ──────────────────────────────────────────
    # WEBHOOK MODE (Cloud Run)
    # ──────────────────────────────────────────

    async def setup_webhook(self, webhook_url: str):
        """Configure le webhook Telegram pour recevoir les updates via HTTP POST."""
        if not self.bot_token:
            logger.info("Telegram bot: pas de token, webhook non configure")
            return False
        try:
            http = await self._get_http()
            resp = await http.post(
                f"{self._base_url}/setWebhook",
                json={
                    "url": webhook_url,
                    "allowed_updates": ["message"],
                    "drop_pending_updates": False,
                },
            )
            data = resp.json()
            if data.get("ok"):
                logger.info(f"Telegram webhook configure: {webhook_url}")
                return True
            else:
                logger.error(f"Telegram webhook erreur: {data}")
                return False
        except Exception as e:
            logger.error(f"Telegram webhook setup erreur: {e}")
            return False

    async def handle_webhook_update(self, update: dict):
        """Traite un update recu via webhook (POST du serveur Telegram)."""
        message = update.get("message")
        if message and message.get("text"):
            await self._handle_message(message)

    async def _poll_updates(self):
        """Recupere les nouveaux messages."""
        http = await self._get_http()
        try:
            resp = await http.get(
                f"{self._base_url}/getUpdates",
                params={
                    "offset": self._last_update_id + 1,
                    "timeout": 30,
                    "allowed_updates": '["message"]',
                },
            )
            if resp.status_code != 200:
                await asyncio.sleep(2)
                return
            data = resp.json()
            if not data.get("ok"):
                await asyncio.sleep(2)
                return
            for update in data.get("result", []):
                self._last_update_id = update["update_id"]
                message = update.get("message")
                if message and message.get("text"):
                    await self._handle_message(message)
        except httpx.ReadTimeout:
            pass  # Normal pour long polling
        except Exception as e:
            logger.debug(f"Telegram poll: {e}")
            await asyncio.sleep(2)

    # ──────────────────────────────────────────
    # MESSAGE HANDLER
    # ──────────────────────────────────────────

    async def _handle_message(self, message: dict):
        """Traite un message entrant."""
        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        username = message["from"].get("username", "")
        text = message.get("text", "").strip()

        # /start et /pair sont toujours accessibles
        if text.startswith("/"):
            parts = text.split(maxsplit=1)
            cmd = parts[0].lower().split("@")[0]
            args = parts[1] if len(parts) > 1 else ""

            if cmd == "/start":
                await self._cmd_start(chat_id, user_id, username)
                return
            if cmd == "/pair":
                await self._cmd_pair(chat_id, user_id, username, args)
                return

        # Verifier que l'utilisateur est enregistre
        role = self.auth.verify_telegram_user(user_id)
        if not role:
            await self._send(chat_id,
                             "Vous n'etes pas enregistre.\n"
                             "Envoyez /pair <code_totp> pour vous associer.")
            return

        # /totp pour valider l'acces WRITE/CRITICAL
        if text.startswith("/totp"):
            args = text.split(maxsplit=1)[1] if " " in text else ""
            await self._cmd_totp(chat_id, user_id, args)
            return

        # ── PARSER: slash commands OU francais libre ──
        luna_cmd = None
        args = ""

        if text.startswith("/"):
            # Commande slash classique
            parts = text.split(maxsplit=1)
            cmd = parts[0].lower().split("@")[0]
            args = parts[1] if len(parts) > 1 else ""
            command_map = {
                # LECTURE
                "/status": "STATUS", "/health": "HEALTH", "/etat": "STATUS",
                "/sante": "HEALTH", "/threats": "THREATS", "/menaces": "THREATS",
                "/securite": "THREATS", "/clients": "CLIENTS",
                "/quota": "QUOTA", "/conso": "QUOTA",
                "/banned": "BANNED", "/bannis": "BANNED",
                "/logs": "LOGS", "/journal": "LOGS",
                "/errors": "ERRORS", "/erreurs": "ERRORS",
                "/digest": "DIGEST", "/rapport": "DIGEST", "/bilan": "DIGEST",
                "/cortex": "CORTEX", "/cerveau": "CORTEX",
                "/help": "HELP", "/aide": "HELP",
                "/ping": "PING", "/allo": "PING",
                "/uptime": "UPTIME", "/duree": "UPTIME",
                "/redis": "REDIS", "/bdd": "REDIS",
                "/config": "CONFIG", "/configuration": "CONFIG",
                "/whitelist": "WHITELIST", "/listeblanche": "WHITELIST",
                "/sessions": "SESSIONS", "/connectes": "SESSIONS",
                "/processes": "PROCESSES", "/processus": "PROCESSES", "/top": "PROCESSES",
                "/network": "NETWORK", "/reseau": "NETWORK",
                "/disk": "DISK", "/disque": "DISK", "/stockage": "DISK",
                "/version": "VERSION",
                # ECRITURE
                "/ban": "BAN", "/bannir": "BAN", "/bloquer": "BAN",
                "/unban": "UNBAN", "/debannir": "UNBAN",
                "/kill": "KILL", "/couper": "KILL", "/suspendre": "KILL",
                "/revive": "REVIVE", "/reactiver": "REVIVE",
                "/backup": "BACKUP", "/sauvegarde": "BACKUP",
                "/maintenance": "MAINTENANCE",
                "/announce": "ANNOUNCE", "/annonce": "ANNOUNCE", "/diffuser": "ANNOUNCE",
                "/msg": "MSG", "/message": "MSG",
                "/whitelist_add": "WHITELIST_ADD", "/wladd": "WHITELIST_ADD",
                "/whitelist_del": "WHITELIST_DEL", "/wldel": "WHITELIST_DEL",
                "/quota_set": "QUOTA_SET",
                "/quota_reset": "QUOTA_RESET", "/raz_quota": "QUOTA_RESET",
                "/purge": "PURGE", "/nettoyer": "PURGE",
                "/ratelimit": "RATELIMIT", "/limite": "RATELIMIT",
                # AUDIT + PDF
                "/audit": "AUDIT", "/historique": "AUDIT", "/piste": "AUDIT",
                "/couts": "COUTS", "/costs": "COUTS", "/depenses": "COUTS",
                "/export": "EXPORT", "/pdf": "EXPORT",
                # CRITIQUE
                "/lock": "LOCK", "/verrouiller": "LOCK", "/fermer": "LOCK",
                "/unlock": "UNLOCK", "/ouvrir": "UNLOCK",
                "/shield": "SHIELD", "/bouclier": "SHIELD",
                "/restart": "RESTART", "/redemarrer": "RESTART",
                "/stop": "STOP", "/eteindre": "STOP",
                "/rekey": "REKEY",
                "/wipe": "WIPE", "/effacer": "WIPE",
            }
            luna_cmd = command_map.get(cmd)
        else:
            # Francais libre: "comment va le serveur", "bloque 1.2.3.4"
            try:
                from .fr_parser import understand_french
                luna_cmd, args = await understand_french(text)
            except ImportError:
                pass

        if not luna_cmd:
            await self._send(chat_id,
                             "Je n'ai pas compris.\n"
                             "Ecris en francais:\n"
                             "  comment va le serveur\n"
                             "  ya des attaques\n"
                             "  bloque l'ip 1.2.3.4\n"
                             "Ou tape /aide")
            return

        # Verifier le niveau d'acces
        level = COMMAND_LEVELS.get(luna_cmd, LEVEL_READ)
        if level in (LEVEL_WRITE, LEVEL_CRITICAL):
            totp_time = await self._get_totp_time(user_id)
            max_age = 600 if level == LEVEL_WRITE else 120
            if time.time() - totp_time > max_age:
                msg = (
                    f"Commande {level.upper()}: TOTP requis.\n"
                    f"Envoyez /totp <code_6_chiffres>\n"
                    f"puis retentez la commande."
                )
                if level == LEVEL_CRITICAL:
                    msg += "\n(Valide 2 minutes seulement)"
                await self._send(chat_id, msg)
                return

        # Executer via le systeme d'urgence du Cortex
        if self.brain and self.brain.emergency:
            # Restaurer la session depuis Redis si multi-instance
            await self._restore_emergency_session(user_id)
            # Simuler un SMS "LUNA COMMANDE args"
            fake_sms = f"LUNA {luna_cmd} {args}".strip()
            # S'assurer que l'emergency mode reconnait ce user
            phone_key = f"telegram:{user_id}"
            if not self.brain.emergency._is_authenticated(phone_key):
                self.brain.emergency._sessions[phone_key] = {
                    "auth": True,
                    "time": time.time(),
                    "role": role,
                }
            response = await self.brain.emergency.handle_incoming_sms(
                phone_key, fake_sms)
            if response:
                await self._send(chat_id, response)
            else:
                await self._send(chat_id, "Commande executee (pas de reponse).")
        else:
            await self._send(chat_id, "Cortex non disponible.")

    # ──────────────────────────────────────────
    # COMMANDES SPECIALES
    # ──────────────────────────────────────────

    async def _cmd_start(self, chat_id: int, user_id: int,
                          username: str):
        """Premier contact avec le bot."""
        role = self.auth.verify_telegram_user(user_id)
        if role:
            await self._send(
                chat_id,
                f"Luna Cortex\n"
                f"Bienvenue {username or 'utilisateur'}.\n"
                f"Role: {role}\n"
                f"Tapez /help pour les commandes.\n"
                f"Tapez /totp <code> pour debloquer les commandes sensibles."
            )
        else:
            await self._send(
                chat_id,
                f"Luna Cortex — Enregistrement\n\n"
                f"Votre User ID: {user_id}\n\n"
                f"Pour vous associer, envoyez:\n"
                f"/pair <code_totp_6_chiffres>\n\n"
                f"Le code TOTP vient de Google Authenticator.\n"
                f"Si vous n'avez pas encore scanne le QR code,\n"
                f"connectez-vous au serveur Luna et lancez:\n"
                f"  python3 -m core.cortex.setup"
            )

    async def _cmd_pair(self, chat_id: int, user_id: int,
                         username: str, args: str):
        """Associer un compte Telegram (necessite TOTP)."""
        code = args.strip()
        if not code:
            await self._send(chat_id,
                             "Usage: /pair <code_totp_6_chiffres>")
            return

        if self.auth.verify_totp(code):
            # Determiner le role
            # Premier utilisateur = founder, suivants = exploitant
            role = "founder" if not self.auth.get_telegram_users() else "exploitant"
            self.auth.register_telegram_user(user_id, role, username)
            self._totp_sessions[user_id] = time.time()
            await self._send(
                chat_id,
                f"ASSOCIATION REUSSIE\n"
                f"User ID: {user_id}\n"
                f"Username: @{username}\n"
                f"Role: {role}\n\n"
                f"Vous pouvez maintenant controler Luna.\n"
                f"Tapez /help pour les commandes."
            )
            logger.info(
                f"Telegram user enregistre: {user_id} (@{username}) = {role}")
        else:
            await self._send(chat_id,
                             "Code TOTP incorrect. Verifiez Google Authenticator.")

    async def _cmd_totp(self, chat_id: int, user_id: int, args: str):
        """Valider un code TOTP pour debloquer les commandes."""
        code = args.strip()
        if not code:
            await self._send(chat_id,
                             "Usage: /totp <code_6_chiffres>")
            return

        if self.auth.verify_totp(code):
            now = time.time()
            self._totp_sessions[user_id] = now
            # Persister dans Redis (survit aux redemarrages Cloud Run)
            await self._set_totp_time(user_id, now)
            # Synchroniser avec EmergencyMode (local + Redis)
            role = self.auth.verify_telegram_user(user_id) or "founder"
            if self.brain and self.brain.emergency:
                phone_key = f"telegram:{user_id}"
                self.brain.emergency._sessions[phone_key] = {
                    "auth": True,
                    "time": now,
                    "role": role,
                    "totp_verified": True,
                    "totp_time": now,
                }
            await self._sync_emergency_session_redis(user_id, role, now)
            await self._send(
                chat_id,
                "TOTP verifie.\n"
                "Commandes WRITE debloquees (10 min).\n"
                "Commandes CRITIQUES debloquees (2 min)."
            )
        else:
            await self._send(chat_id,
                             "Code TOTP incorrect.")

    async def _cmd_help(self, chat_id: int, role: str):
        """Liste des commandes."""
        text = (
            "LUNA CORTEX — Commandes\n"
            "─────────────────────────\n"
            "LECTURE (pas de TOTP):\n"
            "  /status — Etat serveur\n"
            "  /health — Sante systeme\n"
            "  /threats — Securite\n"
            "  /clients — Liste clients\n"
            "  /quota <id> — Quota client\n"
            "  /banned — IPs bannies\n"
            "  /logs — Evenements\n"
            "  /errors — Erreurs\n"
            "  /cortex — Status IA\n"
            "  /digest — Rapport\n"
            "  /ping — Test serveur\n"
            "  /uptime — Duree fonctionnement\n"
            "  /redis — Infos base\n"
            "  /config — Configuration\n"
            "  /version — Versions\n"
            "  /sessions — Qui est connecte\n"
            "  /processes — Top CPU\n"
            "  /network — Reseau\n"
            "  /disk — Espace disque\n"
            "  /whitelist — IPs autorisees\n"
            "\n"
            "AUDIT:\n"
            "  /audit [jours] — Journal actions\n"
            "  /couts — Couts du mois\n"
            "\n"
            "ECRITURE (TOTP 10 min):\n"
            "  /export audit|couts|complet — PDF\n"
            "  /ban <ip> — Bannir IP\n"
            "  /unban <ip> — Debannir\n"
            "  /kill <id> — Suspendre client\n"
            "  /revive <id> — Reactiver\n"
            "  /backup — Backup Redis\n"
            "  /maintenance <msg> — Maintenance\n"
            "  /announce <msg> — Annonce\n"
            "  /msg <id> <msg> — Message client\n"
            "  /wladd <ip> — Whitelist +\n"
            "  /wldel <ip> — Whitelist -\n"
            "  /quota_set <id> <r> <v> — Modif quota\n"
            "  /quota_reset <id> — RAZ quota\n"
            "  /purge <cible> — Nettoyer\n"
            "  /ratelimit <n> — Limite req/min\n"
            "\n"
        )
        if role == "founder":
            text += (
                "CRITIQUE (TOTP 2 min):\n"
                "  /lock <raison> — Lockdown\n"
                "  /unlock — Deverrouiller\n"
                "  /shield on|off — Bouclier\n"
                "  /restart — Redemarrer\n"
                "  /stop — Arret complet\n"
                "  /rekey — Nouvelle cle API\n"
                "  /wipe <id> — Supprimer client\n"
                "\n"
            )
        text += (
            "SECURITE:\n"
            "  /totp <code> — Valider TOTP\n"
            "  /pair <totp> — Associer compte\n"
            "\n"
            "Tu peux aussi ecrire en francais libre!"
        )
        await self._send(chat_id, text)

    # ──────────────────────────────────────────
    # TOTP REDIS PERSISTENCE (multi-instance Cloud Run)
    # ──────────────────────────────────────────

    async def _get_totp_time(self, user_id: int) -> float:
        """Recupere le timestamp de validation TOTP depuis Redis."""
        # D'abord le cache local (meme instance)
        local = self._totp_sessions.get(user_id, 0)
        if local and time.time() - local < 600:
            return local
        # Sinon Redis (autre instance peut avoir valide)
        if self.brain and self.brain.redis:
            try:
                val = await self.brain.redis.get(f"cortex:totp:{user_id}")
                if val:
                    ts = float(val)
                    self._totp_sessions[user_id] = ts  # mettre en cache
                    return ts
            except Exception as e:
                logger.debug(f"Redis get totp: {e}")
        return local

    async def _set_totp_time(self, user_id: int, timestamp: float):
        """Persiste le timestamp TOTP dans Redis (TTL 10 min)."""
        if self.brain and self.brain.redis:
            try:
                key = f"cortex:totp:{user_id}"
                await self.brain.redis.set(key, str(timestamp), ex=620)
            except Exception as e:
                logger.debug(f"Redis set totp: {e}")

    async def _sync_emergency_session_redis(self, user_id: int,
                                              role: str, now: float):
        """Persiste la session emergency dans Redis pour multi-instance."""
        if self.brain and self.brain.redis:
            try:
                import json
                key = f"cortex:session:telegram:{user_id}"
                data = json.dumps({
                    "auth": True, "time": now, "role": role,
                    "totp_verified": True, "totp_time": now,
                })
                await self.brain.redis.set(key, data, ex=620)
            except Exception as e:
                logger.debug(f"Redis set session: {e}")

    async def _restore_emergency_session(self, user_id: int) -> bool:
        """Restaure la session emergency depuis Redis si manquante localement."""
        if not self.brain or not self.brain.redis or not self.brain.emergency:
            return False
        phone_key = f"telegram:{user_id}"
        # Deja en memoire locale ?
        session = self.brain.emergency._sessions.get(phone_key, {})
        if session.get("totp_verified") and time.time() - session.get("totp_time", 0) < 600:
            return True
        # Chercher dans Redis
        try:
            import json
            data = await self.brain.redis.get(f"cortex:session:{phone_key}")
            if data:
                session_data = json.loads(data)
                if session_data.get("totp_verified") and time.time() - session_data.get("totp_time", 0) < 600:
                    self.brain.emergency._sessions[phone_key] = session_data
                    self._totp_sessions[user_id] = session_data["totp_time"]
                    return True
        except Exception as e:
            logger.debug(f"Redis restore session: {e}")
        return False

    # ──────────────────────────────────────────
    # ENVOI
    # ──────────────────────────────────────────

    async def _send(self, chat_id: int, text: str):
        """Envoie un message Telegram."""
        try:
            http = await self._get_http()
            await http.post(
                f"{self._base_url}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text[:4000],
                },
            )
        except Exception as e:
            logger.error(f"Telegram send erreur: {e}")

    async def send_document(self, chat_id: int, file_bytes,
                             filename: str,
                             caption: str = "") -> bool:
        """Envoie un document (PDF) via Telegram."""
        try:
            http = await self._get_http()
            resp = await http.post(
                f"{self._base_url}/sendDocument",
                data={
                    "chat_id": str(chat_id),
                    "caption": caption[:1024] if caption else "",
                },
                files={
                    "document": (filename, file_bytes,
                                 "application/pdf"),
                },
            )
            if resp.status_code == 200:
                logger.info(f"Document envoye a {chat_id}: {filename}")
                return True
            logger.error(f"sendDocument echec: {resp.status_code}")
            return False
        except Exception as e:
            logger.error(f"Telegram sendDocument erreur: {e}")
            return False
