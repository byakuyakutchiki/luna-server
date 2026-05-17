"""
Configuration des IPs fondateur — chargées depuis l'environnement.

Ces IPs bénéficient d'un bypass absolu de toutes les sécurités Cortex.
Configurer dans .env (ou variables Cloud Run) :

    FOUNDER_IPS=92.92.129.172
    FOUNDER_IP_PREFIXES=2a02:8429:a9e4:f101:

Plusieurs valeurs séparées par des virgules.
"""
import os
import logging

logger = logging.getLogger(__name__)

_FOUNDER_IPS: frozenset | None = None
_FOUNDER_IP_PREFIXES: tuple | None = None


def _load() -> None:
    global _FOUNDER_IPS, _FOUNDER_IP_PREFIXES

    raw_ips = os.getenv("FOUNDER_IPS", "")
    raw_prefixes = os.getenv("FOUNDER_IP_PREFIXES", "")

    _FOUNDER_IPS = frozenset(ip.strip() for ip in raw_ips.split(",") if ip.strip())
    _FOUNDER_IP_PREFIXES = tuple(p.strip() for p in raw_prefixes.split(",") if p.strip())

    if not _FOUNDER_IPS and not _FOUNDER_IP_PREFIXES:
        logger.warning(
            "FOUNDER_IPS et FOUNDER_IP_PREFIXES non configures — "
            "la protection fondateur est inactive."
        )


def is_founder_ip(ip: str) -> bool:
    """Retourne True si l'IP est celle du fondateur (bypass total Cortex)."""
    global _FOUNDER_IPS, _FOUNDER_IP_PREFIXES
    if _FOUNDER_IPS is None:
        _load()
    if ip in _FOUNDER_IPS:
        return True
    for prefix in _FOUNDER_IP_PREFIXES:
        if ip.startswith(prefix):
            return True
    return False
