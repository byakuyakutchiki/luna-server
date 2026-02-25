"""
BRIEFING ENGINE — Notifications vers l'exploitant ET le fondateur.

4 modes de notification:
- URGENT (SMS immediat) : piratage, crash, fraude
- ALERTE (Telegram temps reel) : anomalies, quotas critiques
- DIGEST (SMS/Telegram 8h+20h) : resume quotidien
- HEBDO (Telegram lundi 9h) : rapport complet semaine

Le fondateur recoit une vue MULTI-EXPLOITANT.
L'exploitant recoit les infos de SON serveur.
"""

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional

import httpx

from .config import CortexConfig, CortexState
from .signals import Severity, Signal

logger = logging.getLogger("cortex.briefing")


class BriefingEngine:
    """Envoie les briefings aux bonnes personnes au bon moment."""

    def __init__(self, config: CortexConfig, redis_client=None):
        self.config = config
        self.redis = redis_client
        self._cooldowns: dict[str, float] = {}  # hash -> timestamp
        self._http: Optional[httpx.AsyncClient] = None

    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(timeout=10.0)
        return self._http

    async def close(self):
        if self._http and not self._http.is_closed:
            await self._http.aclose()

    # ──────────────────────────────────────────
    # SMS via Twilio
    # ──────────────────────────────────────────

    async def send_sms(self, to: str, message: str) -> bool:
        """Envoie un SMS via Twilio."""
        if not all([self.config.twilio_account_sid,
                    self.config.twilio_auth_token,
                    self.config.twilio_sms_from, to]):
            logger.warning("SMS non envoye: config Twilio incomplete")
            return False

        try:
            http = await self._get_http()
            url = (f"https://api.twilio.com/2010-04-01/Accounts/"
                   f"{self.config.twilio_account_sid}/Messages.json")
            resp = await http.post(
                url,
                auth=(self.config.twilio_account_sid,
                      self.config.twilio_auth_token),
                data={
                    "From": self.config.twilio_sms_from,
                    "To": to,
                    "Body": message[:1600],  # Limite Twilio
                },
            )
            if resp.status_code == 201:
                logger.info(f"SMS envoye a {to[:8]}...")
                # Suivi des couts
                if hasattr(self, '_cost_tracker') and self._cost_tracker:
                    try:
                        await self._cost_tracker.track_sms()
                    except Exception:
                        pass
                return True
            else:
                logger.error(f"SMS echec {resp.status_code}: {resp.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"SMS erreur: {e}")
            return False

    # ──────────────────────────────────────────
    # Telegram
    # ──────────────────────────────────────────

    async def send_telegram(self, chat_id: str, message: str,
                            parse_mode: str = "HTML") -> bool:
        """Envoie un message Telegram."""
        if not all([self.config.telegram_bot_token, chat_id]):
            logger.debug("Telegram non envoye: config incomplete")
            return False

        try:
            http = await self._get_http()
            url = (f"https://api.telegram.org/bot"
                   f"{self.config.telegram_bot_token}/sendMessage")
            resp = await http.post(url, json={
                "chat_id": chat_id,
                "text": message[:4000],
                "parse_mode": parse_mode,
            })
            if resp.status_code == 200:
                return True
            else:
                logger.error(f"Telegram echec: {resp.text[:200]}")
                return False
        except Exception as e:
            logger.error(f"Telegram erreur: {e}")
            return False

    # ──────────────────────────────────────────
    # Anti-spam / Cooldown
    # ──────────────────────────────────────────

    def _cooldown_key(self, severity: Severity, message: str) -> str:
        h = hashlib.md5(f"{severity.value}:{message[:100]}".encode()).hexdigest()[:12]
        return f"cooldown:{h}"

    def _is_in_cooldown(self, severity: Severity, message: str) -> bool:
        key = self._cooldown_key(severity, message)
        last = self._cooldowns.get(key, 0)
        cooldown_map = {
            Severity.INFO: 600,
            Severity.WARNING: 300,
            Severity.CRITICAL: 60,
            Severity.EMERGENCY: 0,
        }
        return (time.time() - last) < cooldown_map.get(severity, 300)

    def _mark_sent(self, severity: Severity, message: str):
        key = self._cooldown_key(severity, message)
        self._cooldowns[key] = time.time()

    async def _can_send_urgent_sms(self) -> bool:
        """Verifie le quota SMS urgents du jour."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self.redis:
            key = "cortex:urgent_sms_count"
            date_key = "cortex:urgent_sms_date"
            stored_date = await self.redis.get(date_key) if hasattr(self.redis, 'get') else None
            if stored_date and stored_date.decode() != today:
                await self.redis.set(key, 0)
                await self.redis.set(date_key, today)
            count = await self.redis.get(key) if hasattr(self.redis, 'get') else None
            return int(count or 0) < self.config.max_urgent_sms_per_day
        return True

    async def _increment_urgent_sms(self):
        if self.redis:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            await self.redis.set("cortex:urgent_sms_date", today)
            await self.redis.incr("cortex:urgent_sms_count")

    # ──────────────────────────────────────────
    # DISPATCH — Envoie selon la severite
    # ──────────────────────────────────────────

    async def dispatch(self, signal: Signal):
        """Route un signal vers les bons canaux selon sa severite."""
        if self._is_in_cooldown(signal.severity, signal.message):
            logger.debug(f"Signal en cooldown: {signal.title}")
            return

        self._mark_sent(signal.severity, signal.message)

        # Log Redis pour historique
        await self._log_signal(signal)

        if signal.severity == Severity.EMERGENCY:
            await self._send_urgent(signal)
        elif signal.severity == Severity.CRITICAL:
            await self._send_alert(signal)
        elif signal.severity == Severity.WARNING:
            await self._send_warning(signal)
        else:
            # INFO — juste log, sera dans le digest
            logger.info(f"[CORTEX] {signal.title}: {signal.message}")

    async def _send_urgent(self, signal: Signal):
        """EMERGENCY → SMS immediat a l'exploitant + fondateur."""
        prefix = "LUNA URGENCE"
        msg = f"{prefix}\n{signal.title}\n{signal.message}"

        if signal.ip:
            msg += f"\nIP: {signal.ip}"
        msg += f"\nHeure: {datetime.now().strftime('%H:%M:%S')}"

        # SMS exploitant
        if await self._can_send_urgent_sms():
            if self.config.exploitant_phone:
                await self.send_sms(self.config.exploitant_phone, msg)
            # SMS fondateur (toujours pour EMERGENCY)
            if self.config.founder_phone:
                founder_msg = (
                    f"{prefix} [FOUNDER]\n"
                    f"Serveur: {self.config.exploitant_phone or 'inconnu'}\n"
                    f"{signal.title}\n{signal.message}"
                )
                await self.send_sms(self.config.founder_phone, founder_msg)
            await self._increment_urgent_sms()

        # Telegram aussi (immediat)
        tg_msg = (
            f"<b>{prefix}</b>\n"
            f"<b>{signal.title}</b>\n"
            f"{signal.message}\n"
        )
        if signal.ip:
            tg_msg += f"IP: <code>{signal.ip}</code>\n"
        tg_msg += f"Heure: {datetime.now().strftime('%H:%M:%S')}"

        if self.config.exploitant_telegram_chat_id:
            await self.send_telegram(
                self.config.exploitant_telegram_chat_id, tg_msg)
        if self.config.founder_telegram_chat_id:
            await self.send_telegram(
                self.config.founder_telegram_chat_id,
                f"[SERVEUR {self.config.exploitant_phone or '?'}]\n{tg_msg}")

    async def _send_alert(self, signal: Signal):
        """CRITICAL → Telegram temps reel + SMS si tres grave."""
        tg_msg = (
            f"<b>ALERTE LUNA</b>\n"
            f"<b>{signal.title}</b>\n"
            f"{signal.message}\n"
            f"Heure: {datetime.now().strftime('%H:%M:%S')}"
        )
        if self.config.exploitant_telegram_chat_id:
            await self.send_telegram(
                self.config.exploitant_telegram_chat_id, tg_msg)
        if self.config.founder_telegram_chat_id:
            await self.send_telegram(
                self.config.founder_telegram_chat_id, tg_msg)

    async def _send_warning(self, signal: Signal):
        """WARNING → Telegram seulement."""
        tg_msg = (
            f"<b>Luna Warning</b>\n"
            f"{signal.title}\n"
            f"{signal.message}"
        )
        if self.config.exploitant_telegram_chat_id:
            await self.send_telegram(
                self.config.exploitant_telegram_chat_id, tg_msg)

    # ──────────────────────────────────────────
    # DIGEST QUOTIDIEN
    # ──────────────────────────────────────────

    async def generate_digest(self, health: dict, threats: dict,
                               business: dict) -> str:
        """Genere le digest quotidien."""
        now = datetime.now()
        lines = [
            f"LUNA DIGEST — {now.strftime('%d %b %Y, %Hh%M')}",
            "=" * 36,
            "",
            "SYSTEME:",
            f"  Redis: {health.get('redis_memory_pct', '?')}% RAM",
            f"  CPU: {health.get('cpu_usage_pct', '?')}%",
            f"  Disque: {health.get('disk_usage_pct', '?')}%",
            f"  Uptime: {self._format_uptime(health.get('uptime_seconds', 0))}",
            f"  Mode: {health.get('luna_mode', 'normal')}",
            "",
            "SECURITE:",
            f"  Menaces 24h: {threats.get('total_threats_24h', 0)}",
            f"  IPs bannies: {threats.get('banned_ips', 0)}",
            f"  Requetes bloquees: {threats.get('blocked_requests_24h', 0)}",
            f"  Actions auto: {len(threats.get('auto_actions_taken', []))}",
            "",
            "BUSINESS:",
            f"  Clients actifs: {business.get('active_clients', 0)}"
            f"/{business.get('total_clients', 0)}",
            f"  MRR: {business.get('mrr', 0):.0f}EUR",
            f"  Quotas critiques: {business.get('quota_critical', 0)} clients",
            f"  Inactifs >14j: {business.get('inactive_clients', 0)}",
            "",
        ]

        # Ajouter les actions prises
        actions = threats.get("auto_actions_taken", [])
        if actions:
            lines.append("ACTIONS CORTEX:")
            for a in actions[-5:]:  # 5 dernieres
                lines.append(f"  - {a}")
            lines.append("")

        # Verdict
        score = self._health_score(health, threats)
        if score >= 90:
            lines.append("Tout va bien. Luna gere.")
        elif score >= 70:
            lines.append("Quelques points d'attention. Sous controle.")
        elif score >= 50:
            lines.append("ATTENTION: intervention recommandee.")
        else:
            lines.append("CRITIQUE: action requise!")

        return "\n".join(lines)

    async def send_digest(self, health: dict, threats: dict,
                           business: dict):
        """Envoie le digest a l'exploitant et au fondateur."""
        digest = await self.generate_digest(health, threats, business)

        # Telegram exploitant
        if self.config.exploitant_telegram_chat_id:
            await self.send_telegram(
                self.config.exploitant_telegram_chat_id,
                f"<pre>{digest}</pre>")

        # SMS exploitant (version courte)
        if self.config.exploitant_phone:
            short = self._shorten_digest(digest)
            await self.send_sms(self.config.exploitant_phone, short)

        # Telegram fondateur (avec identifiant serveur)
        if self.config.founder_telegram_chat_id:
            header = f"[SERVEUR: {self.config.exploitant_phone or 'inconnu'}]\n"
            await self.send_telegram(
                self.config.founder_telegram_chat_id,
                f"<pre>{header}{digest}</pre>")

    # ──────────────────────────────────────────
    # RAPPORT HEBDO
    # ──────────────────────────────────────────

    async def generate_weekly(self, week_data: dict) -> str:
        """Genere le rapport hebdomadaire."""
        now = datetime.now()
        lines = [
            f"RAPPORT HEBDO LUNA",
            f"Semaine du {week_data.get('week_start', '?')}"
            f" au {week_data.get('week_end', '?')}",
            "=" * 40,
            "",
            "BUSINESS:",
            f"  Nouveaux clients: +{week_data.get('new_clients', 0)}",
            f"  Desabonnements: {week_data.get('churned', 0)}",
            f"  CA semaine: {week_data.get('revenue_week', 0):.0f}EUR",
            f"  MRR actuel: {week_data.get('mrr', 0):.0f}EUR",
            "",
            "TECHNIQUE:",
            f"  Uptime: {week_data.get('uptime_pct', 0):.2f}%",
            f"  Requetes totales: {week_data.get('total_requests', 0):,}",
            f"  Temps reponse moyen: {week_data.get('avg_latency_ms', 0):.0f}ms",
            f"  Incidents securite: {week_data.get('security_incidents', 0)}",
            f"    (auto-resolus: {week_data.get('auto_resolved', 0)})",
            "",
            "CLIENTS:",
            f"  Plus actif: {week_data.get('most_active', 'N/A')}",
            f"  A risque churn: {week_data.get('churn_risk', 'aucun')}",
            f"  Quotas critiques: {week_data.get('quota_critical', 0)}",
            "",
            "ACTIONS CORTEX CETTE SEMAINE:",
        ]
        for action in week_data.get("cortex_actions", [])[:10]:
            lines.append(f"  - {action}")
        if not week_data.get("cortex_actions"):
            lines.append("  Aucune action necessaire")

        return "\n".join(lines)

    # ──────────────────────────────────────────
    # BRIEF FONDATEUR MULTI-EXPLOITANT
    # ──────────────────────────────────────────

    async def brief_founder(self, message: str,
                             severity: Severity = Severity.INFO):
        """Brief specifique au fondateur."""
        if severity in (Severity.EMERGENCY, Severity.CRITICAL):
            if self.config.founder_phone:
                await self.send_sms(self.config.founder_phone, message)
        if self.config.founder_telegram_chat_id:
            await self.send_telegram(
                self.config.founder_telegram_chat_id, message)

    # ──────────────────────────────────────────
    # UTILS
    # ──────────────────────────────────────────

    async def _log_signal(self, signal: Signal):
        """Log le signal dans Redis pour historique."""
        if not self.redis:
            return
        try:
            key = "cortex:signals"
            data = json.dumps(signal.to_dict())
            if hasattr(self.redis, 'lpush'):
                await self.redis.lpush(key, data)
                await self.redis.ltrim(key, 0, 999)  # Garder 1000 derniers
        except Exception as e:
            logger.debug(f"Log signal Redis erreur: {e}")

    def _format_uptime(self, seconds: float) -> str:
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        if days > 0:
            return f"{days}j {hours}h"
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h{minutes:02d}m"

    def _health_score(self, health: dict, threats: dict) -> int:
        """Score de sante global 0-100."""
        score = 100
        ram = health.get("redis_memory_pct", 0)
        if ram > 95:
            score -= 30
        elif ram > 80:
            score -= 10
        cpu = health.get("cpu_usage_pct", 0)
        if cpu > 90:
            score -= 20
        elif cpu > 70:
            score -= 5
        disk = health.get("disk_usage_pct", 0)
        if disk > 90:
            score -= 20
        elif disk > 80:
            score -= 5
        t = threats.get("total_threats_24h", 0)
        if t > 50:
            score -= 20
        elif t > 10:
            score -= 5
        if health.get("luna_mode") == "lockdown":
            score -= 30
        return max(0, score)

    def _shorten_digest(self, digest: str) -> str:
        """Version courte du digest pour SMS (160 chars max useful)."""
        lines = digest.split("\n")
        parts = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("="):
                continue
            if line.startswith(("SYSTEME", "SECURITE", "BUSINESS",
                                "ACTIONS", "Tout va", "Quelques",
                                "ATTENTION", "CRITIQUE")):
                parts.append(line)
            elif ":" in line and any(
                kw in line for kw in
                ["Redis", "Menaces", "Clients actifs", "MRR", "Mode"]
            ):
                parts.append(line.strip())
        return "\n".join(parts)[:1500]
