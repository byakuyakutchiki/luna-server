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
    r"(--|#|/\*)\s*$",
    r"\bexec\s*\(",
    r"\bchar\s*\(\d+\)",
    r";\s*(drop|delete|update|insert)\b",
    r"0x[0-9a-fA-F]+",
    r"\bwaitfor\s+delay\b",
    r"\bbenchmark\s*\(",
    r"\bsleep\s*\(\d+\)",
]

XSS_PATTERNS = [
    r"<\s*script\b",
    r"\bon\w+\s*=",
    r"javascript\s*:",
    r"<\s*img\b[^>]+onerror",
    r"<\s*svg\b[^>]+onload",
    r"<\s*iframe\b",
    r"document\.cookie",
    r"document\.location",
    r"eval\s*\(",
    r"alert\s*\(",
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
                        headers: Optional[dict] = None) -> list[Signal]:
        """
        Analyse une requete entrante et retourne les signaux de menace.
        Appele par le middleware FastAPI a chaque requete.
        """
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

        # 7. Auto-decision de ban basee sur le threat score
        score = self._threat_scores.get(ip, 0)
        if score >= self.config.threat_score_ban:
            ban_signal = self._auto_ban(ip, score)
            if ban_signal:
                signals.append(ban_signal)

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

            # Auto-ban si > 2x le seuil
            if count >= self.config.brute_force_threshold * 2:
                ban_signal = self._auto_ban(ip, self._threat_scores[ip])
                if ban_signal:
                    signals.append(ban_signal)

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

    def _auto_ban(self, ip: str, score: float) -> Optional[Signal]:
        """Ban automatique d'une IP basee sur son score."""
        if ip in self._banned_ips:
            return None  # Deja bannie

        # Escalade progressive
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
            "reason": f"Score menace {score:.0f}/100 ({signals_count} signaux)",
            "level": level,
            "score": score,
        }

        duration_str = self._format_duration(duration)
        action_desc = f"Ban {ip} ({level}, {duration_str}) — score {score:.0f}"
        self._actions_taken.append(action_desc)

        return Signal(
            source=SignalSource.VIGIL,
            severity=Severity.CRITICAL,
            category="security",
            title=f"IP {ip} bannie ({level})",
            message=(
                f"IP {ip} auto-bannie pour {duration_str}. "
                f"Score menace: {score:.0f}/100. "
                f"Signaux: {signals_count}. "
                f"Types: {self._threat_summary(ip)}"
            ),
            threat_type=ThreatType.UNKNOWN,
            ip=ip,
            metadata={"ban_level": level, "ban_duration": duration},
        )

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
