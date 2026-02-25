"""
Signaux du Cortex — tout ce que le cerveau collecte et analyse.
Chaque module (Vigil, Doctor, Accountant) produit des signaux.
Le Brain les agrege, les analyse avec l'IA, et decide des actions.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Severity(str, Enum):
    """Niveau de gravite d'un signal."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class SignalSource(str, Enum):
    """Source du signal."""
    VIGIL = "vigil"
    DOCTOR = "doctor"
    ACCOUNTANT = "accountant"
    EMERGENCY = "emergency"
    SYSTEM = "system"


class ActionType(str, Enum):
    """Types d'actions que le Cortex peut executer."""
    BAN_IP = "ban_ip"
    UNBAN_IP = "unban_ip"
    LOCKDOWN = "lockdown"
    UNLOCK = "unlock"
    SHIELD_ON = "shield_on"
    SHIELD_OFF = "shield_off"
    PURGE_REDIS = "purge_redis"
    BACKUP = "backup"
    RESTART_SERVICE = "restart_service"
    THROTTLE_CLIENT = "throttle_client"
    SUSPEND_CLIENT = "suspend_client"
    REACTIVATE_CLIENT = "reactivate_client"
    SEND_SMS = "send_sms"
    SEND_TELEGRAM = "send_telegram"
    ROTATE_KEY = "rotate_key"
    RENEW_CERT = "renew_cert"
    BRIEF_EXPLOITANT = "brief_exploitant"
    BRIEF_FOUNDER = "brief_founder"
    LOG = "log"
    NOOP = "noop"


class ThreatType(str, Enum):
    """Types de menaces detectees par Vigil."""
    BRUTE_FORCE = "brute_force"
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    PATH_TRAVERSAL = "path_traversal"
    COMMAND_INJECTION = "command_injection"
    DDOS = "ddos"
    PORT_SCAN = "port_scan"
    HONEYPOT_HIT = "honeypot_hit"
    CODE_TAMPERING = "code_tampering"
    PV_BYPASS = "pv_bypass"
    LICENSE_VIOLATION = "license_violation"
    API_KEY_LEAK = "api_key_leak"
    GEO_ANOMALY = "geo_anomaly"
    AUTH_BYPASS = "auth_bypass"
    UNKNOWN = "unknown"


@dataclass
class Signal:
    """Un signal collecte par le Cortex."""
    source: SignalSource
    severity: Severity
    category: str  # Ex: "security", "health", "business"
    title: str  # Ex: "Brute force detecte"
    message: str  # Detail humain lisible
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)
    # Pour Vigil
    threat_type: Optional[ThreatType] = None
    ip: Optional[str] = None
    # Pour Accountant
    tenant_id: Optional[str] = None
    # Tracking
    handled: bool = False
    actions_taken: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source": self.source.value,
            "severity": self.severity.value,
            "category": self.category,
            "title": self.title,
            "message": self.message,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "threat_type": self.threat_type.value if self.threat_type else None,
            "ip": self.ip,
            "tenant_id": self.tenant_id,
            "handled": self.handled,
            "actions_taken": self.actions_taken,
        }


@dataclass
class CortexAction:
    """Une action decidee par le Cortex."""
    action_type: ActionType
    target: str = ""  # IP, tenant_id, service name, etc.
    params: dict = field(default_factory=dict)
    reason: str = ""
    decided_by: str = "cortex"  # "cortex", "vigil", "founder_sms", etc.
    timestamp: float = field(default_factory=time.time)
    executed: bool = False
    result: str = ""

    def to_dict(self) -> dict:
        return {
            "action_type": self.action_type.value,
            "target": self.target,
            "params": self.params,
            "reason": self.reason,
            "decided_by": self.decided_by,
            "timestamp": self.timestamp,
            "executed": self.executed,
            "result": self.result,
        }


@dataclass
class SystemHealth:
    """Snapshot de la sante systeme."""
    timestamp: float = field(default_factory=time.time)
    redis_connected: bool = False
    redis_memory_pct: float = 0.0
    redis_memory_used: str = ""
    redis_memory_max: str = ""
    disk_usage_pct: float = 0.0
    cpu_usage_pct: float = 0.0
    uptime_seconds: float = 0.0
    active_connections: int = 0
    requests_last_hour: int = 0
    errors_last_hour: int = 0
    api_latency_ms: dict = field(default_factory=dict)  # service -> latency
    ssl_days_remaining: int = -1
    last_backup_age_hours: float = -1
    luna_mode: str = "unknown"  # normal, lockdown, shield, degraded
    services: dict = field(default_factory=dict)  # service -> status

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class ThreatReport:
    """Rapport de menace agrege par Vigil."""
    timestamp: float = field(default_factory=time.time)
    total_threats_24h: int = 0
    threats_by_type: dict = field(default_factory=dict)
    top_offenders: list = field(default_factory=list)  # [(ip, score, threats)]
    banned_ips: int = 0
    blocked_requests_24h: int = 0
    honeypot_hits_24h: int = 0
    active_attacks: list = field(default_factory=list)
    auto_actions_taken: list = field(default_factory=list)
