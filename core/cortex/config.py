"""
Configuration du Cortex — seuils, intervalles, contacts.
Tout est lu depuis .env avec des defaults sains.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CortexConfig:
    """Configuration principale du Cortex."""

    # --- Activation ---
    enabled: bool = True
    loop_interval_seconds: int = 30  # Boucle principale toutes les 30s
    ai_analysis_interval: int = 300  # Analyse IA toutes les 5 min
    ai_model: str = "gpt-4o-mini"  # Modele pour analyses (~0.50€/jour)

    # --- Contacts ---
    founder_phone: str = ""  # Telephone du fondateur (Ludo)
    founder_telegram_chat_id: str = ""  # Telegram fondateur
    exploitant_phone: str = ""  # Telephone exploitant (ADMIN_NUMBER)
    exploitant_telegram_chat_id: str = ""  # Telegram exploitant
    telegram_bot_token: str = ""  # Token bot Telegram

    # --- Twilio (pour SMS) ---
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_sms_from: str = ""

    # --- Seuils Vigil (Securite) ---
    brute_force_threshold: int = 5  # Echecs login avant ban
    brute_force_window: int = 60  # Fenetre en secondes
    scan_threshold: int = 10  # Hits honeypot avant ban
    ddos_threshold: int = 500  # Req/s avant mode bouclier
    threat_score_ban: int = 85  # Score menace pour auto-ban (releve pour eviter faux positifs)
    threat_score_alert: int = 50  # Score menace pour alerte
    ban_duration_soft: int = 3600  # 1h
    ban_duration_hard: int = 86400  # 24h
    ban_duration_permanent: int = 604800  # 7 jours
    max_failed_auth: int = 10  # Echecs auth avant lockout global

    # --- Seuils Doctor (Sante systeme) ---
    redis_ram_warn: int = 80  # % RAM Redis avant alerte
    redis_ram_critical: int = 95  # % RAM Redis avant purge agressive
    disk_warn: int = 85  # % disque avant alerte
    cpu_warn: int = 90  # % CPU avant alerte (soutenu 5 min)
    api_latency_warn: float = 5.0  # Secondes
    api_latency_critical: float = 15.0  # Secondes
    cert_expiry_warn_days: int = 14  # Jours avant expiration
    backup_max_age_hours: int = 24  # Heures sans backup avant alerte
    session_purge_days: int = 30  # Purge sessions >30 jours
    conversation_archive_days: int = 90  # Archive conversations >90 jours

    # --- Seuils Accountant (Business) ---
    quota_warn_pct: int = 80  # % quota avant alerte client
    quota_critical_pct: int = 95  # % quota avant alerte exploitant
    inactive_warn_days: int = 14  # Jours inactif avant alerte
    inactive_critical_days: int = 30  # Jours inactif avant risque churn
    dunning_day1: int = 1  # J+1 apres echec paiement
    dunning_day3: int = 3  # J+3 relance SMS
    dunning_day7: int = 7  # J+7 suspension
    api_budget_warn_pct: int = 80  # % budget API avant throttle

    # --- Briefing ---
    digest_hours: list = field(default_factory=lambda: [8, 20])  # 8h et 20h
    weekly_report_day: int = 0  # 0=lundi
    weekly_report_hour: int = 9  # 9h
    max_urgent_sms_per_day: int = 5  # Anti-spam SMS urgents
    sms_cooldown_seconds: int = 300  # 5 min entre SMS non-urgents

    # --- Emergency Mode (Pilotage SMS) ---
    emergency_enabled: bool = True
    emergency_auth_code: str = ""  # Code 6 chiffres pour auth SMS
    emergency_allowed_phones: list = field(default_factory=list)
    emergency_session_ttl: int = 3600  # Session SMS expire apres 1h

    # --- Redis ---
    redis_url: str = "redis://localhost:6379"

    @classmethod
    def from_env(cls) -> "CortexConfig":
        """Charge la config depuis les variables d'environnement."""
        config = cls()

        config.enabled = os.getenv("CORTEX_ENABLED", "true").lower() == "true"
        config.loop_interval_seconds = int(os.getenv("CORTEX_LOOP_INTERVAL", "30"))
        config.ai_analysis_interval = int(os.getenv("CORTEX_AI_INTERVAL", "300"))
        config.ai_model = os.getenv("CORTEX_AI_MODEL", "gpt-4o-mini")

        # Contacts
        config.founder_phone = os.getenv("FOUNDER_PHONE", "")
        config.founder_telegram_chat_id = os.getenv("FOUNDER_TELEGRAM_CHAT_ID", "")
        config.exploitant_phone = os.getenv("ADMIN_NUMBER", "")
        config.exploitant_telegram_chat_id = os.getenv("ALERT_TELEGRAM_CHAT_ID", "")
        config.telegram_bot_token = os.getenv("ALERT_TELEGRAM_BOT_TOKEN", "")

        # Twilio
        config.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        config.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        config.twilio_sms_from = os.getenv("TWILIO_SMS_FROM", "")

        # Emergency
        config.emergency_enabled = os.getenv("CORTEX_EMERGENCY", "true").lower() == "true"
        config.emergency_auth_code = os.getenv("CORTEX_EMERGENCY_CODE", "")

        # Phones autorisés pour commandes d'urgence
        founder = config.founder_phone
        exploitant = config.exploitant_phone
        extra = os.getenv("CORTEX_EMERGENCY_PHONES", "")
        phones = [p.strip() for p in extra.split(",") if p.strip()]
        if founder:
            phones.insert(0, founder)
        if exploitant and exploitant not in phones:
            phones.append(exploitant)
        config.emergency_allowed_phones = phones

        # Redis
        config.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

        return config


@dataclass
class CortexState:
    """Etat courant du Cortex, persiste dans Redis."""
    mode: str = "normal"  # normal, alert, lockdown, maintenance, shield
    lockdown_reason: str = ""
    lockdown_by: str = ""
    lockdown_at: str = ""
    shield_mode: bool = False  # Mode bouclier (whitelist only)
    whitelist_ips: set = field(default_factory=set)
    banned_ips: dict = field(default_factory=dict)  # ip -> {reason, until, by}
    last_digest: str = ""
    last_weekly: str = ""
    last_ai_analysis: str = ""
    urgent_sms_today: int = 0
    urgent_sms_date: str = ""
