"""
VIGIL — Agent Securite IA du Cortex.

Surveille en permanence:
- Tentatives de brute force (login, API)
- Injections SQL/XSS/Command
- Scans et honeypot hits
- DDoS / flood
- Tampering code (modification fichiers critiques)
- Bypass PV de recette
- Anomalies geographiques
- Fuites de cles API

Reagit automatiquement:
- Ban IP (progressif: 1h → 24h → 7j)
- Mode bouclier (whitelist only)
- Lockdown serveur
- Alertes SMS/Telegram

Analyse IA toutes les 5 min:
- GPT-4o-mini analyse les patterns
- Genere un rapport humain lisible
- Decide si escalade necessaire
"""

import hashlib
import json
import logging
import os
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import CortexConfig
from .signals import (
    ActionType, CortexAction, Severity, Signal,
    SignalSource, ThreatReport, ThreatType,
)

logger = logging.getLogger("cortex.vigil")

# ──────────────────────────────────────────
# PATTERNS DE DETECTION
# ──────────────────────────────────────────

SQL_INJECTION_PATTERNS = [
    r"(\b(union|select|insert|update|delete|drop|alter|create)\b.*\b(from|into|table|where)\b)",
    r"('|\")?\s*(or|and)\s+\d+\s*=\s*\d+",
    r"(--|/\*)\s*;\s*$",  # SQL comment avant fin, pas # seul (fragment URL)
    r"\bexec\s*\(",
    r"\bchar\s*\(\d+\)",
    r";\s*(drop|delete|update|insert)\b",
    r"\b0x[0-9a-fA-F]{8,}",  # Hex long seulement (>=8 chars), pas les courts
    r"\bwaitfor\s+delay\b",
    r"\bbenchmark\s*\(",
    r"\bsleep\s*\(\d+\)",
]

XSS_PATTERNS = [
    r"<\s*script\b",
    r"\bon(load|error|click|mouseover|mouseout|focus|blur|submit|change|input|keydown|keyup|keypress|mousedown|mouseup|contextmenu|dblclick|drag|drop|paste|cut|copy|unload|beforeunload|abort|resize|scroll)\s*=",
    r"javascript\s*:",
    r"<\s*img\b[^>]+onerror",
    r"<\s*svg\b[^>]+onload",
    r"<\s*iframe\b",
    r"document\.cookie",
    r"document\.location",
    r"eval\s*\(",
    r"alert\s*\(\s*['\"]",  # alert('...') ou alert("..."), pas alert() seul
]

PATH_TRAVERSAL_PATTERNS = [
    r"\.\./",
    r"\.\.\x5c",
    r"%2e%2e",
    r"%252e%252e",
    r"/etc/(passwd|shadow|hosts)",
    r"/proc/self",
    r"\\windows\\",
    r"\\system32\\",
]

COMMAND_INJECTION_PATTERNS = [
    r";\s*(ls|cat|wget|curl|nc|bash|sh|python|perl|ruby)\b",
    r"\|\s*(ls|cat|wget|curl|nc|bash|sh)\b",
    r"`[^`]+`",
    r"\$\([^)]+\)",
    r"\b(rm|chmod|chown|kill|pkill)\s+-",
    r"&&\s*(wget|curl|nc|bash)",
    r"\bnohup\b",
    r"\b(reverse|bind)\s*shell\b",
]

API_KEY_PATTERNS = [
    r"sk-[a-zA-Z0-9]{20,}",  # OpenAI
    r"AC[a-f0-9]{32}",  # Twilio SID
    r"sk_live_[a-zA-Z0-9]+",  # Stripe
    r"sk_test_[a-zA-Z0-9]+",  # Stripe test
    r"Bearer\s+[a-zA-Z0-9._-]{30,}",  # JWT tokens
]

# Fichiers critiques a surveiller
CRITICAL_FILES = [
    "luna_web.py",
    "core/license/heartbeat.py",
    "core/license/fingerprint.py",
    "core/license/integrity.py",
    "core/safety/guardian.py",
    "core/memory/redis_client.py",
    "core/memory/memory_manager.py",
    "core/actions/quota_guard.py",
    "core/cortex/vigil.py",
    "core/cortex/brain.py",
    "core/cortex/emergency.py",
]

# Honeypot paths — jamais accedes par un utilisateur legitime
HONEYPOT_PATHS = [
    "/wp-admin", "/wp-login", "/phpmyadmin", "/phpMyAdmin",
    "/.env", "/.git", "/.aws", "/.docker",
    "/admin-debug", "/debug", "/console",
    "/actuator", "/server-status", "/server-info",
    "/elmah.axd", "/solr", "/jenkins",
    "/api/v2/internal", "/api/config", "/api/debug",
    "/cgi-bin", "/manager/html",
]


class VigilAgent:
    """Agent de securite autonome."""

    # Nombre d'avertissements avant ban automatique
    WARNINGS_BEFORE_BAN = 3

    def __init__(self, config: CortexConfig, redis_client=None):
        self.config = config
        self.redis = redis_client
        self._base_path = Path(os.getenv("LUNA_BASE_PATH",
                                          str(Path(__file__).parent.parent.parent)))

        # Compteurs en memoire (rapide, pas de Redis pour chaque requete)
        self._request_counts: dict[str, list[float]] = defaultdict(list)
        self._failed_auths: dict[str, list[float]] = defaultdict(list)
        self._threat_scores: dict[str, float] = defaultdict(float)
        self._threat_signals: dict[str, list[dict]] = defaultdict(list)
        self._banned_ips: dict[str, dict] = {}  # ip -> {until, reason, level}
        self._file_hashes: dict[str, str] = {}  # path -> sha256
        self._global_request_count: list[float] = []
        self._last_integrity_check: float = 0
        self._actions_taken: list[str] = []

        # Systeme d'avertissements progressifs (avant ban)
        # ip -> [{"time": t, "reason": str, "score": float, "threat_types": [...]}]
        self._warnings: dict[str, list[dict]] = defaultdict(list)
        # Historique complet des avertissements (pour consultation admin)
        # [{"ip": str, "time": t, "reason": str, "warning_number": int, ...}]
        self._warnings_history: list[dict] = []

        # Init file hashes
        self._compute_file_hashes()

    # ──────────────────────────────────────────
    # FILE INTEGRITY
    # ──────────────────────────────────────────

    def _compute_file_hashes(self):
        """Calcule les SHA-256 des fichiers critiques."""
        for rel_path in CRITICAL_FILES:
            full_path = self._base_path / rel_path
            if full_path.exists():
                try:
                    content = full_path.read_bytes()
                    h = hashlib.sha256(content).hexdigest()
                    self._file_hashes[rel_path] = h
                except Exception:
                    pass
        logger.info(f"Vigil: {len(self._file_hashes)} fichiers critiques surveilles")

    def check_file_integrity(self) -> list[Signal]:
        """Verifie que les fichiers critiques n'ont pas ete modifies."""
        signals = []
        for rel_path, expected_hash in self._file_hashes.items():
            full_path = self._base_path / rel_path
            if not full_path.exists():
                signals.append(Signal(
                    source=SignalSource.VIGIL,
                    severity=Severity.EMERGENCY,
                    category="security",
                    title=f"Fichier critique SUPPRIME: {rel_path}",
                    message=(f"Le fichier {rel_path} a ete supprime. "
                             f"Possible tentative de tampering."),
                    threat_type=ThreatType.CODE_TAMPERING,
                ))
                continue
            try:
                content = full_path.read_bytes()
                current_hash = hashlib.sha256(content).hexdigest()
                if current_hash != expected_hash:
                    signals.append(Signal(
                        source=SignalSource.VIGIL,
                        severity=Severity.EMERGENCY,
                        category="security",
                        title=f"Fichier critique MODIFIE: {rel_path}",
                        message=(
                            f"Le fichier {rel_path} a ete modifie depuis "
                            f"le demarrage. Hash attendu: {expected_hash[:16]}... "
                            f"Hash actuel: {current_hash[:16]}... "
                            f"Possible injection de code."
                        ),
                        threat_type=ThreatType.CODE_TAMPERING,
                    ))
            except Exception as e:
                signals.append(Signal(
                    source=SignalSource.VIGIL,
                    severity=Severity.CRITICAL,
                    category="security",
                    title=f"Erreur lecture fichier: {rel_path}",
                    message=str(e),
                    threat_type=ThreatType.CODE_TAMPERING,
                ))
        return signals

    # ──────────────────────────────────────────
    # ANALYSE DE REQUETE (appele par le middleware)
    # ──────────────────────────────────────────

    def analyze_request(self, ip: str, method: str, path: str,
                        query: str = "", body: str = "",
                        headers: Optional[dict] = None,
                        whitelist_ips: Optional[set] = None) -> list[Signal]:
        """
        Analyse une requete entrante et retourne les signaux de menace.
        Appele par le middleware FastAPI a chaque requete.
        """
        # Skip analysis for whitelisted IPs
        if whitelist_ips and ip in whitelist_ips:
            return []

        signals = []
        now = time.time()
        headers = headers or {}

        # 0. IP deja bannie?
        if self.is_banned(ip):
            return [Signal(
                source=SignalSource.VIGIL,
                severity=Severity.INFO,
                category="security",
                title="Requete IP bannie bloquee",
                message=f"IP {ip} bannie, requete rejetee",
                ip=ip,
            )]

        # 1. Rate tracking global (DDoS detection)
        self._global_request_count.append(now)
        self._global_request_count = [
            t for t in self._global_request_count if t > now - 1]
        if len(self._global_request_count) > self.config.ddos_threshold:
            signals.append(Signal(
                source=SignalSource.VIGIL,
                severity=Severity.EMERGENCY,
                category="security",
                title="DDoS detecte!",
                message=(
                    f"{len(self._global_request_count)} req/s "
                    f"(seuil: {self.config.ddos_threshold}). "
                    f"Activation mode bouclier."
                ),
                threat_type=ThreatType.DDOS,
                ip=ip,
            ))

        # 2. Rate tracking par IP
        self._request_counts[ip].append(now)
        self._request_counts[ip] = [
            t for t in self._request_counts[ip] if t > now - 60]
        req_per_min = len(self._request_counts[ip])

        if req_per_min > 200:
            signals.append(Signal(
                source=SignalSource.VIGIL,
                severity=Severity.CRITICAL,
                category="security",
                title=f"Flood IP: {req_per_min} req/min",
                message=(f"IP {ip} envoie {req_per_min} requetes/min. "
                         f"Possible bot ou attaque."),
                threat_type=ThreatType.DDOS,
                ip=ip,
            ))

        # 3. Honeypot check
        for hp in HONEYPOT_PATHS:
            if path.startswith(hp):
                signals.append(Signal(
                    source=SignalSource.VIGIL,
                    severity=Severity.WARNING,
                    category="security",
                    title=f"Honeypot hit: {path}",
                    message=(f"IP {ip} a accede au honeypot {path}. "
                             f"Scanner ou attaquant."),
                    threat_type=ThreatType.HONEYPOT_HIT,
                    ip=ip,
                ))
                self._boost_threat(ip, ThreatType.HONEYPOT_HIT, 25)
                break

        # 4. Injection checks (query + body + path)
        # Skip pattern checks for upload endpoints (documents legits contiennent
        # du texte qui peut matcher des patterns de securite)
        _UPLOAD_PATHS = ("/api/form-filler/analyze", "/api/form-filler/fill",
                         "/api/secretary/scan", "/api/chat",
                         "/api/perception/analyze")
        if any(path.startswith(p) for p in _UPLOAD_PATHS):
            return signals

        payload = f"{path} {query} {body}"

        for pattern in SQL_INJECTION_PATTERNS:
            if re.search(pattern, payload, re.IGNORECASE):
                signals.append(Signal(
                    source=SignalSource.VIGIL,
                    severity=Severity.CRITICAL,
                    category="security",
                    title="Injection SQL detectee",
                    message=(f"IP {ip} tente une injection SQL. "
                             f"Path: {path}"),
                    threat_type=ThreatType.SQL_INJECTION,
                    ip=ip,
                    metadata={"pattern": pattern, "path": path},
                ))
                self._boost_threat(ip, ThreatType.SQL_INJECTION, 40)
                break

        for pattern in XSS_PATTERNS:
            if re.search(pattern, payload, re.IGNORECASE):
                signals.append(Signal(
                    source=SignalSource.VIGIL,
                    severity=Severity.CRITICAL,
                    category="security",
                    title="Tentative XSS detectee",
                    message=f"IP {ip} tente du XSS. Path: {path}",
                    threat_type=ThreatType.XSS,
                    ip=ip,
                    metadata={"path": path},
                ))
                self._boost_threat(ip, ThreatType.XSS, 35)
                break

        for pattern in PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, payload, re.IGNORECASE):
                signals.append(Signal(
                    source=SignalSource.VIGIL,
                    severity=Severity.CRITICAL,
                    category="security",
                    title="Path traversal detecte",
                    message=f"IP {ip} tente un path traversal. Path: {path}",
                    threat_type=ThreatType.PATH_TRAVERSAL,
                    ip=ip,
                ))
                self._boost_threat(ip, ThreatType.PATH_TRAVERSAL, 40)
                break

        for pattern in COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, payload, re.IGNORECASE):
                signals.append(Signal(
                    source=SignalSource.VIGIL,
                    severity=Severity.EMERGENCY,
                    category="security",
                    title="Injection de commande detectee!",
                    message=(f"IP {ip} tente une injection de commande. "
                             f"Path: {path}. TRES DANGEREUX."),
                    threat_type=ThreatType.COMMAND_INJECTION,
                    ip=ip,
                ))
                self._boost_threat(ip, ThreatType.COMMAND_INJECTION, 50)
                break

        # 5. API key leak detection (dans les logs/requetes)
        for pattern in API_KEY_PATTERNS:
            if re.search(pattern, payload):
                signals.append(Signal(
                    source=SignalSource.VIGIL,
                    severity=Severity.EMERGENCY,
                    category="security",
                    title="Cle API detectee dans requete!",
                    message=(f"Une cle API a ete detectee dans une requete "
                             f"de {ip}. Possible fuite de credentials."),
                    threat_type=ThreatType.API_KEY_LEAK,
                    ip=ip,
                ))
                break

        # 6. PV bypass attempt
        if any(p in path for p in ["/pv_lock", "/data/pv_lock",
                                    "pv_lock.json", "factory_reset"]):
            signals.append(Signal(
                source=SignalSource.VIGIL,
                severity=Severity.EMERGENCY,
                category="security",
                title="Tentative bypass PV detectee!",
                message=(f"IP {ip} tente d'acceder aux fichiers PV. "
                         f"Path: {path}"),
                threat_type=ThreatType.PV_BYPASS,
                ip=ip,
            ))
            self._boost_threat(ip, ThreatType.PV_BYPASS, 60)

        # 7. Avertissement progressif basee sur le threat score
        # (avant c'etait un ban direct — maintenant on avertit d'abord)
        score = self._threat_scores.get(ip, 0)
        if score >= self.config.threat_score_ban:
            warning_signal = self._issue_warning(ip, score)
            if warning_signal:
                signals.append(warning_signal)

        return signals

    # ──────────────────────────────────────────
    # BRUTE FORCE AUTH
    # ──────────────────────────────────────────

    def record_failed_auth(self, ip: str, email: str = "") -> list[Signal]:
        """Enregistre un echec d'authentification."""
        signals = []
        now = time.time()
        self._failed_auths[ip].append(now)
        self._failed_auths[ip] = [
            t for t in self._failed_auths[ip]
            if t > now - self.config.brute_force_window
        ]
        count = len(self._failed_auths[ip])

        if count >= self.config.brute_force_threshold:
            signals.append(Signal(
                source=SignalSource.VIGIL,
                severity=Severity.CRITICAL,
                category="security",
                title=f"Brute force: {count} echecs en {self.config.brute_force_window}s",
                message=(f"IP {ip} a echoue {count} authentifications "
                         f"en {self.config.brute_force_window}s. "
                         f"Dernier email tente: {email[:3]}..."),
                threat_type=ThreatType.BRUTE_FORCE,
                ip=ip,
                metadata={"attempts": count, "email_prefix": email[:3]},
            ))
            self._boost_threat(ip, ThreatType.BRUTE_FORCE, 30)

            # Avertissement progressif si > 2x le seuil
            if count >= self.config.brute_force_threshold * 2:
                reason = f"Brute force: {count} echecs login"
                warn_signal = self._issue_warning(
                    ip, self._threat_scores[ip], reason)
                if warn_signal:
                    signals.append(warn_signal)

        return signals

    # ──────────────────────────────────────────
    # THREAT SCORING & AUTO-BAN
    # ──────────────────────────────────────────

    def _boost_threat(self, ip: str, threat_type: ThreatType, points: float):
        """Augmente le score de menace d'une IP."""
        self._threat_scores[ip] = min(100, self._threat_scores.get(ip, 0) + points)
        self._threat_signals[ip].append({
            "type": threat_type.value,
            "points": points,
            "time": time.time(),
        })
        # Garder les 50 derniers signaux par IP
        self._threat_signals[ip] = self._threat_signals[ip][-50:]

    def _issue_warning(self, ip: str, score: float, reason: str = "") -> Signal:
        """
        Emettre un avertissement pour une IP.
        Apres WARNINGS_BEFORE_BAN avertissements, on passe au ban.
        Chaque avertissement est enregistre et historise.
        """
        now = time.time()

        # Nettoyer les vieux avertissements (plus de 24h) pour cette IP
        self._warnings[ip] = [
            w for w in self._warnings[ip]
            if now - w["time"] < 86400
        ]

        # Compter les avertissements actifs (dernières 24h)
        warning_count = len(self._warnings[ip]) + 1  # +1 pour celui-ci
        threat_types = list(set(
            s["type"] for s in self._threat_signals.get(ip, [])
        ))

        if not reason:
            reason = f"Score menace {score:.0f}/100 ({self._threat_summary(ip)})"

        # Enregistrer l'avertissement
        warning_entry = {
            "time": now,
            "reason": reason,
            "score": score,
            "threat_types": threat_types,
            "warning_number": warning_count,
        }
        self._warnings[ip].append(warning_entry)

        # Historique global (garder les 200 derniers)
        history_entry = {
            "ip": ip,
            **warning_entry,
            "time_str": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        }
        self._warnings_history.append(history_entry)
        if len(self._warnings_history) > 200:
            self._warnings_history = self._warnings_history[-200:]

        # Persister dans Redis (async best-effort)
        self._persist_warning_to_redis(ip, history_entry)

        # Si on a atteint le seuil → ban
        if warning_count >= self.WARNINGS_BEFORE_BAN:
            return self._escalate_to_ban(ip, score, warning_count)

        # Sinon → avertissement simple
        remaining = self.WARNINGS_BEFORE_BAN - warning_count
        action_desc = (f"Avertissement {warning_count}/{self.WARNINGS_BEFORE_BAN} "
                       f"pour {ip} — score {score:.0f}")
        self._actions_taken.append(action_desc)

        return Signal(
            source=SignalSource.VIGIL,
            severity=Severity.WARNING,
            category="security",
            title=f"Avertissement {warning_count}/{self.WARNINGS_BEFORE_BAN} — IP {ip}",
            message=(
                f"IP {ip} — Avertissement {warning_count}/{self.WARNINGS_BEFORE_BAN}. "
                f"Score: {score:.0f}/100. Raison: {reason}. "
                f"Encore {remaining} avertissement(s) avant blocage."
            ),
            threat_type=ThreatType.UNKNOWN,
            ip=ip,
            metadata={
                "warning_number": warning_count,
                "warnings_before_ban": self.WARNINGS_BEFORE_BAN,
                "remaining": remaining,
                "threat_types": threat_types,
            },
        )

    def _escalate_to_ban(self, ip: str, score: float,
                         warning_count: int) -> Signal:
        """Ban apres epuisement des avertissements."""
        if ip in self._banned_ips:
            return None

        # Escalade progressive basee sur le nombre de signaux
        signals_count = len(self._threat_signals.get(ip, []))
        if signals_count > 20:
            duration = self.config.ban_duration_permanent
            level = "permanent"
        elif signals_count > 10:
            duration = self.config.ban_duration_hard
            level = "hard"
        else:
            duration = self.config.ban_duration_soft
            level = "soft"

        self._banned_ips[ip] = {
            "until": time.time() + duration,
            "reason": (f"Score {score:.0f}/100 apres "
                       f"{warning_count} avertissements ignores"),
            "level": level,
            "score": score,
            "warnings_count": warning_count,
        }

        # Persister le ban dans Redis
        self._persist_ban_to_redis(ip, self._banned_ips[ip])

        duration_str = self._format_duration(duration)
        action_desc = (f"Ban {ip} ({level}, {duration_str}) — "
                       f"apres {warning_count} avertissements")
        self._actions_taken.append(action_desc)

        return Signal(
            source=SignalSource.VIGIL,
            severity=Severity.CRITICAL,
            category="security",
            title=f"IP {ip} bannie apres {warning_count} avertissements",
            message=(
                f"IP {ip} bannie pour {duration_str} ({level}). "
                f"Score: {score:.0f}/100. "
                f"{warning_count} avertissements ignores. "
                f"Types: {self._threat_summary(ip)}"
            ),
            threat_type=ThreatType.UNKNOWN,
            ip=ip,
            metadata={
                "ban_level": level,
                "ban_duration": duration,
                "warnings_count": warning_count,
            },
        )

    def _persist_warning_to_redis(self, ip: str, entry: dict):
        """Persiste un avertissement dans Redis (best-effort, non-bloquant)."""
        if not self.redis:
            return
        try:
            import asyncio
            data = json.dumps(entry, default=str)
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._async_persist_warning(ip, data))
        except Exception:
            pass

    async def _async_persist_warning(self, ip: str, data: str):
        """Sauvegarde async dans Redis."""
        try:
            # Liste des avertissements par IP (max 20 par IP)
            key = f"cortex:warnings:{ip}"
            await self.redis.rpush(key, data)
            await self.redis.ltrim(key, -20, -1)
            await self.redis.expire(key, 86400 * 7)  # TTL 7 jours
            # Historique global (max 500)
            await self.redis.rpush("cortex:warnings:history", data)
            await self.redis.ltrim("cortex:warnings:history", -500, -1)
        except Exception:
            pass

    def _persist_ban_to_redis(self, ip: str, ban_data: dict):
        """Persiste un ban dans Redis (best-effort)."""
        if not self.redis:
            return
        try:
            import asyncio
            data = json.dumps(ban_data, default=str)
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._async_persist_ban(ip, data))
        except Exception:
            pass

    async def _async_persist_ban(self, ip: str, data: str):
        """Sauvegarde async du ban dans Redis."""
        try:
            ttl = int(json.loads(data).get("until", 0) - time.time())
            if ttl > 0:
                await self.redis.setex(f"cortex:ban:{ip}", ttl, data)
        except Exception:
            pass

    async def restore_from_redis(self):
        """Restaure les bans et avertissements depuis Redis au demarrage."""
        if not self.redis:
            return
        try:
            # Restaurer les bans actifs
            cursor = b"0"
            while True:
                cursor, keys = await self.redis.scan(
                    cursor, match="cortex:ban:*", count=100)
                for key in keys:
                    try:
                        data = await self.redis.get(key)
                        if data:
                            ban = json.loads(data)
                            ip = key.decode().replace("cortex:ban:", "") if isinstance(key, bytes) else key.replace("cortex:ban:", "")
                            if ban.get("until", 0) > time.time():
                                self._banned_ips[ip] = ban
                    except Exception:
                        pass
                if cursor == b"0" or cursor == 0:
                    break

            # Restaurer l'historique des avertissements
            raw_history = await self.redis.lrange(
                "cortex:warnings:history", 0, -1)
            if raw_history:
                for r in raw_history:
                    try:
                        entry = json.loads(r)
                        self._warnings_history.append(entry)
                        # Reconstituer _warnings par IP (dernières 24h)
                        ip = entry.get("ip", "")
                        if ip and time.time() - entry.get("time", 0) < 86400:
                            self._warnings[ip].append(entry)
                    except Exception:
                        pass

            if self._banned_ips:
                logger.info(f"VIGIL restaure {len(self._banned_ips)} ban(s) depuis Redis")
            if self._warnings_history:
                logger.info(f"VIGIL restaure {len(self._warnings_history)} avertissement(s) depuis Redis")
        except Exception as e:
            logger.warning(f"VIGIL restore from Redis failed: {e}")

    def get_warnings(self, ip: str = None) -> list[dict]:
        """Retourne les avertissements. Si ip fourni, filtre par IP."""
        if ip:
            return list(self._warnings.get(ip, []))
        return list(self._warnings_history)

    def get_ip_status(self, ip: str) -> dict:
        """Status complet d'une IP : score, avertissements, ban."""
        warnings = self._warnings.get(ip, [])
        active_warnings = [
            w for w in warnings
            if time.time() - w["time"] < 86400
        ]
        banned = self.is_banned(ip)
        ban_info = self._banned_ips.get(ip, {}) if banned else {}

        return {
            "ip": ip,
            "threat_score": self._threat_scores.get(ip, 0),
            "warnings_active": len(active_warnings),
            "warnings_before_ban": self.WARNINGS_BEFORE_BAN,
            "warnings_remaining": max(0, self.WARNINGS_BEFORE_BAN - len(active_warnings)),
            "warnings_detail": active_warnings,
            "banned": banned,
            "ban_info": {
                "until": ban_info.get("until"),
                "reason": ban_info.get("reason"),
                "level": ban_info.get("level"),
            } if banned else None,
            "signals_count": len(self._threat_signals.get(ip, [])),
        }

    def is_banned(self, ip: str) -> bool:
        """Verifie si une IP est bannie."""
        if ip not in self._banned_ips:
            return False
        ban = self._banned_ips[ip]
        if time.time() > ban["until"]:
            del self._banned_ips[ip]
            return False
        return True

    def manual_ban(self, ip: str, duration: int = 86400,
                   reason: str = "Manual", by: str = "admin") -> Signal:
        """Ban manuelle (depuis commande SMS ou admin)."""
        self._banned_ips[ip] = {
            "until": time.time() + duration,
            "reason": reason,
            "level": "manual",
            "score": 100,
        }
        desc = f"Ban manuelle {ip} par {by} ({self._format_duration(duration)})"
        self._actions_taken.append(desc)
        return Signal(
            source=SignalSource.VIGIL,
            severity=Severity.INFO,
            category="security",
            title=f"IP {ip} bannie manuellement",
            message=f"Par {by}. Raison: {reason}. Duree: {self._format_duration(duration)}",
            ip=ip,
        )

    def manual_unban(self, ip: str, by: str = "admin") -> bool:
        """Deban manuelle."""
        if ip in self._banned_ips:
            del self._banned_ips[ip]
            self._actions_taken.append(f"Unban {ip} par {by}")
            return True
        return False

    # ──────────────────────────────────────────
    # PV LOCK MONITORING
    # ──────────────────────────────────────────

    def check_pv_integrity(self) -> list[Signal]:
        """Verifie l'integrite du pv_lock.json."""
        signals = []
        pv_path = self._base_path / "data" / "pv_lock.json"
        if not pv_path.exists():
            return signals  # Pas de PV = pas de check

        try:
            content = json.loads(pv_path.read_text())
            if "hmac" not in content:
                signals.append(Signal(
                    source=SignalSource.VIGIL,
                    severity=Severity.EMERGENCY,
                    category="security",
                    title="pv_lock.json corrompu!",
                    message="Le fichier pv_lock.json ne contient pas de HMAC.",
                    threat_type=ThreatType.PV_BYPASS,
                ))
        except (json.JSONDecodeError, Exception) as e:
            signals.append(Signal(
                source=SignalSource.VIGIL,
                severity=Severity.EMERGENCY,
                category="security",
                title="pv_lock.json illisible!",
                message=f"Erreur lecture pv_lock.json: {e}",
                threat_type=ThreatType.PV_BYPASS,
            ))
        return signals

    # ──────────────────────────────────────────
    # RAPPORT DE MENACES
    # ──────────────────────────────────────────

    def get_threat_report(self) -> ThreatReport:
        """Genere un rapport de menaces agrege."""
        now = time.time()
        cutoff_24h = now - 86400

        # Comptage par type
        threats_by_type: dict[str, int] = defaultdict(int)
        total = 0
        for ip, signals in self._threat_signals.items():
            for s in signals:
                if s["time"] > cutoff_24h:
                    threats_by_type[s["type"]] += 1
                    total += 1

        # Top offenders
        top = sorted(
            self._threat_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        top_offenders = [
            {"ip": ip, "score": score,
             "signals": len(self._threat_signals.get(ip, []))}
            for ip, score in top if score > 0
        ]

        return ThreatReport(
            total_threats_24h=total,
            threats_by_type=dict(threats_by_type),
            top_offenders=top_offenders,
            banned_ips=len(self._banned_ips),
            blocked_requests_24h=sum(
                1 for ip in self._banned_ips
                if self._banned_ips[ip]["until"] > cutoff_24h
            ),
            honeypot_hits_24h=threats_by_type.get("honeypot_hit", 0),
            auto_actions_taken=self._actions_taken[-20:],
        )

    def get_status(self) -> dict:
        """Status compact pour API/SMS."""
        report = self.get_threat_report()
        return {
            "threats_24h": report.total_threats_24h,
            "banned_ips": report.banned_ips,
            "top_threat": (report.top_offenders[0]
                          if report.top_offenders else None),
            "actions_today": len(self._actions_taken),
            "monitored_files": len(self._file_hashes),
        }

    # ──────────────────────────────────────────
    # SCAN PERIODIQUE (appele par le Brain)
    # ──────────────────────────────────────────

    def periodic_scan(self) -> list[Signal]:
        """
        Scan periodique (toutes les 30s).
        Verifie l'integrite, nettoie les bans expires, decay les scores.
        """
        signals = []
        now = time.time()

        # Integrity check toutes les 5 minutes
        if now - self._last_integrity_check > 300:
            signals.extend(self.check_file_integrity())
            signals.extend(self.check_pv_integrity())
            self._last_integrity_check = now

        # Cleanup bans expires
        expired = [
            ip for ip, ban in self._banned_ips.items()
            if now > ban["until"]
        ]
        for ip in expired:
            del self._banned_ips[ip]

        # Decay threat scores (perd 1 point/minute)
        for ip in list(self._threat_scores.keys()):
            self._threat_scores[ip] = max(0, self._threat_scores[ip] - 0.5)
            if self._threat_scores[ip] == 0:
                del self._threat_scores[ip]
                self._threat_signals.pop(ip, None)

        # Cleanup vieux compteurs
        cutoff = now - 120
        for ip in list(self._request_counts.keys()):
            self._request_counts[ip] = [
                t for t in self._request_counts[ip] if t > cutoff]
            if not self._request_counts[ip]:
                del self._request_counts[ip]

        for ip in list(self._failed_auths.keys()):
            self._failed_auths[ip] = [
                t for t in self._failed_auths[ip] if t > cutoff]
            if not self._failed_auths[ip]:
                del self._failed_auths[ip]

        return signals

    # ──────────────────────────────────────────
    # ANALYSE IA (toutes les 5 min)
    # ──────────────────────────────────────────

    def build_ai_analysis_prompt(self) -> Optional[str]:
        """
        Construit le prompt pour l'analyse IA des menaces.
        Retourne None si rien a analyser.
        """
        report = self.get_threat_report()
        if report.total_threats_24h == 0 and report.banned_ips == 0:
            return None

        prompt = f"""Tu es Vigil, l'agent de securite IA de Luna (serveur de compagnon IA pour personnes agees).
Analyse ce rapport de securite des 24 dernieres heures et donne:
1. Une evaluation de la situation (1-2 phrases)
2. Les menaces les plus preoccupantes
3. Des recommandations si action humaine necessaire
4. Si tu detectes un pattern d'attaque coordonnee

Rapport:
- Total menaces: {report.total_threats_24h}
- Par type: {json.dumps(report.threats_by_type, indent=2)}
- IPs bannies: {report.banned_ips}
- Top offenders: {json.dumps(report.top_offenders[:5], indent=2)}
- Actions auto prises: {json.dumps(report.auto_actions_taken[-10:], indent=2)}

Reponds en francais, format court et actionnable. Max 500 chars."""

        return prompt

    # ──────────────────────────────────────────
    # SHIELD MODE (whitelist only)
    # ──────────────────────────────────────────

    def activate_shield(self, whitelist_ips: Optional[list] = None) -> Signal:
        """Active le mode bouclier — seules les IPs whitelist passent."""
        return Signal(
            source=SignalSource.VIGIL,
            severity=Severity.CRITICAL,
            category="security",
            title="Mode BOUCLIER active",
            message=("Seules les IPs autorisees peuvent acceder au serveur. "
                     f"Whitelist: {whitelist_ips or 'aucune'}"),
            metadata={"shield": True, "whitelist": whitelist_ips or []},
        )

    def deactivate_shield(self) -> Signal:
        return Signal(
            source=SignalSource.VIGIL,
            severity=Severity.INFO,
            category="security",
            title="Mode BOUCLIER desactive",
            message="Retour en mode normal.",
            metadata={"shield": False},
        )

    # ──────────────────────────────────────────
    # UTILS
    # ──────────────────────────────────────────

    def _threat_summary(self, ip: str) -> str:
        """Resume des types de menaces pour une IP."""
        types = defaultdict(int)
        for s in self._threat_signals.get(ip, []):
            types[s["type"]] += 1
        return ", ".join(f"{k}({v})" for k, v in types.items())

    def _format_duration(self, seconds: int) -> str:
        if seconds >= 86400:
            return f"{seconds // 86400}j"
        if seconds >= 3600:
            return f"{seconds // 3600}h"
        return f"{seconds // 60}min"
