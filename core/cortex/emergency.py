"""
EMERGENCY FALLBACK MODE — Pilotage SMS d'urgence.

Scenario: il est 3h du mat, t'as plus Claude, plus d'ordi,
juste ton telephone portable. Un exploitant a un probleme.
Tu envoies un SMS au serveur Luna et il t'obeit.

COMME AU SIAAP QUAND LE BATIMENT PASSE EN MODE SECURITE.

═══════════════════════════════════════════════════════════
   COMMANDES SMS FONDATEUR (acces total)
═══════════════════════════════════════════════════════════

LUNA AUTH <totp>        → Authentification par TOTP Google Authenticator
LUNA STATUS             → Etat complet du serveur
LUNA HEALTH             → Sante systeme (RAM, CPU, disk, APIs)
LUNA THREATS            → Rapport securite
LUNA CLIENTS            → Liste clients + status
LUNA QUOTA <id>         → Quota d'un client
LUNA BAN <ip>           → Bannir une IP
LUNA UNBAN <ip>         → Debannir une IP
LUNA BANNED             → Liste IPs bannies
LUNA LOCK <raison>      → Lockdown serveur (plus aucun acces client)
LUNA UNLOCK             → Deverrouiller le serveur
LUNA SHIELD ON          → Mode bouclier (whitelist only)
LUNA SHIELD OFF         → Desactiver le bouclier
LUNA KILL <tenant_id>   → Suspendre un client
LUNA REVIVE <tenant_id> → Reactiver un client
LUNA BACKUP             → Lancer un backup Redis
LUNA LOGS               → 10 derniers evenements
LUNA ERRORS             → 10 dernieres erreurs
LUNA RESTART            → Restart graceful du serveur
LUNA DIGEST             → Forcer un digest maintenant
LUNA CORTEX             → Status du Cortex
LUNA HELP               → Liste des commandes

═══════════════════════════════════════════════════════════
   COMMANDES SMS EXPLOITANT (acces limite)
═══════════════════════════════════════════════════════════

LUNA AUTH <code>         → Authentification
LUNA STATUS              → Etat du serveur
LUNA CLIENTS             → Liste clients
LUNA QUOTA <id>          → Quota client
LUNA HELP                → Liste des commandes

═══════════════════════════════════════════════════════════
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from typing import Optional

from .config import CortexConfig
from .signals import (
    ActionType, CortexAction, Severity, Signal, SignalSource,
)

logger = logging.getLogger("cortex.emergency")


# Commandes disponibles par role
FOUNDER_COMMANDS = {
    "AUTH", "TOTP", "STATUS", "HEALTH", "THREATS", "CLIENTS", "QUOTA",
    "BAN", "UNBAN", "BANNED", "LOCK", "UNLOCK", "SHIELD",
    "KILL", "REVIVE", "BACKUP", "LOGS", "ERRORS", "RESTART",
    "DIGEST", "CORTEX", "HELP",
    # Commandes READ
    "ANNOUNCE", "UPTIME", "REDIS", "CONFIG", "WHITELIST",
    "SESSIONS", "PROCESSES", "NETWORK", "DISK", "VERSION", "PING",
    "CLIENT",
    # Audit + couts
    "AUDIT", "COUTS", "EXPORT",
    # Commandes WRITE
    "MAINTENANCE", "WHITELIST_ADD", "WHITELIST_DEL",
    "QUOTA_SET", "QUOTA_RESET", "MSG", "PURGE", "RATELIMIT",
    "REGISTER", "PLAN_SET", "BROADCAST",
    # Commandes CRITICAL
    "STOP", "REKEY", "WIPE",
}

EXPLOITANT_COMMANDS = {
    "AUTH", "TOTP", "STATUS", "CLIENTS", "QUOTA", "HELP",
    "UPTIME", "VERSION", "PING", "LOGS",
    "AUDIT", "COUTS",
}

# Niveaux de commande pour TOTP
WRITE_COMMANDS = {
    "BAN", "UNBAN", "KILL", "REVIVE", "BACKUP",
    "MAINTENANCE", "WHITELIST_ADD", "WHITELIST_DEL",
    "QUOTA_SET", "QUOTA_RESET", "MSG", "PURGE", "RATELIMIT",
    "ANNOUNCE", "EXPORT",
    "REGISTER", "PLAN_SET", "BROADCAST",
}
CRITICAL_COMMANDS = {
    "LOCK", "UNLOCK", "SHIELD", "RESTART",
    "STOP", "REKEY", "WIPE",
}


class EmergencyMode:
    """
    Controleur d'urgence par SMS.
    Recoit les SMS entrants Twilio, parse les commandes,
    execute les actions, repond par SMS.

    Auth: TOTP (Google Authenticator) — plus de code statique.
    Les commandes WRITE/CRITICAL necessitent un TOTP recent.
    """

    def __init__(self, config: CortexConfig, cortex_brain=None):
        self.config = config
        self.brain = cortex_brain  # Reference au Brain pour acceder a tout
        self._sessions: dict[str, dict] = {}  # phone -> {auth: bool, time: float, role: str}
        self._auth = None  # CortexAuth, injecte par le Brain
        self._audit_logger = None  # CortexAuditLogger, injecte par le Brain
        self._cost_tracker = None  # CortexCostTracker, injecte par le Brain
        self._pdf_exporter = None  # CortexPDFExporter, injecte par le Brain

    # ──────────────────────────────────────────
    # RECEPTION SMS (appele par le webhook Twilio)
    # ──────────────────────────────────────────

    async def handle_incoming_sms(self, from_phone: str,
                                   body: str) -> Optional[str]:
        """
        Traite un SMS entrant. Retourne la reponse a envoyer.
        Retourne None si le SMS n'est pas une commande Luna.
        """
        body = body.strip()

        # Verifier que le numero est autorise
        normalized = self._normalize_phone(from_phone)
        if not self._is_allowed(normalized):
            logger.warning(f"SMS commande refuse de {from_phone} (non autorise)")
            return None

        # ── PARSER FRANCAIS ──
        # Accepte "LUNA STATUS" classique OU du francais libre
        # "comment va le serveur" → STATUS
        # "bloque l'ip 185.x.x.x" → BAN 185.x.x.x
        if body.upper().startswith("LUNA "):
            # Format classique: LUNA COMMANDE [args]
            parts = body.split(maxsplit=2)
            if len(parts) < 2:
                return await self._cmd_help(normalized,
                                             self._get_role(normalized), "")
            command = parts[1].upper()
            args = parts[2] if len(parts) > 2 else ""
        else:
            # Francais libre: parser avec le module FR
            try:
                from .fr_parser import understand_french
                command, args = await understand_french(body)
                if not command:
                    return (
                        "LUNA: Je n'ai pas compris.\n"
                        "Exemples:\n"
                        "  comment va le serveur\n"
                        "  ya des attaques\n"
                        "  bloque l'ip 1.2.3.4\n"
                        "  montre les clients\n"
                        "  aide"
                    )
            except ImportError:
                # Fallback si fr_parser pas dispo
                if not body.upper().startswith("LUNA"):
                    return None
                parts = body.split(maxsplit=2)
                command = parts[1].upper() if len(parts) > 1 else "HELP"
                args = parts[2] if len(parts) > 2 else ""

        # Determiner le role
        role = self._get_role(normalized)
        allowed = FOUNDER_COMMANDS if role == "founder" else EXPLOITANT_COMMANDS

        # Auth obligatoire sauf pour AUTH, TOTP et HELP
        if command not in ("AUTH", "TOTP", "HELP"):
            if not self._is_authenticated(normalized):
                return (
                    "LUNA: Authentification requise.\n"
                    "Envoyez: LUNA AUTH <code_totp>\n"
                    "puis retentez votre commande."
                )

        # Verifier que la commande est autorisee pour ce role
        if command not in allowed:
            return f"LUNA: Commande '{command}' non autorisee pour votre role ({role})."

        # Verifier le niveau TOTP pour les commandes sensibles
        if command in WRITE_COMMANDS or command in CRITICAL_COMMANDS:
            session = self._sessions.get(normalized, {})
            totp_ok = session.get("totp_verified", False)
            totp_age = time.time() - session.get("totp_time", 0)
            # Fallback Redis si session locale vide (multi-instance Cloud Run)
            if (not totp_ok or totp_age > 600) and self.brain and self.brain.redis:
                try:
                    import json as _json
                    redis_data = await self.brain.redis.get(f"cortex:session:{normalized}")
                    if redis_data:
                        session = _json.loads(redis_data)
                        self._sessions[normalized] = session
                        totp_ok = session.get("totp_verified", False)
                        totp_age = time.time() - session.get("totp_time", 0)
                except Exception:
                    pass
            max_age = 120 if command in CRITICAL_COMMANDS else 600

            if not totp_ok or totp_age > max_age:
                level = "CRITIQUE" if command in CRITICAL_COMMANDS else "WRITE"
                return (
                    f"LUNA: Commande {level} — TOTP requis.\n"
                    f"Envoyez: LUNA TOTP <code_6_chiffres>\n"
                    f"puis retentez votre commande.\n"
                    f"{'(Valide 2 min seulement)' if level == 'CRITIQUE' else '(Valide 10 min)'}"
                )

        # Router la commande
        source = "telegram" if normalized.startswith("telegram:") else "sms"
        try:
            handler = getattr(self, f"_cmd_{command.lower()}", None)
            if handler:
                result = await handler(normalized, role, args)
                # Audit trail
                if self._audit_logger:
                    await self._audit_logger.log(
                        actor_id=normalized, role=role, source=source,
                        command=command, args=args,
                        result=result or "", success=True,
                    )
                return result
            return f"LUNA: Commande '{command}' non implementee."
        except Exception as e:
            logger.error(f"Erreur commande {command}: {e}")
            if self._audit_logger:
                await self._audit_logger.log(
                    actor_id=normalized, role=role, source=source,
                    command=command, args=args,
                    result=str(e), success=False,
                )
            return f"LUNA ERREUR: {str(e)[:200]}"

    # ──────────────────────────────────────────
    # AUTHENTIFICATION
    # ──────────────────────────────────────────

    def _is_allowed(self, phone: str) -> bool:
        """Verifie si le numero est dans la liste autorisee."""
        # Les appels depuis le bot Telegram sont deja verifies
        if phone.startswith("telegram:"):
            return True
        return phone in self.config.emergency_allowed_phones

    def _get_role(self, phone: str) -> str:
        """Determine le role du numero."""
        # Telegram: role deja dans la session
        if phone.startswith("telegram:"):
            session = self._sessions.get(phone, {})
            return session.get("role", "founder")
        if phone == self._normalize_phone(self.config.founder_phone):
            return "founder"
        return "exploitant"

    def _is_authenticated(self, phone: str) -> bool:
        """Verifie si le numero est authentifie."""
        session = self._sessions.get(phone)
        if not session:
            return False
        if not session.get("auth"):
            return False
        # Expiration de session
        if time.time() - session["time"] > self.config.emergency_session_ttl:
            del self._sessions[phone]
            return False
        return True

    async def _cmd_auth(self, phone: str, role: str, args: str) -> str:
        """LUNA AUTH <totp> — Authentification par TOTP Google Authenticator."""
        code = args.strip()
        if not code:
            return (
                "LUNA: Envoyez LUNA AUTH <code_totp_6_chiffres>\n"
                "Le code vient de Google Authenticator."
            )

        # Verifier le TOTP
        if self._auth and self._auth.verify_totp(code):
            self._sessions[phone] = {
                "auth": True,
                "time": time.time(),
                "role": role,
                "totp_verified": True,
                "totp_time": time.time(),
            }
            ttl_min = self.config.emergency_session_ttl // 60
            return (
                f"LUNA: Authentification TOTP OK.\n"
                f"Role: {role.upper()}\n"
                f"Session valide {ttl_min} min.\n"
                f"Commandes READ: OK.\n"
                f"Commandes WRITE: OK (10 min).\n"
                f"Commandes CRITIQUES: OK (2 min).\n"
                f"Tapez LUNA HELP pour les commandes."
            )
        elif not self._auth:
            # Fallback sur code statique si TOTP pas dispo
            expected = self.config.emergency_auth_code
            if expected and code == expected:
                self._sessions[phone] = {
                    "auth": True,
                    "time": time.time(),
                    "role": role,
                    "totp_verified": False,
                    "totp_time": 0,
                }
                return (
                    f"LUNA: Auth code statique OK (TOTP recommande).\n"
                    f"Role: {role.upper()}\n"
                    f"Commandes READ seulement (pas de TOTP)."
                )
            return "LUNA: Code incorrect."
        else:
            logger.warning(f"Echec auth TOTP SMS depuis {phone[:8]}...")
            return "LUNA: Code TOTP incorrect. Verifiez Google Authenticator."

    async def _cmd_totp(self, phone: str, role: str, args: str) -> str:
        """LUNA TOTP <code> — Elever les droits avec un code TOTP."""
        code = args.strip()
        if not code:
            return "LUNA: Envoyez LUNA TOTP <code_totp_6_chiffres>"

        if self._auth and self._auth.verify_totp(code):
            session = self._sessions.get(phone)
            if session:
                session["totp_verified"] = True
                session["totp_time"] = time.time()
            return (
                "LUNA: TOTP verifie.\n"
                "Commandes WRITE debloquees (10 min).\n"
                "Commandes CRITIQUES debloquees (2 min)."
            )
        return "LUNA: Code TOTP incorrect."

    # ──────────────────────────────────────────
    # COMMANDES STATUS / HEALTH
    # ──────────────────────────────────────────

    async def _cmd_status(self, phone: str, role: str, args: str) -> str:
        """LUNA STATUS — Etat complet."""
        status = await self._get_system_status()
        return (
            f"LUNA STATUS\n"
            f"{'=' * 24}\n"
            f"Mode: {status['mode']}\n"
            f"Uptime: {status['uptime']}\n"
            f"Clients: {status['active_clients']}/{status['total_clients']}\n"
            f"Redis: {status['redis_status']}\n"
            f"Menaces 24h: {status['threats_24h']}\n"
            f"IPs bannies: {status['banned_ips']}\n"
            f"CPU: {status['cpu']}% | RAM: {status['ram']}%\n"
            f"Disk: {status['disk']}%\n"
            f"Dernier backup: {status['last_backup']}\n"
            f"Cortex: {status['cortex_status']}"
        )

    async def _cmd_health(self, phone: str, role: str, args: str) -> str:
        """LUNA HEALTH — Sante systeme detaillee."""
        health = await self._get_health_details()
        return (
            f"LUNA HEALTH\n"
            f"{'=' * 24}\n"
            f"Redis RAM: {health['redis_ram']}\n"
            f"Redis keys: {health['redis_keys']}\n"
            f"CPU: {health['cpu']}\n"
            f"Disk: {health['disk_used']}/{health['disk_total']}\n"
            f"SSL expire: {health['ssl_days']}j\n"
            f"OpenAI: {health['openai_status']}\n"
            f"Twilio: {health['twilio_status']}\n"
            f"Tavus: {health['tavus_status']}\n"
            f"Backup age: {health['backup_age']}"
        )

    async def _cmd_threats(self, phone: str, role: str, args: str) -> str:
        """LUNA THREATS — Rapport securite."""
        if not self.brain or not self.brain.vigil:
            return "LUNA: Vigil non disponible."
        report = self.brain.vigil.get_threat_report()
        lines = [
            "LUNA SECURITE",
            "=" * 24,
            f"Menaces 24h: {report.total_threats_24h}",
            f"IPs bannies: {report.banned_ips}",
        ]
        if report.threats_by_type:
            lines.append("Par type:")
            for ttype, count in sorted(report.threats_by_type.items(),
                                        key=lambda x: -x[1])[:5]:
                lines.append(f"  {ttype}: {count}")
        if report.top_offenders:
            lines.append("Top menaces:")
            for off in report.top_offenders[:3]:
                lines.append(
                    f"  {off['ip']} (score:{off['score']:.0f}, "
                    f"signaux:{off['signals']})")
        if report.auto_actions_taken:
            lines.append("Actions auto:")
            for a in report.auto_actions_taken[-3:]:
                lines.append(f"  {a}")
        return "\n".join(lines)

    # ──────────────────────────────────────────
    # COMMANDES CLIENTS
    # ──────────────────────────────────────────

    async def _cmd_clients(self, phone: str, role: str, args: str) -> str:
        """LUNA CLIENTS — Liste clients."""
        clients = await self._get_clients_summary()
        if not clients:
            return "LUNA: Aucun client."
        lines = ["LUNA CLIENTS", "=" * 24]
        for c in clients[:10]:  # Max 10 pour SMS
            status_icon = "OK" if c["active"] else "OFF"
            lines.append(
                f"#{c['id']} {c['name'][:15]} "
                f"[{c['plan']}] {status_icon} "
                f"Q:{c['quota_pct']}%"
            )
        if len(clients) > 10:
            lines.append(f"... +{len(clients) - 10} autres")
        return "\n".join(lines)

    async def _cmd_quota(self, phone: str, role: str, args: str) -> str:
        """LUNA QUOTA <client_id> — Quota d'un client."""
        tenant_id = args.strip()
        if not tenant_id:
            return "LUNA: Precisez l'ID client. Ex: LUNA QUOTA 3"
        quota = await self._get_client_quota(tenant_id)
        if not quota:
            return f"LUNA: Client #{tenant_id} non trouve."
        return (
            f"LUNA QUOTA #{tenant_id}\n"
            f"{'=' * 24}\n"
            f"Plan: {quota['plan']}\n"
            f"SMS: {quota['sms_used']}/{quota['sms_limit']}\n"
            f"Voix: {quota['voice_used']}/{quota['voice_limit']} min\n"
            f"Visio: {quota['visio_used']}/{quota['visio_limit']} min\n"
            f"Chat: {quota['chat_count']} msgs\n"
            f"API cost: {quota['api_cost']:.2f}EUR"
        )

    # ──────────────────────────────────────────
    # COMMANDES SECURITE (FONDATEUR ONLY)
    # ──────────────────────────────────────────

    async def _cmd_ban(self, phone: str, role: str, args: str) -> str:
        """LUNA BAN <ip> — Bannir une IP."""
        ip = args.strip().split()[0] if args.strip() else ""
        if not ip:
            return "LUNA: Precisez l'IP. Ex: LUNA BAN 185.220.101.34"
        if self.brain and self.brain.vigil:
            self.brain.vigil.manual_ban(
                ip, duration=86400,
                reason="SMS emergency", by="founder_sms")
            return f"LUNA: IP {ip} bannie 24h."
        return "LUNA: Vigil non disponible."

    async def _cmd_unban(self, phone: str, role: str, args: str) -> str:
        """LUNA UNBAN <ip> — Debannir."""
        ip = args.strip().split()[0] if args.strip() else ""
        if not ip:
            return "LUNA: Precisez l'IP. Ex: LUNA UNBAN 185.220.101.34"
        if self.brain and self.brain.vigil:
            if self.brain.vigil.manual_unban(ip, by="founder_sms"):
                return f"LUNA: IP {ip} debannie."
            return f"LUNA: IP {ip} n'etait pas bannie."
        return "LUNA: Vigil non disponible."

    async def _cmd_banned(self, phone: str, role: str, args: str) -> str:
        """LUNA BANNED — Liste IPs bannies."""
        if not self.brain or not self.brain.vigil:
            return "LUNA: Vigil non disponible."
        banned = self.brain.vigil._banned_ips
        if not banned:
            return "LUNA: Aucune IP bannie."
        lines = ["LUNA IPs BANNIES", "=" * 24]
        for ip, info in list(banned.items())[:10]:
            remaining = int(info["until"] - time.time())
            if remaining <= 0:
                continue
            rem_str = self.brain.vigil._format_duration(remaining)
            lines.append(f"{ip} [{info['level']}] {rem_str} restant")
        return "\n".join(lines)

    async def _cmd_lock(self, phone: str, role: str, args: str) -> str:
        """LUNA LOCK <raison> — Lockdown serveur."""
        reason = args.strip() or "Lockdown d'urgence via SMS"
        if self.brain:
            await self.brain.set_mode("lockdown", reason=reason,
                                       by="founder_sms")
            return (
                f"LUNA: LOCKDOWN ACTIVE\n"
                f"Raison: {reason}\n"
                f"Plus aucun client ne peut acceder.\n"
                f"Pour deverrouiller: LUNA UNLOCK"
            )
        return "LUNA: Cortex non disponible."

    async def _cmd_unlock(self, phone: str, role: str, args: str) -> str:
        """LUNA UNLOCK — Deverrouiller."""
        if self.brain:
            await self.brain.set_mode("normal", by="founder_sms")
            return "LUNA: Serveur DEVERROUILLE. Mode normal."
        return "LUNA: Cortex non disponible."

    async def _cmd_shield(self, phone: str, role: str, args: str) -> str:
        """LUNA SHIELD ON/OFF — Mode bouclier."""
        action = args.strip().upper()
        if action == "ON":
            if self.brain:
                await self.brain.set_mode("shield", by="founder_sms")
                return (
                    "LUNA: MODE BOUCLIER ACTIVE\n"
                    "Seules les IPs whitelistees passent.\n"
                    "Pour desactiver: LUNA SHIELD OFF"
                )
        elif action == "OFF":
            if self.brain:
                await self.brain.set_mode("normal", by="founder_sms")
                return "LUNA: Bouclier DESACTIVE. Mode normal."
        return "LUNA: Precisez ON ou OFF. Ex: LUNA SHIELD ON"

    async def _cmd_kill(self, phone: str, role: str, args: str) -> str:
        """LUNA KILL <tenant_id> — Suspendre un client."""
        tenant_id = args.strip()
        if not tenant_id:
            return "LUNA: Precisez l'ID. Ex: LUNA KILL 5"
        success = await self._suspend_tenant(tenant_id)
        if success:
            return f"LUNA: Client #{tenant_id} SUSPENDU."
        return f"LUNA: Client #{tenant_id} non trouve."

    async def _cmd_revive(self, phone: str, role: str, args: str) -> str:
        """LUNA REVIVE <tenant_id> — Reactiver un client."""
        tenant_id = args.strip()
        if not tenant_id:
            return "LUNA: Precisez l'ID. Ex: LUNA REVIVE 5"
        success = await self._reactivate_tenant(tenant_id)
        if success:
            return f"LUNA: Client #{tenant_id} REACTIVE."
        return f"LUNA: Client #{tenant_id} non trouve."

    # ──────────────────────────────────────────
    # COMMANDES SYSTEME (FONDATEUR ONLY)
    # ──────────────────────────────────────────

    async def _cmd_backup(self, phone: str, role: str, args: str) -> str:
        """LUNA BACKUP — Lancer backup Redis."""
        try:
            if self.brain and self.brain.redis:
                redis = self.brain.redis
                if hasattr(redis, 'bgsave'):
                    await redis.bgsave()
                    return "LUNA: Backup Redis lance (BGSAVE)."
            return "LUNA: Redis non disponible."
        except Exception as e:
            return f"LUNA: Erreur backup: {str(e)[:100]}"

    async def _cmd_logs(self, phone: str, role: str, args: str) -> str:
        """LUNA LOGS — 10 derniers evenements."""
        events = await self._get_recent_events(10)
        if not events:
            return "LUNA: Aucun evenement recent."
        lines = ["LUNA LOGS (10 derniers)", "=" * 24]
        for e in events:
            ts = datetime.fromtimestamp(
                e.get("timestamp", 0)).strftime("%H:%M")
            lines.append(f"[{ts}] {e.get('title', '?')[:50]}")
        return "\n".join(lines)

    async def _cmd_errors(self, phone: str, role: str, args: str) -> str:
        """LUNA ERRORS — 10 dernieres erreurs."""
        errors = await self._get_recent_errors(10)
        if not errors:
            return "LUNA: Aucune erreur recente."
        lines = ["LUNA ERREURS (10 dern.)", "=" * 24]
        for e in errors:
            ts = datetime.fromtimestamp(
                e.get("timestamp", 0)).strftime("%H:%M")
            lines.append(f"[{ts}] {e.get('message', '?')[:50]}")
        return "\n".join(lines)

    async def _cmd_restart(self, phone: str, role: str, args: str) -> str:
        """LUNA RESTART — Restart graceful (Cloud Run relance le container)."""
        if self.brain:
            from .signals import Signal, SignalSource, Severity
            await self.brain.briefing.dispatch(Signal(
                source=SignalSource.SYSTEM,
                severity=Severity.CRITICAL,
                category="system",
                title="RESTART DEMANDE",
                message=f"Restart par {phone[:15]}. Le serveur va redemarrer.",
            ))
        # Envoyer la reponse AVANT de tuer le process
        asyncio.get_event_loop().call_later(
            2.0, lambda: os._exit(0))
        return (
            "LUNA: RESTART EN COURS\n"
            "Le process va s'arreter dans 2s.\n"
            "Cloud Run relancera automatiquement."
        )

    async def _cmd_digest(self, phone: str, role: str, args: str) -> str:
        """LUNA DIGEST — Forcer un digest maintenant."""
        if self.brain:
            await self.brain.force_digest()
            return "LUNA: Digest envoye sur Telegram."
        return "LUNA: Cortex non disponible."

    async def _cmd_cortex(self, phone: str, role: str, args: str) -> str:
        """LUNA CORTEX — Status du Cortex."""
        if not self.brain:
            return "LUNA: Cortex non disponible."
        status = self.brain.get_cortex_status()
        return (
            f"LUNA CORTEX\n"
            f"{'=' * 24}\n"
            f"Mode: {status['mode']}\n"
            f"Uptime: {status['uptime']}\n"
            f"Boucles: {status['loop_count']}\n"
            f"Signaux traites: {status['signals_processed']}\n"
            f"Actions executees: {status['actions_executed']}\n"
            f"Vigil: {'OK' if status['vigil_active'] else 'OFF'}\n"
            f"Doctor: {'OK' if status['doctor_active'] else 'OFF'}\n"
            f"Accountant: {'OK' if status['accountant_active'] else 'OFF'}\n"
            f"Derniere analyse IA: {status['last_ai']}"
        )

    # ──────────────────────────────────────────
    # COMMANDES NOUVELLES — LECTURE
    # ──────────────────────────────────────────

    async def _cmd_ping(self, phone: str, role: str, args: str) -> str:
        """LUNA PING — Test rapide."""
        return "LUNA: PONG — Serveur en ligne."

    async def _cmd_uptime(self, phone: str, role: str, args: str) -> str:
        """LUNA UPTIME — Temps de fonctionnement."""
        try:
            import psutil
            boot = psutil.boot_time()
            uptime_sys = time.time() - boot
            days_sys = int(uptime_sys // 86400)
            hours_sys = int((uptime_sys % 86400) // 3600)
            mins_sys = int((uptime_sys % 3600) // 60)
        except ImportError:
            days_sys = hours_sys = mins_sys = 0

        cortex_uptime = "?"
        if self.brain:
            ct = time.time() - self.brain._start_time
            ch = int(ct // 3600)
            cm = int((ct % 3600) // 60)
            cortex_uptime = f"{ch}h{cm:02d}m"

        return (
            f"LUNA UPTIME\n"
            f"{'=' * 24}\n"
            f"Systeme: {days_sys}j {hours_sys}h{mins_sys:02d}m\n"
            f"Cortex: {cortex_uptime}\n"
            f"Boucles: {self.brain._loop_count if self.brain else '?'}\n"
            f"Signaux: {self.brain._signals_processed if self.brain else '?'}\n"
            f"Actions: {self.brain._actions_executed if self.brain else '?'}"
        )

    async def _cmd_redis(self, phone: str, role: str, args: str) -> str:
        """LUNA REDIS — Infos Redis detaillees."""
        if not self.brain or not self.brain.redis:
            return "LUNA: Redis non disponible."
        try:
            redis = self.brain.redis
            info = {}
            if hasattr(redis, 'info'):
                info = await redis.info()
            keys = 0
            if hasattr(redis, 'dbsize'):
                keys = await redis.dbsize()

            # Latence ping
            t0 = time.time()
            if hasattr(redis, 'ping'):
                await redis.ping()
            latency = int((time.time() - t0) * 1000)

            return (
                f"LUNA REDIS\n"
                f"{'=' * 24}\n"
                f"Version: {info.get('redis_version', '?')}\n"
                f"RAM: {info.get('used_memory_human', '?')}\n"
                f"RAM pic: {info.get('used_memory_peak_human', '?')}\n"
                f"Keys: {keys}\n"
                f"Clients connectes: {info.get('connected_clients', '?')}\n"
                f"Ops/sec: {info.get('instantaneous_ops_per_sec', '?')}\n"
                f"Latence: {latency}ms\n"
                f"Dernier save: {info.get('rdb_last_save_time', '?')}\n"
                f"Uptime: {info.get('uptime_in_days', '?')}j"
            )
        except Exception as e:
            return f"LUNA REDIS ERREUR: {str(e)[:150]}"

    async def _cmd_config(self, phone: str, role: str, args: str) -> str:
        """LUNA CONFIG — Configuration active."""
        if not self.brain:
            return "LUNA: Cortex non disponible."
        cfg = self.brain.config
        return (
            f"LUNA CONFIG\n"
            f"{'=' * 24}\n"
            f"Mode: {self.brain.state.mode}\n"
            f"Cortex: {'ON' if cfg.enabled else 'OFF'}\n"
            f"Urgence SMS: {'ON' if cfg.emergency_enabled else 'OFF'}\n"
            f"Telegram bot: {'ON' if cfg.telegram_bot_token else 'OFF'}\n"
            f"Boucle: {cfg.loop_interval_seconds}s\n"
            f"IA: {cfg.ai_model}\n"
            f"Analyse IA: {cfg.ai_analysis_interval}s\n"
            f"Digest: {cfg.digest_hours}h\n"
            f"Hebdo: lundi {cfg.weekly_report_hour}h\n"
            f"Ban auto score: {cfg.auto_ban_score}\n"
            f"Session TTL: {cfg.emergency_session_ttl // 60}min\n"
            f"Fondateur: {cfg.founder_phone[:8]}...\n"
            f"Phones: {len(cfg.emergency_allowed_phones)}"
        )

    async def _cmd_whitelist(self, phone: str, role: str, args: str) -> str:
        """LUNA WHITELIST — IPs en whitelist."""
        if not self.brain:
            return "LUNA: Cortex non disponible."
        wl = self.brain.state.whitelist_ips
        if not wl:
            return "LUNA: Whitelist vide (aucune IP privilegiee)."
        lines = ["LUNA WHITELIST", "=" * 24]
        for ip in sorted(wl):
            lines.append(f"  {ip}")
        lines.append(f"\nTotal: {len(wl)} IPs")
        return "\n".join(lines)

    async def _cmd_sessions(self, phone: str, role: str, args: str) -> str:
        """LUNA SESSIONS — Sessions actives."""
        lines = ["LUNA SESSIONS ACTIVES", "=" * 24]
        # Sessions SMS/emergency
        now = time.time()
        for ident, sess in self._sessions.items():
            age = int(now - sess.get("time", 0))
            age_str = f"{age // 60}min" if age < 3600 else f"{age // 3600}h"
            role_s = sess.get("role", "?")
            totp = "TOTP" if sess.get("totp_verified") else "base"
            lines.append(f"  {ident[:20]}: {role_s} [{totp}] {age_str}")
        if len(self._sessions) == 0:
            lines.append("  Aucune session SMS/emergency")
        # Telegram users
        if self.brain and self.brain.auth:
            tg = self.brain.auth.get_telegram_users()
            if tg:
                lines.append(f"\nTelegram ({len(tg)} users):")
                for uid, r in tg.items():
                    lines.append(f"  ID:{uid} = {r}")
        return "\n".join(lines)

    async def _cmd_processes(self, phone: str, role: str, args: str) -> str:
        """LUNA PROCESSES — Top processus."""
        try:
            import psutil
            procs = []
            for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    info = p.info
                    if info['cpu_percent'] is not None and info['cpu_percent'] > 0.1:
                        procs.append(info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            procs.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            lines = ["LUNA PROCESSUS (top CPU)", "=" * 24]
            for p in procs[:8]:
                lines.append(
                    f"  {p['name'][:15]:15s} "
                    f"CPU:{p['cpu_percent']:5.1f}% "
                    f"RAM:{p.get('memory_percent', 0):4.1f}%"
                )
            total_cpu = psutil.cpu_percent(interval=0.1)
            total_ram = psutil.virtual_memory().percent
            lines.append(f"\nGlobal: CPU {total_cpu}% | RAM {total_ram}%")
            return "\n".join(lines)
        except ImportError:
            return "LUNA: psutil non disponible."

    async def _cmd_network(self, phone: str, role: str, args: str) -> str:
        """LUNA NETWORK — Connexions reseau."""
        try:
            import psutil
            conns = psutil.net_connections(kind='inet')
            listen = [c for c in conns if c.status == 'LISTEN']
            established = [c for c in conns if c.status == 'ESTABLISHED']
            lines = [
                "LUNA RESEAU",
                "=" * 24,
                f"Ports ecoute: {len(listen)}",
            ]
            for c in listen[:8]:
                lines.append(f"  :{c.laddr.port}")
            lines.append(f"\nConnexions actives: {len(established)}")
            # IPs uniques
            remote_ips = set()
            for c in established:
                if c.raddr:
                    remote_ips.add(c.raddr.ip)
            lines.append(f"IPs distantes: {len(remote_ips)}")
            for ip in list(remote_ips)[:5]:
                lines.append(f"  {ip}")
            if len(remote_ips) > 5:
                lines.append(f"  ... +{len(remote_ips) - 5}")
            # Bandwidth
            net_io = psutil.net_io_counters()
            sent_mb = net_io.bytes_sent / (1024 * 1024)
            recv_mb = net_io.bytes_recv / (1024 * 1024)
            lines.append(f"\nTraffic: {sent_mb:.0f}MB out / {recv_mb:.0f}MB in")
            return "\n".join(lines)
        except ImportError:
            return "LUNA: psutil non disponible."
        except Exception as e:
            return f"LUNA RESEAU: {str(e)[:150]}"

    async def _cmd_disk(self, phone: str, role: str, args: str) -> str:
        """LUNA DISK — Details disque."""
        try:
            import psutil
            lines = ["LUNA DISQUE", "=" * 24]
            for part in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    used_gb = usage.used / (1024**3)
                    total_gb = usage.total / (1024**3)
                    free_gb = usage.free / (1024**3)
                    lines.append(
                        f"{part.mountpoint}\n"
                        f"  {used_gb:.1f}G / {total_gb:.1f}G "
                        f"({usage.percent}%) "
                        f"libre: {free_gb:.1f}G"
                    )
                except PermissionError:
                    pass
            # Espace Luna specifiquement
            luna_path = os.getenv("LUNA_BASE_PATH",
                                   str(os.path.dirname(os.path.dirname(
                                       os.path.dirname(__file__)))))
            luna_usage = psutil.disk_usage(luna_path)
            lines.append(f"\nLuna ({luna_path}):")
            lines.append(f"  {luna_usage.percent}% utilise")
            return "\n".join(lines)
        except ImportError:
            return "LUNA: psutil non disponible."

    async def _cmd_version(self, phone: str, role: str, args: str) -> str:
        """LUNA VERSION — Version et dependances."""
        import sys
        lines = [
            "LUNA VERSION",
            "=" * 24,
            f"Python: {sys.version.split()[0]}",
            f"Cortex: 1.0.0",
        ]
        # Versions des deps
        for mod_name, display in [
            ("fastapi", "FastAPI"), ("uvicorn", "Uvicorn"),
            ("httpx", "HTTPX"), ("redis", "Redis-py"),
            ("pyotp", "PyOTP"), ("psutil", "psutil"),
            ("openai", "OpenAI"), ("stripe", "Stripe"),
        ]:
            try:
                mod = __import__(mod_name)
                ver = getattr(mod, "__version__", "?")
                lines.append(f"{display}: {ver}")
            except ImportError:
                lines.append(f"{display}: non installe")
        # Mode Luna
        luna_mode = os.getenv("LUNA_MODE", "full")
        lines.append(f"\nMode Luna: {luna_mode}")
        lines.append(f"Cortex: {'ON' if self.brain else 'OFF'}")
        return "\n".join(lines)

    # ──────────────────────────────────────────
    # COMMANDES NOUVELLES — ECRITURE (TOTP 10 min)
    # ──────────────────────────────────────────

    async def _cmd_maintenance(self, phone: str, role: str, args: str) -> str:
        """LUNA MAINTENANCE <message> — Mode maintenance avec annonce."""
        message = args.strip() or "Maintenance en cours"
        if self.brain:
            await self.brain.set_mode("maintenance",
                                       reason=message, by="founder_sms")
            # Stocker le message de maintenance
            if self.brain.redis and hasattr(self.brain.redis, 'set'):
                await self.brain.redis.set("luna:maintenance_message",
                                            json.dumps({
                                                "message": message,
                                                "since": time.time(),
                                                "by": phone[:10],
                                            }))
            return (
                f"LUNA: MODE MAINTENANCE ACTIF\n"
                f"Message: {message}\n"
                f"Les clients verront ce message.\n"
                f"Pour revenir: ouvre le serveur"
            )
        return "LUNA: Cortex non disponible."

    async def _cmd_announce(self, phone: str, role: str, args: str) -> str:
        """LUNA ANNOUNCE <message> — Annonce a tous."""
        message = args.strip()
        if not message:
            return "LUNA: Precisez le message. Ex: LUNA ANNOUNCE Maintenance prevue ce soir 22h"
        if not self.brain:
            return "LUNA: Cortex non disponible."

        # Stocker l'annonce dans Redis
        if self.brain.redis and hasattr(self.brain.redis, 'lpush'):
            await self.brain.redis.lpush("luna:announcements", json.dumps({
                "message": message,
                "timestamp": time.time(),
                "by": phone[:10],
            }))
            await self.brain.redis.ltrim("luna:announcements", 0, 49)

        # Envoyer sur Telegram si dispo
        if self.brain.briefing:
            from .signals import Signal, SignalSource, Severity
            await self.brain.briefing.dispatch(Signal(
                source=SignalSource.SYSTEM,
                severity=Severity.INFO,
                category="announcement",
                title="ANNONCE",
                message=message,
            ))

        return (
            f"LUNA: ANNONCE ENVOYEE\n"
            f"Message: {message}\n"
            f"Diffuse sur Telegram + Redis."
        )

    async def _cmd_whitelist_add(self, phone: str, role: str, args: str) -> str:
        """LUNA WHITELIST_ADD <ip> — Ajouter IP a la whitelist."""
        ip = args.strip().split()[0] if args.strip() else ""
        if not ip:
            return "LUNA: Precisez l'IP. Ex: LUNA WHITELIST_ADD 192.168.1.100"
        if self.brain:
            self.brain.state.whitelist_ips.add(ip)
            # Persister
            if self.brain.redis and hasattr(self.brain.redis, 'sadd'):
                await self.brain.redis.sadd("cortex:whitelist", ip)
            return f"LUNA: IP {ip} ajoutee a la whitelist."
        return "LUNA: Cortex non disponible."

    async def _cmd_whitelist_del(self, phone: str, role: str, args: str) -> str:
        """LUNA WHITELIST_DEL <ip> — Retirer IP de la whitelist."""
        ip = args.strip().split()[0] if args.strip() else ""
        if not ip:
            return "LUNA: Precisez l'IP. Ex: LUNA WHITELIST_DEL 192.168.1.100"
        if self.brain:
            self.brain.state.whitelist_ips.discard(ip)
            if self.brain.redis and hasattr(self.brain.redis, 'srem'):
                await self.brain.redis.srem("cortex:whitelist", ip)
            return f"LUNA: IP {ip} retiree de la whitelist."
        return "LUNA: Cortex non disponible."

    async def _cmd_quota_set(self, phone: str, role: str, args: str) -> str:
        """LUNA QUOTA_SET <id> <ressource> <valeur> — Modifier quota."""
        parts = args.strip().split()
        if len(parts) < 3:
            return (
                "LUNA: Usage: QUOTA_SET <id> <ressource> <valeur>\n"
                "Ressources: sms, voice, visio\n"
                "Ex: QUOTA_SET 3 sms 50"
            )
        tenant_id, resource, value = parts[0], parts[1].lower(), parts[2]
        if resource not in ("sms", "voice", "visio"):
            return "LUNA: Ressource invalide. Valides: sms, voice, visio"
        try:
            value_int = int(value)
        except ValueError:
            return "LUNA: La valeur doit etre un nombre."
        if not self.brain or not self.brain.redis:
            return "LUNA: Redis non disponible."
        try:
            redis = self.brain.redis
            quota_raw = await redis.get(f"luna:{tenant_id}:quota")
            if not quota_raw:
                return f"LUNA: Client #{tenant_id} non trouve."
            q = json.loads(quota_raw)
            q[f"{resource}_limit"] = value_int
            await redis.set(f"luna:{tenant_id}:quota", json.dumps(q))
            return f"LUNA: Client #{tenant_id} — {resource} limite = {value_int}"
        except Exception as e:
            return f"LUNA ERREUR: {str(e)[:100]}"

    async def _cmd_quota_reset(self, phone: str, role: str, args: str) -> str:
        """LUNA QUOTA_RESET <id> — RAZ des compteurs quota."""
        tenant_id = args.strip()
        if not tenant_id:
            return "LUNA: Precisez l'ID. Ex: QUOTA_RESET 3"
        if not self.brain or not self.brain.redis:
            return "LUNA: Redis non disponible."
        try:
            redis = self.brain.redis
            quota_raw = await redis.get(f"luna:{tenant_id}:quota")
            if not quota_raw:
                return f"LUNA: Client #{tenant_id} non trouve."
            q = json.loads(quota_raw)
            for k in ["sms_used", "voice_used", "visio_used", "chat_count", "api_cost"]:
                q[k] = 0
            await redis.set(f"luna:{tenant_id}:quota", json.dumps(q))
            return f"LUNA: Quotas du client #{tenant_id} remis a zero."
        except Exception as e:
            return f"LUNA ERREUR: {str(e)[:100]}"

    async def _cmd_msg(self, phone: str, role: str, args: str) -> str:
        """LUNA MSG <id> <message> — Envoyer un message a un client."""
        parts = args.strip().split(maxsplit=1)
        if len(parts) < 2:
            return "LUNA: Usage: MSG <id_client> <message>"
        tenant_id, message = parts[0], parts[1]
        if not self.brain or not self.brain.redis:
            return "LUNA: Redis non disponible."
        try:
            await self.brain.redis.lpush(
                f"luna:{tenant_id}:notifications",
                json.dumps({
                    "message": message,
                    "timestamp": time.time(),
                    "from": "fondateur",
                    "type": "admin_message",
                })
            )
            await self.brain.redis.ltrim(f"luna:{tenant_id}:notifications", 0, 49)
            return f"LUNA: Message envoye au client #{tenant_id}."
        except Exception as e:
            return f"LUNA ERREUR: {str(e)[:100]}"

    async def _cmd_purge(self, phone: str, role: str, args: str) -> str:
        """LUNA PURGE <cible> — Nettoyer logs/donnees."""
        target = args.strip().lower()
        valid_targets = {
            "logs": "cortex:signals",
            "errors": "cortex:errors",
            "bans": None,  # Special
            "announcements": "luna:announcements",
            "sessions": None,  # Special
        }
        if target not in valid_targets:
            return (
                "LUNA: Usage: PURGE <cible>\n"
                "Cibles: logs, errors, bans, announcements, sessions"
            )
        if target == "bans":
            if self.brain and self.brain.vigil:
                count = len(self.brain.vigil._banned_ips)
                self.brain.vigil._banned_ips.clear()
                return f"LUNA: {count} bans purges."
            return "LUNA: Vigil non disponible."
        if target == "sessions":
            count = len(self._sessions)
            self._sessions.clear()
            return f"LUNA: {count} sessions purgees."
        # Redis list
        key = valid_targets[target]
        if self.brain and self.brain.redis and hasattr(self.brain.redis, 'delete'):
            await self.brain.redis.delete(key)
            return f"LUNA: {target} purge."
        return "LUNA: Redis non disponible."

    async def _cmd_ratelimit(self, phone: str, role: str, args: str) -> str:
        """LUNA RATELIMIT <valeur> — Changer la limite de requetes/min."""
        parts = args.strip().split()
        if not parts or not parts[0].isdigit():
            return (
                "LUNA: Usage: RATELIMIT <max_par_minute>\n"
                "Ex: RATELIMIT 30 (30 req/min par IP)\n"
                "Actuel: info non disponible sans Redis"
            )
        limit = int(parts[0])
        if limit < 5 or limit > 1000:
            return "LUNA: Limite entre 5 et 1000 req/min."
        if self.brain and self.brain.redis and hasattr(self.brain.redis, 'set'):
            await self.brain.redis.set("cortex:ratelimit", str(limit))
            return f"LUNA: Rate limit = {limit} req/min par IP."
        return "LUNA: Redis non disponible."

    # ──────────────────────────────────────────
    # COMMANDES NOUVELLES — CRITIQUE (TOTP 2 min)
    # ──────────────────────────────────────────

    async def _cmd_stop(self, phone: str, role: str, args: str) -> str:
        """LUNA STOP — Arret complet du serveur."""
        if self.brain:
            # Log l'arret
            from .signals import Signal, SignalSource, Severity
            await self.brain.briefing.dispatch(Signal(
                source=SignalSource.SYSTEM,
                severity=Severity.EMERGENCY,
                category="system",
                title="ARRET SERVEUR",
                message=f"Arret demande par {phone[:10]}. Le serveur va s'eteindre.",
            ))
            # Stopper le Cortex proprement
            await self.brain.stop()
            # Signaler l'arret au process principal
            try:
                pid = os.getpid()
                import signal as sig_module
                os.kill(pid, sig_module.SIGTERM)
            except Exception:
                pass
            return (
                "LUNA: ARRET EN COURS\n"
                "Le serveur va s'eteindre.\n"
                "Pour redemarrer: relancez le service."
            )
        return "LUNA: Cortex non disponible."

    async def _cmd_rekey(self, phone: str, role: str, args: str) -> str:
        """LUNA REKEY — Regenerer la cle API."""
        if self.brain and self.brain.auth:
            new_key = self.brain.auth.regenerate_api_key()
            return (
                f"LUNA: CLE API REGENEREE\n"
                f"Nouvelle cle: {new_key}\n"
                f"L'ancienne cle est INVALIDEE.\n"
                f"Mettez a jour ~/.luna-ctl.key"
            )
        return "LUNA: Auth non disponible."

    async def _cmd_wipe(self, phone: str, role: str, args: str) -> str:
        """LUNA WIPE <id> — Supprimer toutes les donnees d'un client."""
        tenant_id = args.strip()
        if not tenant_id:
            return "LUNA: Precisez l'ID. Ex: WIPE 5\nATTENTION: irreversible!"
        if not self.brain or not self.brain.redis:
            return "LUNA: Redis non disponible."
        try:
            redis = self.brain.redis
            # Trouver toutes les cles du tenant
            if hasattr(redis, 'keys'):
                keys = await redis.keys(f"luna:{tenant_id}:*")
                count = len(keys)
                for key in keys:
                    await redis.delete(key)
                return (
                    f"LUNA: CLIENT #{tenant_id} EFFACE\n"
                    f"{count} cles supprimees.\n"
                    f"IRREVERSIBLE — donnees perdues."
                )
        except Exception as e:
            return f"LUNA ERREUR: {str(e)[:100]}"

    # ──────────────────────────────────────────
    # COMMANDES GESTION CLIENTS (WRITE)
    # ──────────────────────────────────────────

    async def _cmd_client(self, phone: str, role: str, args: str) -> str:
        """LUNA CLIENT <id> — Details complets d'un client."""
        tenant_id = args.strip()
        if not tenant_id:
            return "LUNA: Precisez l'ID. Ex: /client 3"
        if not self.brain or not self.brain.redis:
            return "LUNA: Redis non disponible."
        try:
            redis = self.brain.redis
            # Profil
            profile = await redis.hgetall(f"luna:{tenant_id}:profile")
            if not profile:
                return f"LUNA: Client #{tenant_id} non trouve."
            # Decode bytes si necessaire
            def _d(val):
                return val.decode() if isinstance(val, bytes) else val
            p = {_d(k): _d(v) for k, v in profile.items()}
            first = p.get("first_name", "?")
            last = p.get("last_name", "")
            email = p.get("email", "?")
            tel = p.get("phone", "non renseigne")

            # Plan depuis luna:auth:*
            plan = "?"
            auth_email = ""
            created = "?"
            auth_keys = await redis.keys("luna:auth:*")
            for ak in auth_keys:
                ak_str = _d(ak)
                if ak_str in ("luna:auth:next_tenant_id",
                               "luna:auth:tenant_index"):
                    continue
                auth_data = await redis.get(ak)
                if auth_data:
                    a = json.loads(_d(auth_data))
                    if str(a.get("tenant_id")) == str(tenant_id):
                        plan = a.get("plan", "?")
                        auth_email = a.get("email", "")
                        ts = a.get("created_at", 0)
                        if ts:
                            created = datetime.fromtimestamp(ts).strftime(
                                "%d/%m/%Y %H:%M")
                        break

            # Suspendu ?
            suspended = await redis.get(f"luna:{tenant_id}:suspended")
            status = "SUSPENDU" if suspended else "ACTIF"

            # Quota du mois
            quota = await self._get_client_quota(tenant_id)
            quota_lines = ""
            if quota:
                quota_lines = (
                    f"\nQUOTAS (mois):\n"
                    f"  SMS: {quota['sms_used']}/{quota['sms_limit']}\n"
                    f"  Voix: {quota['voice_used']}/{quota['voice_limit']} min\n"
                    f"  Visio: {quota['visio_used']}/{quota['visio_limit']} min\n"
                    f"  Chat: {quota['chat_count']} msgs"
                )

            return (
                f"LUNA CLIENT #{tenant_id}\n"
                f"{'=' * 28}\n"
                f"Nom: {first} {last}\n"
                f"Email: {auth_email or email}\n"
                f"Tel: {tel}\n"
                f"Plan: {plan}\n"
                f"Status: {status}\n"
                f"Inscrit: {created}"
                f"{quota_lines}"
            )
        except Exception as e:
            return f"LUNA ERREUR: {str(e)[:150]}"

    async def _cmd_register(self, phone: str, role: str, args: str) -> str:
        """LUNA REGISTER <email> <plan> <prenom> [nom] — Inscrire un client."""
        parts = args.strip().split()
        if len(parts) < 3:
            return (
                "LUNA: Usage: /register <email> <plan> <prenom> [nom]\n"
                "Plans: essentiel, confort, premium\n"
                "Ex: /register marie@mail.fr essentiel Marie Dupont"
            )
        email = parts[0].lower()
        plan = parts[1].lower()
        prenom = parts[2]
        nom = parts[3] if len(parts) > 3 else ""

        if "@" not in email:
            return "LUNA: Email invalide."
        if plan not in ("essentiel", "confort", "premium"):
            return "LUNA: Plan invalide. Valides: essentiel, confort, premium"

        if not self.brain or not self.brain.redis:
            return "LUNA: Redis non disponible."

        try:
            redis = self.brain.redis

            # Verifier email deja pris
            existing = await redis.get(f"luna:auth:{email}")
            if existing:
                return f"LUNA: Email {email} deja utilise."

            # Generer tenant_id
            exists = await redis.exists("luna:auth:next_tenant_id")
            if not exists:
                await redis.set("luna:auth:next_tenant_id", 1)
            tenant_id = await redis.incr("luna:auth:next_tenant_id")

            # Generer un mot de passe temporaire
            import secrets as _secrets
            temp_password = _secrets.token_urlsafe(8)  # 11 chars
            try:
                import bcrypt
                pw_hash = bcrypt.hashpw(
                    temp_password[:72].encode("utf-8"),
                    bcrypt.gensalt(rounds=12)
                ).decode("utf-8")
            except ImportError:
                import hashlib
                pw_hash = hashlib.sha256(
                    temp_password.encode()).hexdigest()

            # Creer l'enregistrement auth
            auth_record = json.dumps({
                "tenant_id": tenant_id,
                "password_hash": pw_hash,
                "plan": plan,
                "active": True,
                "created_at": time.time(),
                "email": email,
            })
            created = await redis.setnx(f"luna:auth:{email}", auth_record)
            if not created:
                return f"LUNA: Email {email} deja pris (race condition)."

            # Index tenant
            await redis.zadd("luna:auth:tenant_index",
                             {str(tenant_id): time.time()})

            # Profil
            await redis.hset(f"luna:{tenant_id}:profile", mapping={
                "tenant_id": str(tenant_id),
                "first_name": prenom,
                "last_name": nom,
                "email": email,
                "language": "fr",
                "tutoiement": "1",
            })

            return (
                f"LUNA: CLIENT CREE\n"
                f"{'=' * 28}\n"
                f"ID: #{tenant_id}\n"
                f"Nom: {prenom} {nom}\n"
                f"Email: {email}\n"
                f"Plan: {plan}\n"
                f"Mdp temporaire: {temp_password}\n"
                f"\nCommuniquez le mdp au client.\n"
                f"Il pourra se connecter a l'app Luna."
            )
        except Exception as e:
            return f"LUNA ERREUR: {str(e)[:150]}"

    async def _cmd_plan_set(self, phone: str, role: str, args: str) -> str:
        """LUNA PLAN_SET <id> <plan> — Changer le plan d'un client."""
        parts = args.strip().split()
        if len(parts) < 2:
            return (
                "LUNA: Usage: /plan_set <id> <plan>\n"
                "Plans: essentiel, confort, premium\n"
                "Ex: /plan_set 3 premium"
            )
        tenant_id = parts[0]
        new_plan = parts[1].lower()
        if new_plan not in ("essentiel", "confort", "premium"):
            return "LUNA: Plan invalide. Valides: essentiel, confort, premium"
        if not self.brain or not self.brain.redis:
            return "LUNA: Redis non disponible."
        try:
            redis = self.brain.redis
            # Verifier que le client existe
            profile = await redis.hgetall(f"luna:{tenant_id}:profile")
            if not profile:
                return f"LUNA: Client #{tenant_id} non trouve."

            # Trouver et modifier le record auth
            auth_keys = await redis.keys("luna:auth:*")
            old_plan = "?"
            for ak in auth_keys:
                ak_str = ak.decode() if isinstance(ak, bytes) else ak
                if ak_str in ("luna:auth:next_tenant_id",
                               "luna:auth:tenant_index"):
                    continue
                auth_data = await redis.get(ak)
                if auth_data:
                    auth_str = auth_data.decode() if isinstance(
                        auth_data, bytes) else auth_data
                    a = json.loads(auth_str)
                    if str(a.get("tenant_id")) == str(tenant_id):
                        old_plan = a.get("plan", "?")
                        a["plan"] = new_plan
                        await redis.set(ak_str, json.dumps(a))
                        return (
                            f"LUNA: Plan modifie\n"
                            f"Client #{tenant_id}: {old_plan} → {new_plan}\n"
                            f"Effectif immediatement."
                        )
            return f"LUNA: Record auth non trouve pour #{tenant_id}."
        except Exception as e:
            return f"LUNA ERREUR: {str(e)[:150]}"

    async def _cmd_broadcast(self, phone: str, role: str, args: str) -> str:
        """LUNA BROADCAST <message> — Message a TOUS les clients."""
        message = args.strip()
        if not message:
            return "LUNA: Usage: /broadcast <message>\nEx: /broadcast Maintenance prevue ce soir 22h"
        if not self.brain or not self.brain.redis:
            return "LUNA: Redis non disponible."
        try:
            redis = self.brain.redis
            # Trouver tous les tenants
            clients = await self._get_clients_summary()
            if not clients:
                return "LUNA: Aucun client a notifier."
            count = 0
            notif = json.dumps({
                "message": message,
                "timestamp": time.time(),
                "from": "fondateur",
                "type": "broadcast",
            })
            for c in clients:
                tid = c["id"]
                await redis.lpush(f"luna:{tid}:notifications", notif)
                await redis.ltrim(f"luna:{tid}:notifications", 0, 49)
                count += 1

            # Aussi dans les annonces globales
            await redis.lpush("luna:announcements", json.dumps({
                "message": message,
                "timestamp": time.time(),
                "by": phone[:15],
            }))
            await redis.ltrim("luna:announcements", 0, 49)

            return (
                f"LUNA: MESSAGE DIFFUSE\n"
                f"Envoye a {count} clients.\n"
                f"Message: {message[:100]}"
            )
        except Exception as e:
            return f"LUNA ERREUR: {str(e)[:150]}"

    async def _cmd_help(self, phone: str, role: str, args: str) -> str:
        """LUNA HELP — Liste des commandes."""
        if role == "founder":
            return (
                "LUNA — Commandes fondateur\n"
                "----------------------------\n"
                "LECTURE (pas de TOTP):\n"
                "  /status /health /threats\n"
                "  /clients — liste tous les clients\n"
                "  /client <id> — fiche complete\n"
                "  /quota <id> — conso client\n"
                "  /logs /errors /digest /cortex\n"
                "  /redis /config /version /uptime\n"
                "  /sessions /banned /whitelist\n"
                "  /processes /network /disk\n"
                "  /audit [jours] /couts\n"
                "\n"
                "GESTION CLIENTS (TOTP 10 min):\n"
                "  /register <email> <plan> <prenom> [nom]\n"
                "  /plan_set <id> <plan>\n"
                "  /kill <id> — suspendre\n"
                "  /revive <id> — reactiver\n"
                "  /quota_set <id> <res> <val>\n"
                "  /quota_reset <id>\n"
                "\n"
                "MESSAGES:\n"
                "  /msg <id> <texte> — a 1 client\n"
                "  /broadcast <texte> — a TOUS\n"
                "  /announce <texte> — annonce systeme\n"
                "\n"
                "SECURITE (TOTP 10 min):\n"
                "  /ban <ip> /unban <ip>\n"
                "  /wladd <ip> /wldel <ip>\n"
                "  /maintenance <msg>\n"
                "  /backup /purge <cible>\n"
                "  /ratelimit <val>\n"
                "  /export audit|couts|complet\n"
                "\n"
                "CRITIQUE (TOTP 2 min):\n"
                "  /lock <raison> /unlock\n"
                "  /shield on|off\n"
                "  /restart — redemarre le serveur\n"
                "  /stop — arret complet\n"
                "  /rekey — nouvelle cle API\n"
                "  /wipe <id> — supprime client\n"
            )
        return (
            "LUNA — Commandes exploitant\n"
            "----------------------------\n"
            "LECTURE:\n"
            "  etat / clients / quota <id>\n"
            "  journal / version / uptime / ping\n"
            "\n"
            "En francais libre:\n"
            "  comment va le serveur\n"
            "  montre les clients\n"
            "  quota du client 3\n"
            "\n"
            "LUNA AUTH <code totp> pour se connecter\n"
            "aide pour cette liste"
        )

    # ──────────────────────────────────────────
    # HELPERS — Interaction avec le systeme
    # ──────────────────────────────────────────

    def _normalize_phone(self, phone: str) -> str:
        """Normalise un numero de telephone."""
        phone = phone.strip().replace(" ", "").replace("-", "")
        if phone.startswith("0") and len(phone) == 10:
            phone = "+33" + phone[1:]
        return phone

    async def _get_system_status(self) -> dict:
        """Collecte le status systeme."""
        status = {
            "mode": "normal",
            "uptime": "inconnu",
            "active_clients": 0,
            "total_clients": 0,
            "redis_status": "inconnu",
            "threats_24h": 0,
            "banned_ips": 0,
            "cpu": 0,
            "ram": 0,
            "disk": 0,
            "last_backup": "inconnu",
            "cortex_status": "actif",
        }

        if self.brain:
            cortex = self.brain.get_cortex_status()
            status["mode"] = cortex.get("mode", "normal")
            status["uptime"] = cortex.get("uptime", "?")
            status["cortex_status"] = "actif" if cortex.get("vigil_active") else "degrade"

            if self.brain.vigil:
                v = self.brain.vigil.get_status()
                status["threats_24h"] = v.get("threats_24h", 0)
                status["banned_ips"] = v.get("banned_ips", 0)

        # System metrics
        try:
            import psutil
            status["cpu"] = int(psutil.cpu_percent(interval=0.1))
            status["ram"] = int(psutil.virtual_memory().percent)
            status["disk"] = int(psutil.disk_usage("/").percent)
        except ImportError:
            pass

        # Redis
        try:
            if self.brain and self.brain.redis:
                redis = self.brain.redis
                if hasattr(redis, 'ping'):
                    await redis.ping()
                    status["redis_status"] = "OK"
                    info = await redis.info("memory") if hasattr(redis, 'info') else {}
                    if info:
                        used = info.get("used_memory_human", "?")
                        status["redis_status"] = f"OK ({used})"
        except Exception:
            status["redis_status"] = "ERREUR"

        # Clients
        try:
            clients = await self._get_clients_summary()
            status["total_clients"] = len(clients)
            status["active_clients"] = sum(
                1 for c in clients if c.get("active"))
        except Exception:
            pass

        return status

    async def _get_health_details(self) -> dict:
        """Details de sante systeme."""
        health = {
            "redis_ram": "?",
            "redis_keys": "?",
            "cpu": "?",
            "disk_used": "?",
            "disk_total": "?",
            "ssl_days": "?",
            "openai_status": "?",
            "twilio_status": "?",
            "tavus_status": "?",
            "backup_age": "?",
        }

        try:
            import psutil
            health["cpu"] = f"{psutil.cpu_percent(interval=0.5):.1f}%"
            disk = psutil.disk_usage("/")
            health["disk_used"] = f"{disk.used // (1024**3)}G"
            health["disk_total"] = f"{disk.total // (1024**3)}G"
        except ImportError:
            pass

        # Redis details
        try:
            if self.brain and self.brain.redis:
                redis = self.brain.redis
                if hasattr(redis, 'info'):
                    info = await redis.info("memory")
                    health["redis_ram"] = info.get("used_memory_human", "?")
                if hasattr(redis, 'dbsize'):
                    keys = await redis.dbsize()
                    health["redis_keys"] = str(keys)
        except Exception:
            health["redis_ram"] = "ERREUR"

        # SSL check
        try:
            from pathlib import Path
            cert_path = Path(os.getenv("LUNA_BASE_PATH",
                                        str(Path(__file__).parent.parent.parent))) / "cert.pem"
            if cert_path.exists():
                import ssl
                import datetime
                cert = ssl.PEM_cert_to_DER_cert(cert_path.read_text())
                # Simplified — just check file age as proxy
                age_days = (time.time() - cert_path.stat().st_mtime) / 86400
                health["ssl_days"] = f"{max(0, 365 - int(age_days))}"
        except Exception:
            health["ssl_days"] = "?"

        return health

    async def _get_clients_summary(self) -> list[dict]:
        """Resume des clients depuis Redis."""
        clients = []
        try:
            if not self.brain or not self.brain.redis:
                return clients
            redis = self.brain.redis
            # Scan les tenants (profils principaux uniquement, pas les contacts)
            if hasattr(redis, 'keys'):
                keys = await redis.keys("luna:*:profile")
                for key in keys:
                    key_str = key.decode() if isinstance(key, bytes) else key
                    # Ignorer les profils de contacts (luna:X:contact:+phone:profile)
                    if ":contact:" in key_str:
                        continue
                    parts = key_str.split(":")
                    if len(parts) >= 3:
                        tenant_id = parts[1]
                        # Les profils sont des HASH Redis, pas des strings
                        try:
                            profile = await redis.hgetall(key)
                            if profile:
                                first = profile.get("first_name", "") or profile.get(b"first_name", b"").decode() if isinstance(profile.get(b"first_name", b""), bytes) else profile.get("first_name", "")
                                last = profile.get("last_name", "") or profile.get(b"last_name", b"").decode() if isinstance(profile.get(b"last_name", b""), bytes) else profile.get("last_name", "")
                                # Handle bytes keys from some redis clients
                                if not first and b"first_name" in profile:
                                    first = profile[b"first_name"].decode() if isinstance(profile[b"first_name"], bytes) else str(profile[b"first_name"])
                                if not last and b"last_name" in profile:
                                    last = profile[b"last_name"].decode() if isinstance(profile[b"last_name"], bytes) else str(profile[b"last_name"])
                                name = (f"{first} {last}").strip() or f"Client {tenant_id}"
                            else:
                                name = f"Client {tenant_id}"
                        except Exception:
                            name = f"Client {tenant_id}"

                        # Plan: lire depuis luna:auth:* ou le profil
                        plan = "?"
                        try:
                            auth_keys = await redis.keys(f"luna:auth:*")
                            for ak in auth_keys:
                                ak_str = ak.decode() if isinstance(ak, bytes) else ak
                                if ak_str in ("luna:auth:next_tenant_id", "luna:auth:tenant_index"):
                                    continue
                                auth_data = await redis.get(ak)
                                if auth_data:
                                    auth_str = auth_data.decode() if isinstance(auth_data, bytes) else auth_data
                                    a = json.loads(auth_str)
                                    if str(a.get("tenant_id")) == str(tenant_id):
                                        plan = a.get("plan", "?")
                                        break
                        except Exception:
                            pass

                        # Quota check
                        quota_key = f"luna:{tenant_id}:quota"
                        quota_pct = 0
                        try:
                            quota_raw = await redis.hgetall(quota_key)
                            if quota_raw:
                                for resource in ["sms", "voice", "visio"]:
                                    used_key = f"{resource}_used"
                                    limit_key = f"{resource}_limit"
                                    used = int(quota_raw.get(used_key, quota_raw.get(used_key.encode(), 0)) or 0)
                                    limit = int(quota_raw.get(limit_key, quota_raw.get(limit_key.encode(), 1)) or 1)
                                    if limit > 0:
                                        pct = int(used / limit * 100)
                                        quota_pct = max(quota_pct, pct)
                        except Exception:
                            pass

                        clients.append({
                            "id": tenant_id,
                            "name": name,
                            "plan": plan,
                            "active": True,
                            "quota_pct": quota_pct,
                        })
        except Exception as e:
            logger.error(f"Erreur listing clients: {e}")
        return clients

    async def _get_client_quota(self, tenant_id: str) -> Optional[dict]:
        """Quota detaille d'un client."""
        # Limites par plan
        PLAN_LIMITS = {
            "essentiel": {"sms": 25, "voice": 40, "visio": 12},
            "confort": {"sms": 50, "voice": 100, "visio": 28},
            "premium": {"sms": 100, "voice": 180, "visio": 55},
        }
        try:
            if not self.brain or not self.brain.redis:
                return None
            redis = self.brain.redis

            # Vérifier que le profil existe
            profile = await redis.hgetall(f"luna:{tenant_id}:profile")
            if not profile:
                return None

            # Trouver le plan depuis luna:auth:*
            plan = "?"
            auth_keys = await redis.keys("luna:auth:*")
            for ak in auth_keys:
                ak_str = ak.decode() if isinstance(ak, bytes) else ak
                if ak_str in ("luna:auth:next_tenant_id", "luna:auth:tenant_index"):
                    continue
                auth_data = await redis.get(ak)
                if auth_data:
                    auth_str = auth_data.decode() if isinstance(auth_data, bytes) else auth_data
                    a = json.loads(auth_str)
                    if str(a.get("tenant_id")) == str(tenant_id):
                        plan = a.get("plan", "?")
                        break

            limits = PLAN_LIMITS.get(plan, {"sms": 0, "voice": 0, "visio": 0})

            # Lire l'usage du mois courant
            from datetime import datetime
            today = datetime.now().strftime("%Y-%m-%d")
            month_prefix = datetime.now().strftime("%Y-%m")
            usage_keys = await redis.keys(f"luna:{tenant_id}:usage:{month_prefix}-*")

            sms_used = 0
            voice_used = 0
            visio_used = 0
            chat_count = 0
            api_cost = 0.0
            for uk in usage_keys:
                usage = await redis.hgetall(uk)
                if usage:
                    sms_used += int(usage.get("sms_count", usage.get(b"sms_count", 0)) or 0)
                    voice_used += int(usage.get("voice_minutes", usage.get(b"voice_minutes", 0)) or 0)
                    visio_used += int(usage.get("visio_minutes", usage.get(b"visio_minutes", 0)) or 0)
                    chat_count += int(usage.get("messages_count", usage.get(b"messages_count", 0)) or 0)

            return {
                "plan": plan,
                "sms_used": sms_used,
                "sms_limit": limits["sms"],
                "voice_used": voice_used,
                "voice_limit": limits["voice"],
                "visio_used": visio_used,
                "visio_limit": limits["visio"],
                "chat_count": chat_count,
                "api_cost": api_cost,
            }
        except Exception:
            return None

    async def _suspend_tenant(self, tenant_id: str) -> bool:
        """Suspend un tenant."""
        try:
            if not self.brain or not self.brain.redis:
                return False
            redis = self.brain.redis
            await redis.set(f"luna:{tenant_id}:suspended", "true")
            logger.warning(f"Tenant {tenant_id} suspendu via SMS d'urgence")
            return True
        except Exception:
            return False

    async def _reactivate_tenant(self, tenant_id: str) -> bool:
        """Reactive un tenant."""
        try:
            if not self.brain or not self.brain.redis:
                return False
            redis = self.brain.redis
            await redis.delete(f"luna:{tenant_id}:suspended")
            logger.info(f"Tenant {tenant_id} reactive via SMS d'urgence")
            return True
        except Exception:
            return False

    async def _get_recent_events(self, count: int = 10) -> list[dict]:
        """Derniers evenements du Cortex."""
        try:
            if not self.brain or not self.brain.redis:
                return []
            redis = self.brain.redis
            if hasattr(redis, 'lrange'):
                raw = await redis.lrange("cortex:signals", 0, count - 1)
                events = []
                for r in raw:
                    try:
                        events.append(json.loads(r))
                    except (json.JSONDecodeError, TypeError):
                        pass
                return events
        except Exception:
            return []

    async def _get_recent_errors(self, count: int = 10) -> list[dict]:
        """Dernieres erreurs."""
        try:
            if not self.brain or not self.brain.redis:
                return []
            redis = self.brain.redis
            if hasattr(redis, 'lrange'):
                raw = await redis.lrange("cortex:errors", 0, count - 1)
                errors = []
                for r in raw:
                    try:
                        errors.append(json.loads(r))
                    except (json.JSONDecodeError, TypeError):
                        pass
                return errors
        except Exception:
            return []

    # ──────────────────────────────────────────
    # AUDIT + COUTS + EXPORT PDF
    # ──────────────────────────────────────────

    async def _cmd_audit(self, phone: str, role: str, args: str) -> str:
        """LUNA AUDIT [jours] — Journal d'audit."""
        if not self._audit_logger:
            return "LUNA: Audit non disponible."

        days = 1
        if args.strip().isdigit():
            days = min(int(args.strip()), 90)

        entries = await self._audit_logger.get_entries_for_period(days)
        if not entries:
            return f"LUNA: Aucune action dans le journal ({days}j)."

        lines = [f"LUNA AUDIT ({days}j, {len(entries)} actions)",
                 "=" * 30]
        for e in entries[:15]:
            dt = datetime.fromtimestamp(e.timestamp)
            status = "OK" if e.success else "ERR"
            lines.append(
                f"[{dt.strftime('%d/%m %H:%M')}] "
                f"{e.actor_name[:10]} {e.command} {status}"
            )
        if len(entries) > 15:
            lines.append(f"... +{len(entries) - 15} autres")
            lines.append("Pour le PDF: /export audit")
        return "\n".join(lines)

    async def _cmd_couts(self, phone: str, role: str, args: str) -> str:
        """LUNA COUTS — Resume des couts du mois."""
        if not self._cost_tracker:
            return "LUNA: Suivi des couts non disponible."

        costs = await self._cost_tracker.get_month_costs()
        sms_c = costs.get("sms_count", 0)
        sms_cost = costs.get("sms_cost", 0)
        ai_cost = costs.get("openai_cost", 0)
        tavus_min = costs.get("tavus_minutes", 0)
        tavus_cost = costs.get("tavus_cost", 0)
        total = costs.get("total_cost", 0)

        lines = [
            f"LUNA COUTS (mois en cours)",
            "=" * 28,
            "GLOBAL:",
            f"  SMS Twilio: {sms_c} x 0.07EUR = {sms_cost:.2f} EUR",
            f"  Tavus visio: {tavus_min:.0f} min = {tavus_cost:.2f} EUR",
            f"  OpenAI: {ai_cost:.2f} EUR",
            f"  TOTAL: {total:.2f} EUR",
        ]

        # Detail par tenant
        try:
            per_tenant = await self._cost_tracker.get_month_costs_per_tenant()
            if per_tenant:
                # Chercher les noms des clients
                clients = await self._get_clients_summary()
                name_map = {c["id"]: c["name"] for c in clients}
                lines.append("")
                lines.append("PAR CLIENT:")
                for tid, tc in sorted(per_tenant.items()):
                    name = name_map.get(tid, f"#{tid}")[:12]
                    t_sms = tc.get("sms_count", 0)
                    t_sms_c = tc.get("sms_cost", 0)
                    t_vis = tc.get("tavus_minutes", 0)
                    t_vis_c = tc.get("tavus_cost", 0)
                    t_total = t_sms_c + t_vis_c
                    parts = []
                    if t_sms > 0:
                        parts.append(f"{t_sms} SMS={t_sms_c:.2f}EUR")
                    if t_vis > 0:
                        parts.append(f"{t_vis:.0f}min visio={t_vis_c:.2f}EUR")
                    detail = " | ".join(parts) if parts else "0 EUR"
                    lines.append(f"  {name}: {detail}")
        except Exception:
            pass

        lines.append(f"\nPour le PDF: /export couts")
        return "\n".join(lines)

    async def _cmd_export(self, phone: str, role: str, args: str) -> str:
        """LUNA EXPORT <type> [param] — Generer et envoyer un PDF."""
        if not self._pdf_exporter:
            return "LUNA: Export PDF non disponible."

        if not phone.startswith("telegram:"):
            return "LUNA: L'export PDF est disponible uniquement via Telegram."

        chat_id = int(phone.split(":")[1])

        parts = args.strip().lower().split()
        export_type = parts[0] if parts else "audit"
        param = parts[1] if len(parts) > 1 else ""

        try:
            if export_type in ("audit", "historique"):
                days = int(param) if param.isdigit() else 7
                pdf_buf = await self._pdf_exporter.generate_audit_pdf(days)
                filename = f"audit_luna_{datetime.now().strftime('%Y%m%d')}.pdf"
            elif export_type in ("couts", "costs", "depenses"):
                pdf_buf = await self._pdf_exporter.generate_costs_pdf(
                    param or None)
                filename = f"couts_luna_{datetime.now().strftime('%Y%m')}.pdf"
            elif export_type in ("complet", "full", "tout"):
                days = int(param) if param.isdigit() else 30
                pdf_buf = await self._pdf_exporter.generate_combined_pdf(days)
                filename = f"rapport_luna_{datetime.now().strftime('%Y%m%d')}.pdf"
            else:
                return (
                    "LUNA: Types d'export:\n"
                    "  /export audit [jours]\n"
                    "  /export couts [YYYY-MM]\n"
                    "  /export complet [jours]"
                )

            # Envoyer via Telegram
            if self.brain and self.brain.telegram_bot:
                success = await self.brain.telegram_bot.send_document(
                    chat_id, pdf_buf, filename,
                    caption=f"Export {export_type} - Luna Cortex",
                )
                if success:
                    return f"LUNA: PDF {export_type} envoye."
                return "LUNA: Erreur envoi PDF."
            return "LUNA: Telegram non disponible."

        except Exception as e:
            logger.error(f"Export PDF erreur: {e}")
            return f"LUNA: Erreur generation PDF: {str(e)[:100]}"
