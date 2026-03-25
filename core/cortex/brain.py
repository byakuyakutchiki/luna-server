"""
LUNA CORTEX BRAIN — Le cerveau autonome.

Boucle principale toutes les 30 secondes:
1. Collecte les signaux (Vigil, Doctor, Accountant)
2. Analyse avec GPT-4o-mini (toutes les 5 min)
3. Decide des actions
4. Execute les actions
5. Brief l'exploitant et le fondateur

C'est le chef d'orchestre. Il orchestre Vigil (securite),
Doctor (sante systeme) et Accountant (business).
Les commandes SMS d'urgence passent par EmergencyMode.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

import httpx

from .audit import CortexAuditLogger, CortexCostTracker, CortexPDFExporter
from .auth import CortexAuth
from .briefing import BriefingEngine
from .config import CortexConfig, CortexState
from .emergency import EmergencyMode
from .signals import (
    ActionType, CortexAction, Severity, Signal,
    SignalSource, SystemHealth,
)
from .telegram_bot import CortexTelegramBot
from .vigil import VigilAgent

logger = logging.getLogger("cortex.brain")


class LunaCortex:
    """
    Le cerveau autonome de Luna.
    Tourne en background dans le meme process FastAPI.
    """

    def __init__(self, config: CortexConfig, redis_client=None):
        self.config = config
        self.redis = redis_client
        self._start_time = time.time()
        self._loop_count = 0
        self._signals_processed = 0
        self._actions_executed = 0
        self._last_ai_analysis = 0
        self._last_digest_time = 0
        self._last_weekly_time = 0
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Mode actuel
        self.state = CortexState()

        # Auth (TOTP + API Key + Telegram ID)
        self.auth = CortexAuth()

        # Audit trail + couts + PDF
        self.audit_logger = CortexAuditLogger(redis_client)
        self.cost_tracker = CortexCostTracker(redis_client)
        self.pdf_exporter = CortexPDFExporter(self.audit_logger,
                                               self.cost_tracker)

        # Agents
        self.vigil = VigilAgent(config, redis_client)
        self.briefing = BriefingEngine(config, redis_client)
        self.briefing._cost_tracker = self.cost_tracker
        self.emergency = EmergencyMode(config, cortex_brain=self)
        self.emergency._auth = self.auth  # Injecter l'auth TOTP
        self.emergency._audit_logger = self.audit_logger
        self.emergency._cost_tracker = self.cost_tracker
        self.emergency._pdf_exporter = self.pdf_exporter

        # Telegram Bot
        self.telegram_bot = CortexTelegramBot(
            bot_token=config.telegram_bot_token,
            auth=self.auth,
            cortex_brain=self,
        )
        self._telegram_task: Optional[asyncio.Task] = None

        # Doctor et Accountant seront ajoutes (Phase 2/3)
        self.doctor = None
        self.accountant = None

        # Afficher les infos de setup si nouveau
        new_key = self.auth.get_new_api_key()
        if new_key:
            logger.warning(f"NOUVELLE CLE API CORTEX: {new_key}")
            logger.warning("Sauvegardez-la! Elle ne sera plus affichee.")

        logger.info("Luna Cortex initialise (TOTP + Telegram + CLI)")

    # ──────────────────────────────────────────
    # LIFECYCLE
    # ──────────────────────────────────────────

    async def start(self):
        """Demarre la boucle principale du Cortex."""
        if self._running:
            return
        self._running = True

        # Charger les secrets auth depuis Redis (persistance Cloud Run)
        await self.auth.async_init(self.redis)

        self._task = asyncio.create_task(self._main_loop())
        # Telegram: webhook sur Cloud Run, polling en local
        if self.config.telegram_bot_token:
            if os.getenv("ENVIRONMENT") == "cloudrun":
                # Cloud Run: configurer le webhook
                service_url = os.getenv("CLOUD_RUN_URL", "")
                if not service_url:
                    # Detecter l'URL du service Cloud Run
                    service_url = os.getenv("K_SERVICE_URL", "")
                if service_url:
                    webhook_url = f"{service_url}/api/cortex/telegram/webhook"
                    await self.telegram_bot.setup_webhook(webhook_url)
                    logger.info(f"Telegram bot en mode WEBHOOK: {webhook_url}")
                else:
                    logger.warning("Cloud Run sans URL de service, "
                                   "Telegram webhook non configure")
            else:
                # Local: polling classique
                self._telegram_task = asyncio.create_task(
                    self.telegram_bot.start_polling())
                logger.info("Telegram bot en mode POLLING")
        logger.info("Luna Cortex DEMARRE — boucle toutes les "
                     f"{self.config.loop_interval_seconds}s")

        # Brief de demarrage
        await self.briefing.dispatch(Signal(
            source=SignalSource.SYSTEM,
            severity=Severity.INFO,
            category="system",
            title="Cortex demarre",
            message=f"Luna Cortex v1.0 en ligne. Mode: {self.state.mode}.",
        ))

    async def stop(self):
        """Arrete le Cortex proprement."""
        self._running = False
        if self._telegram_task:
            await self.telegram_bot.stop_polling()
            self._telegram_task.cancel()
            try:
                await self._telegram_task
            except asyncio.CancelledError:
                pass
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self.briefing.close()
        logger.info("Luna Cortex ARRETE")

    # ──────────────────────────────────────────
    # BOUCLE PRINCIPALE
    # ──────────────────────────────────────────

    async def _main_loop(self):
        """Boucle infinie du Cortex."""
        while self._running:
            try:
                await self._tick()
                self._loop_count += 1
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cortex erreur boucle: {e}", exc_info=True)
                # Log l'erreur dans Redis
                await self._log_error(str(e))
            await asyncio.sleep(self.config.loop_interval_seconds)

    async def _tick(self):
        """Un cycle du Cortex."""
        now = time.time()
        signals: list[Signal] = []

        # 1. Scan Vigil (securite)
        vigil_signals = self.vigil.periodic_scan()
        signals.extend(vigil_signals)

        # 2. Analyse IA (toutes les 5 min)
        if now - self._last_ai_analysis > self.config.ai_analysis_interval:
            ai_signals = await self._ai_analysis()
            signals.extend(ai_signals)
            self._last_ai_analysis = now

        # 3. Check si c'est l'heure du digest
        current_hour = datetime.now().hour
        if (current_hour in self.config.digest_hours and
                now - self._last_digest_time > 3600):
            await self._send_scheduled_digest()
            self._last_digest_time = now

        # 4. Check si c'est l'heure du rapport hebdo
        current_day = datetime.now().weekday()
        if (current_day == self.config.weekly_report_day and
                current_hour == self.config.weekly_report_hour and
                now - self._last_weekly_time > 86400):
            await self._send_weekly_report()
            self._last_weekly_time = now

        # 5. Dispatch tous les signaux
        for signal in signals:
            await self._handle_signal(signal)
            self._signals_processed += 1

    # ──────────────────────────────────────────
    # TRAITEMENT DES SIGNAUX
    # ──────────────────────────────────────────

    async def _handle_signal(self, signal: Signal):
        """Traite un signal : decide l'action + brief."""
        # Decides les actions automatiques
        actions = self._decide_actions(signal)

        # Execute les actions
        for action in actions:
            await self._execute_action(action)
            signal.actions_taken.append(action.action_type.value)
            self._actions_executed += 1

        # Brief selon la severite
        await self.briefing.dispatch(signal)
        signal.handled = True

    def _decide_actions(self, signal: Signal) -> list[CortexAction]:
        """Decide les actions basees sur un signal."""
        actions = []

        # EMERGENCY → actions immediates
        if signal.severity == Severity.EMERGENCY:
            if signal.threat_type and signal.ip:
                # Auto-ban pour les menaces EMERGENCY
                actions.append(CortexAction(
                    action_type=ActionType.BAN_IP,
                    target=signal.ip,
                    reason=signal.title,
                    decided_by="cortex_auto",
                ))

            # Code tampering → lockdown
            from .signals import ThreatType
            if signal.threat_type == ThreatType.CODE_TAMPERING:
                actions.append(CortexAction(
                    action_type=ActionType.LOCKDOWN,
                    reason="Code tampering detecte",
                    decided_by="cortex_auto",
                ))

            # DDoS → shield mode
            if signal.threat_type == ThreatType.DDOS:
                actions.append(CortexAction(
                    action_type=ActionType.SHIELD_ON,
                    reason="DDoS detecte",
                    decided_by="cortex_auto",
                ))

        return actions

    async def _execute_action(self, action: CortexAction):
        """Execute une action decidee."""
        try:
            if action.action_type == ActionType.BAN_IP:
                self.vigil.manual_ban(
                    action.target,
                    reason=action.reason,
                    by=action.decided_by)
                action.result = f"IP {action.target} bannie"

            elif action.action_type == ActionType.UNBAN_IP:
                self.vigil.manual_unban(action.target, by=action.decided_by)
                action.result = f"IP {action.target} debannie"

            elif action.action_type == ActionType.LOCKDOWN:
                await self.set_mode("lockdown",
                                     reason=action.reason,
                                     by=action.decided_by)
                action.result = "Serveur en lockdown"

            elif action.action_type == ActionType.UNLOCK:
                await self.set_mode("normal", by=action.decided_by)
                action.result = "Serveur deverrouille"

            elif action.action_type == ActionType.SHIELD_ON:
                await self.set_mode("shield",
                                     reason=action.reason,
                                     by=action.decided_by)
                action.result = "Mode bouclier active"

            elif action.action_type == ActionType.SHIELD_OFF:
                await self.set_mode("normal", by=action.decided_by)
                action.result = "Mode bouclier desactive"

            elif action.action_type == ActionType.BACKUP:
                if self.redis and hasattr(self.redis, 'bgsave'):
                    await self.redis.bgsave()
                    action.result = "Backup lance"

            action.executed = True
            logger.info(f"Action executee: {action.action_type.value} "
                        f"→ {action.result}")

            # Audit trail pour actions automatiques
            await self.audit_logger.log(
                actor_id="cortex",
                role="system",
                source="auto",
                command=action.action_type.value.upper(),
                args=action.target or "",
                result=action.result or "",
                success=True,
            )

        except Exception as e:
            action.result = f"Erreur: {e}"
            logger.error(f"Erreur execution action "
                         f"{action.action_type.value}: {e}")

    # ──────────────────────────────────────────
    # MODE DU SERVEUR
    # ──────────────────────────────────────────

    async def set_mode(self, mode: str, reason: str = "",
                        by: str = "cortex"):
        """Change le mode du serveur."""
        old_mode = self.state.mode
        self.state.mode = mode

        if mode == "lockdown":
            self.state.lockdown_reason = reason
            self.state.lockdown_by = by
            self.state.lockdown_at = datetime.now(timezone.utc).isoformat()
        elif mode == "shield":
            self.state.shield_mode = True
        elif mode == "normal":
            self.state.shield_mode = False
            self.state.lockdown_reason = ""

        # Persister dans Redis
        if self.redis:
            try:
                state_data = json.dumps({
                    "mode": self.state.mode,
                    "lockdown_reason": self.state.lockdown_reason,
                    "lockdown_by": self.state.lockdown_by,
                    "lockdown_at": self.state.lockdown_at,
                    "shield_mode": self.state.shield_mode,
                })
                if hasattr(self.redis, 'set'):
                    await self.redis.set("cortex:state", state_data)
            except Exception as e:
                logger.error(f"Erreur sauvegarde state: {e}")

        logger.warning(f"Mode change: {old_mode} → {mode} "
                        f"(par {by}, raison: {reason})")

        # Brief le changement
        severity = (Severity.EMERGENCY if mode == "lockdown"
                    else Severity.CRITICAL if mode == "shield"
                    else Severity.INFO)
        await self.briefing.dispatch(Signal(
            source=SignalSource.SYSTEM,
            severity=severity,
            category="system",
            title=f"Mode change: {mode}",
            message=f"Mode {old_mode} → {mode}. Raison: {reason}. Par: {by}.",
        ))

    def is_request_allowed(self, ip: str, path: str) -> tuple[bool, str]:
        """
        Verifie si une requete est autorisee.
        Appele par le middleware FastAPI.
        Retourne (autorisee, raison).
        """
        # Paths toujours autorises (health, SMS, cortex API, telegram webhook)
        always_allowed = ("/health", "/api/webhook/sms", "/api/cortex/status",
                          "/api/cortex/telegram/webhook")

        # Mode lockdown → tout bloque sauf health et emergency
        if self.state.mode == "lockdown":
            if path in always_allowed:
                return True, ""
            return False, f"Serveur en lockdown: {self.state.lockdown_reason}"

        # Mode maintenance → page maintenance sauf admin
        if self.state.mode == "maintenance":
            if path in always_allowed or path.startswith("/api/cortex"):
                return True, ""
            if path.startswith("/api/admin") or path.startswith("/admin"):
                return True, ""
            return False, f"Maintenance en cours: {self.state.lockdown_reason}"

        # Mode shield → whitelist only
        if self.state.mode == "shield":
            if path in always_allowed:
                return True, ""
            if ip in self.state.whitelist_ips:
                return True, ""
            return False, "Mode bouclier actif. IP non autorisee."

        # Mode normal → check ban IP
        if self.vigil.is_banned(ip):
            return False, "IP bannie."

        return True, ""

    # ──────────────────────────────────────────
    # ANALYSE IA
    # ──────────────────────────────────────────

    async def _ai_analysis(self) -> list[Signal]:
        """Analyse IA periodique des menaces et de la sante."""
        signals = []

        # Construire le prompt Vigil
        prompt = self.vigil.build_ai_analysis_prompt()
        if not prompt:
            return signals

        # Appeler GPT-4o-mini
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            return signals

        try:
            async with httpx.AsyncClient(timeout=15.0) as http:
                resp = await http.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.config.ai_model,
                        "messages": [
                            {"role": "system",
                             "content": "Tu es Vigil, l'agent securite IA de Luna."},
                            {"role": "user", "content": prompt},
                        ],
                        "max_tokens": 300,
                        "temperature": 0.3,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    analysis = data["choices"][0]["message"]["content"]
                    logger.info(f"Analyse IA Vigil: {analysis[:100]}...")

                    # Suivi des couts OpenAI
                    usage = data.get("usage", {})
                    await self.cost_tracker.track_openai(
                        tokens_in=usage.get("prompt_tokens", 0),
                        tokens_out=usage.get("completion_tokens", 0),
                    )

                    # Si l'IA detecte quelque chose de critique
                    if any(w in analysis.lower() for w in
                           ["coordonne", "grave", "urgente", "immediate",
                            "critique", "attaque"]):
                        signals.append(Signal(
                            source=SignalSource.VIGIL,
                            severity=Severity.WARNING,
                            category="security",
                            title="Analyse IA Vigil",
                            message=analysis[:500],
                        ))
                    else:
                        # Log pour le digest
                        if self.redis and hasattr(self.redis, 'set'):
                            await self.redis.set(
                                "cortex:last_ai_analysis",
                                json.dumps({
                                    "time": time.time(),
                                    "analysis": analysis,
                                }),
                            )
        except Exception as e:
            logger.debug(f"Analyse IA indisponible: {e}")

        return signals

    # ──────────────────────────────────────────
    # DIGESTS PROGRAMMES
    # ──────────────────────────────────────────

    async def _send_scheduled_digest(self):
        """Envoie le digest programme."""
        try:
            # Collecte des donnees
            health = await self._collect_health()
            threats = self.vigil.get_threat_report()
            business = await self._collect_business()

            await self.briefing.send_digest(
                health=health,
                threats={
                    "total_threats_24h": threats.total_threats_24h,
                    "banned_ips": threats.banned_ips,
                    "blocked_requests_24h": threats.blocked_requests_24h,
                    "auto_actions_taken": threats.auto_actions_taken,
                },
                business=business,
            )
            logger.info("Digest envoye")
        except Exception as e:
            logger.error(f"Erreur digest: {e}")

    async def force_digest(self):
        """Force l'envoi d'un digest (commande SMS)."""
        await self._send_scheduled_digest()

    async def _send_weekly_report(self):
        """Envoie le rapport hebdomadaire."""
        try:
            week_data = await self._collect_weekly_data()
            report = await self.briefing.generate_weekly(week_data)

            # Telegram exploitant
            if self.config.exploitant_telegram_chat_id:
                await self.briefing.send_telegram(
                    self.config.exploitant_telegram_chat_id,
                    f"<pre>{report}</pre>")
            # Telegram fondateur
            if self.config.founder_telegram_chat_id:
                header = (f"[SERVEUR: "
                          f"{self.config.exploitant_phone or 'inconnu'}]\n")
                await self.briefing.send_telegram(
                    self.config.founder_telegram_chat_id,
                    f"<pre>{header}{report}</pre>")

            logger.info("Rapport hebdo envoye")
        except Exception as e:
            logger.error(f"Erreur rapport hebdo: {e}")

    # ──────────────────────────────────────────
    # COLLECTE DE DONNEES
    # ──────────────────────────────────────────

    async def _collect_health(self) -> dict:
        """Collecte les metriques de sante."""
        health = {
            "redis_memory_pct": 0,
            "cpu_usage_pct": 0,
            "disk_usage_pct": 0,
            "uptime_seconds": time.time() - self._start_time,
            "luna_mode": self.state.mode,
        }

        try:
            import psutil
            health["cpu_usage_pct"] = psutil.cpu_percent(interval=0.1)
            health["disk_usage_pct"] = psutil.disk_usage("/").percent
            health["redis_memory_pct"] = psutil.virtual_memory().percent
        except ImportError:
            pass

        if self.redis:
            try:
                if hasattr(self.redis, 'info'):
                    info = await self.redis.info("memory")
                    used = info.get("used_memory", 0)
                    max_mem = info.get("maxmemory", 0)
                    if max_mem > 0:
                        health["redis_memory_pct"] = (used / max_mem) * 100
            except Exception:
                pass

        return health

    async def _collect_business(self) -> dict:
        """Collecte les metriques business."""
        business = {
            "active_clients": 0,
            "total_clients": 0,
            "mrr": 0,
            "quota_critical": 0,
            "inactive_clients": 0,
        }

        if not self.redis:
            return business

        try:
            if hasattr(self.redis, 'keys'):
                keys = await self.redis.keys("luna:*:profile")
                # Filtrer les profils de contacts (luna:X:contact:+phone:profile)
                client_keys = [k for k in keys if b":contact:" not in (k if isinstance(k, bytes) else k.encode())]
                business["total_clients"] = len(client_keys)
                business["active_clients"] = len(client_keys)  # Approximation
        except Exception:
            pass

        # Recuperer les couts du mois en cours
        if self.cost_tracker:
            try:
                month_costs = await self.cost_tracker.get_month_costs()
                business["sms_count"] = month_costs.get("sms_count", 0)
                business["sms_cost"] = month_costs.get("sms_cost", 0)
                business["openai_cost"] = month_costs.get("openai_cost", 0)
                business["voice_minutes"] = month_costs.get("voice_minutes", 0)
                business["voice_cost"] = month_costs.get("voice_cost", 0)
                business["tavus_minutes"] = month_costs.get("tavus_minutes", 0)
                business["tavus_cost"] = month_costs.get("tavus_cost", 0)
                # Couts infrastructure (env vars configures par l'admin)
                import os
                cloud_run_cost = float(os.getenv("CLOUD_RUN_MONTHLY_COST", "0"))
                redis_cost = float(os.getenv("REDIS_MONTHLY_COST", "0"))
                business["cloud_run_cost"] = cloud_run_cost
                business["redis_cost"] = redis_cost

                api_total = month_costs.get("total_cost", 0)
                business["total_cost"] = api_total + cloud_run_cost + redis_cost

                # Couts par tenant
                tenant_costs = await self.cost_tracker.get_month_costs_per_tenant()
                business["tenant_costs"] = tenant_costs
            except Exception as e:
                logger.debug(f"Cost collection: {e}")

        return business

    async def _collect_weekly_data(self) -> dict:
        """Collecte les donnees pour le rapport hebdo."""
        now = datetime.now()
        return {
            "week_start": (now.strftime("%d/%m")),
            "week_end": now.strftime("%d/%m/%Y"),
            "new_clients": 0,
            "churned": 0,
            "revenue_week": 0,
            "mrr": 0,
            "uptime_pct": 99.9,
            "total_requests": 0,
            "avg_latency_ms": 0,
            "security_incidents": self.vigil.get_threat_report().total_threats_24h,
            "auto_resolved": len(self.vigil._actions_taken),
            "most_active": "N/A",
            "churn_risk": "aucun",
            "quota_critical": 0,
            "cortex_actions": self.vigil._actions_taken[-10:],
        }

    # ──────────────────────────────────────────
    # STATUS
    # ──────────────────────────────────────────

    def get_cortex_status(self) -> dict:
        """Status complet du Cortex."""
        uptime = time.time() - self._start_time
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)

        last_ai = "jamais"
        if self._last_ai_analysis > 0:
            ago = int(time.time() - self._last_ai_analysis)
            last_ai = f"il y a {ago // 60}min"

        return {
            "mode": self.state.mode,
            "uptime": f"{hours}h{minutes:02d}m",
            "loop_count": self._loop_count,
            "signals_processed": self._signals_processed,
            "actions_executed": self._actions_executed,
            "vigil_active": True,
            "doctor_active": self.doctor is not None,
            "accountant_active": self.accountant is not None,
            "last_ai": last_ai,
            "banned_ips": len(self.vigil._banned_ips),
            "threats_24h": self.vigil.get_threat_report().total_threats_24h,
        }

    # ──────────────────────────────────────────
    # INTERFACE POUR LE MIDDLEWARE
    # ──────────────────────────────────────────

    def analyze_request(self, ip: str, method: str, path: str,
                        query: str = "", body: str = "",
                        headers: Optional[dict] = None) -> list[Signal]:
        """
        Point d'entree pour le middleware FastAPI.
        Analyse une requete et retourne les signaux.
        """
        return self.vigil.analyze_request(
            ip, method, path, query, body, headers)

    async def process_signals(self, signals: list[Signal]):
        """Traite une liste de signaux (appele par le middleware)."""
        for signal in signals:
            await self._handle_signal(signal)
            self._signals_processed += 1

    # ──────────────────────────────────────────
    # ERREURS
    # ──────────────────────────────────────────

    async def _log_error(self, error: str):
        """Log une erreur dans Redis."""
        if not self.redis:
            return
        try:
            data = json.dumps({
                "timestamp": time.time(),
                "message": error[:500],
            })
            if hasattr(self.redis, 'lpush'):
                await self.redis.lpush("cortex:errors", data)
                await self.redis.ltrim("cortex:errors", 0, 99)
        except Exception:
            pass
