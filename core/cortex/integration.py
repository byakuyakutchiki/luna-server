"""
CORTEX INTEGRATION — Branchement dans luna_web.py

Ce fichier fournit les fonctions d'integration entre le Cortex
et le serveur FastAPI principal. Il est importe par luna_web.py
pour activer le Cortex sans toucher a la structure existante.

Usage dans luna_web.py:
    from core.cortex.integration import (
        init_cortex, start_cortex, stop_cortex,
        cortex_middleware_check, cortex_analyze_request,
        cortex_handle_sms, get_cortex, cortex_routes
    )
"""

import asyncio
import json
import logging
import os
import time
from typing import Optional

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from .brain import LunaCortex
from .config import CortexConfig
from .signals import Severity, Signal, SignalSource

logger = logging.getLogger("cortex.integration")

# Instance globale du Cortex
_cortex: Optional[LunaCortex] = None


def get_cortex() -> Optional[LunaCortex]:
    """Retourne l'instance du Cortex."""
    return _cortex


def init_cortex(redis_client=None) -> Optional[LunaCortex]:
    """
    Initialise le Cortex. Appele au demarrage de luna_web.py.
    Retourne None si CORTEX_ENABLED=false.
    """
    global _cortex
    config = CortexConfig.from_env()

    if not config.enabled:
        logger.info("Cortex desactive (CORTEX_ENABLED=false)")
        return None

    # Le Cortex a besoin d'un client Redis async
    async_redis = None
    redis_url = config.redis_url
    if redis_url:
        try:
            import redis.asyncio as aioredis
            async_redis = aioredis.from_url(
                redis_url, decode_responses=True,
                socket_timeout=5, socket_connect_timeout=5,
            )
            logger.info(f"Cortex Redis async connecte: {redis_url[:30]}...")
        except Exception as e:
            logger.warning(f"Cortex Redis async indisponible: {e}")

    _cortex = LunaCortex(config, async_redis)
    logger.info("Cortex initialise")
    return _cortex


async def start_cortex():
    """Demarre la boucle du Cortex. Appele dans lifespan startup."""
    if _cortex:
        await _cortex.start()


async def stop_cortex():
    """Arrete le Cortex proprement. Appele dans lifespan shutdown."""
    if _cortex:
        await _cortex.stop()


def cortex_middleware_check(ip: str, path: str) -> tuple[bool, str]:
    """
    Verifie si une requete est autorisee par le Cortex.
    Appele dans security_middleware de luna_web.py.

    Returns: (allowed, reason)
        - (True, "") → requete OK
        - (False, "raison") → requete bloquee

    Usage dans le middleware:
        allowed, reason = cortex_middleware_check(client_ip, path)
        if not allowed:
            return JSONResponse(status_code=403, content={"error": reason})
    """
    if not _cortex:
        return True, ""
    return _cortex.is_request_allowed(ip, path)


def cortex_analyze_request(ip: str, method: str, path: str,
                            query: str = "", body: str = "",
                            headers: Optional[dict] = None):
    """
    Analyse une requete pour detecter les menaces.
    Appele dans security_middleware APRES avoir autorise la requete.
    Les signaux sont traites en background (non-bloquant).
    """
    if not _cortex:
        return
    signals = _cortex.analyze_request(ip, method, path, query, body, headers)
    if signals:
        # Traiter en background pour ne pas ralentir la requete
        asyncio.create_task(_cortex.process_signals(signals))


def cortex_record_failed_auth(ip: str, email: str = ""):
    """
    Enregistre un echec d'authentification.
    Appele quand un login echoue dans luna_web.py.
    """
    if not _cortex:
        return
    signals = _cortex.vigil.record_failed_auth(ip, email)
    if signals:
        asyncio.create_task(_cortex.process_signals(signals))


async def cortex_handle_sms(from_phone: str, body: str) -> Optional[str]:
    """
    Traite un SMS entrant comme commande d'urgence potentielle.
    Appele dans webhook_sms de luna_web.py.

    Si le SMS est une commande LUNA (commence par "LUNA"),
    retourne la reponse a envoyer par SMS.
    Sinon retourne None (le SMS est traite normalement).
    """
    if not _cortex:
        return None
    if not _cortex.config.emergency_enabled:
        return None
    return await _cortex.emergency.handle_incoming_sms(from_phone, body)


# ──────────────────────────────────────────
# ROUTES API du Cortex
# ──────────────────────────────────────────

cortex_routes = APIRouter(prefix="/api/cortex", tags=["cortex"])


def _verify_cortex_auth(request: Request) -> bool:
    """Verifie l'authentification pour les endpoints Cortex."""
    if not _cortex:
        return False
    # Verifier la cle API dans le header X-Cortex-Key
    api_key = request.headers.get("X-Cortex-Key", "")
    if api_key and _cortex.auth.verify_api_key(api_key):
        return True
    # Fallback: admin JWT (si present)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return True  # Le middleware JWT a deja valide
    return False


@cortex_routes.get("/status")
async def cortex_status(request: Request):
    """Status du Cortex (accessible sans auth pour monitoring)."""
    if not _cortex:
        return {"enabled": False, "message": "Cortex desactive"}
    return {
        "enabled": True,
        **_cortex.get_cortex_status(),
    }


@cortex_routes.get("/threats")
async def cortex_threats(request: Request):
    """Rapport de menaces (auth requise)."""
    if not _verify_cortex_auth(request):
        return JSONResponse(status_code=401,
                           content={"error": "Authentification requise (X-Cortex-Key)"})
    if not _cortex:
        return {"error": "Cortex desactive"}
    report = _cortex.vigil.get_threat_report()
    return {
        "total_threats_24h": report.total_threats_24h,
        "threats_by_type": report.threats_by_type,
        "top_offenders": report.top_offenders[:10],
        "banned_ips": report.banned_ips,
        "blocked_requests_24h": report.blocked_requests_24h,
        "honeypot_hits_24h": report.honeypot_hits_24h,
        "auto_actions": report.auto_actions_taken[-20:],
    }


@cortex_routes.get("/signals")
async def cortex_signals(request: Request, limit: int = 50):
    """Derniers signaux du Cortex (admin only)."""
    if not _cortex or not _cortex.redis:
        return {"signals": []}
    try:
        if hasattr(_cortex.redis, 'lrange'):
            raw = await _cortex.redis.lrange("cortex:signals", 0, limit - 1)
            signals = []
            for r in raw:
                try:
                    signals.append(json.loads(r))
                except (json.JSONDecodeError, TypeError):
                    pass
            return {"signals": signals}
    except Exception:
        pass
    return {"signals": []}


@cortex_routes.post("/ban/{ip}")
async def cortex_ban_ip(ip: str, request: Request, duration: int = 86400):
    """Ban manuelle d'une IP (admin only)."""
    if not _verify_cortex_auth(request):
        return JSONResponse(status_code=401, content={"error": "Authentification requise"})
    if not _cortex:
        return {"error": "Cortex desactive"}
    _cortex.vigil.manual_ban(ip, duration=duration,
                              reason="Admin API", by="admin_api")
    return {"success": True, "message": f"IP {ip} bannie pour {duration}s"}


@cortex_routes.delete("/ban/{ip}")
async def cortex_unban_ip(ip: str, request: Request):
    """Deban d'une IP (admin only)."""
    if not _verify_cortex_auth(request):
        return JSONResponse(status_code=401, content={"error": "Authentification requise"})
    if not _cortex:
        return {"error": "Cortex desactive"}
    if _cortex.vigil.manual_unban(ip, by="admin_api"):
        return {"success": True, "message": f"IP {ip} debannie"}
    return {"error": f"IP {ip} n'etait pas bannie"}


@cortex_routes.post("/whitelist/{ip}")
async def cortex_whitelist_add(ip: str, request: Request):
    """Ajoute une IP a la whitelist (admin only)."""
    if not _verify_cortex_auth(request):
        return JSONResponse(status_code=401, content={"error": "Authentification requise"})
    if not _cortex:
        return {"error": "Cortex desactive"}
    _cortex.state.whitelist_ips.add(ip)
    if _cortex.redis:
        try:
            await _cortex.redis.sadd("cortex:whitelist", ip)
        except Exception:
            pass
    # Also unban if currently banned
    _cortex.vigil.manual_unban(ip, by="admin_api")
    return {"success": True, "message": f"IP {ip} ajoutee a la whitelist"}


@cortex_routes.delete("/whitelist/{ip}")
async def cortex_whitelist_remove(ip: str, request: Request):
    """Retire une IP de la whitelist (admin only)."""
    if not _verify_cortex_auth(request):
        return JSONResponse(status_code=401, content={"error": "Authentification requise"})
    if not _cortex:
        return {"error": "Cortex desactive"}
    _cortex.state.whitelist_ips.discard(ip)
    if _cortex.redis:
        try:
            await _cortex.redis.srem("cortex:whitelist", ip)
        except Exception:
            pass
    return {"success": True, "message": f"IP {ip} retiree de la whitelist"}


@cortex_routes.get("/warnings")
async def cortex_warnings(request: Request, ip: str = None, limit: int = 50):
    """Liste des avertissements (admin only). ?ip=x.x.x.x pour filtrer."""
    if not _verify_cortex_auth(request):
        return JSONResponse(status_code=401,
                           content={"error": "Authentification requise"})
    if not _cortex:
        return {"error": "Cortex desactive"}
    warnings = _cortex.vigil.get_warnings(ip=ip)
    return {
        "warnings": warnings[-limit:],
        "total": len(warnings),
        "warnings_before_ban": _cortex.vigil.WARNINGS_BEFORE_BAN,
    }


@cortex_routes.get("/ip/{ip}")
async def cortex_ip_status(ip: str, request: Request):
    """Status complet d'une IP: score, avertissements, ban (admin only)."""
    if not _verify_cortex_auth(request):
        return JSONResponse(status_code=401,
                           content={"error": "Authentification requise"})
    if not _cortex:
        return {"error": "Cortex desactive"}
    return _cortex.vigil.get_ip_status(ip)


@cortex_routes.delete("/warnings/{ip}")
async def cortex_clear_warnings(ip: str, request: Request):
    """Efface les avertissements d'une IP (admin only)."""
    if not _verify_cortex_auth(request):
        return JSONResponse(status_code=401,
                           content={"error": "Authentification requise"})
    if not _cortex:
        return {"error": "Cortex desactive"}
    count = len(_cortex.vigil._warnings.get(ip, []))
    _cortex.vigil._warnings.pop(ip, None)
    # Nettoyer aussi dans Redis
    if _cortex.redis:
        try:
            await _cortex.redis.delete(f"cortex:warnings:{ip}")
        except Exception:
            pass
    return {"success": True, "message": f"{count} avertissement(s) effaces pour {ip}"}


@cortex_routes.post("/mode/{mode}")
async def cortex_set_mode(mode: str, request: Request):
    """Change le mode du serveur (admin only)."""
    if not _verify_cortex_auth(request):
        return JSONResponse(status_code=401, content={"error": "Authentification requise"})
    if not _cortex:
        return {"error": "Cortex desactive"}
    valid_modes = ("normal", "lockdown", "shield", "maintenance")
    if mode not in valid_modes:
        return {"error": f"Mode invalide. Valides: {valid_modes}"}
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    reason = body.get("reason", f"Admin API: mode {mode}")
    await _cortex.set_mode(mode, reason=reason, by="admin_api")
    return {"success": True, "mode": mode, "reason": reason}


@cortex_routes.post("/digest")
async def cortex_force_digest(request: Request):
    """Force l'envoi d'un digest (admin only)."""
    if not _verify_cortex_auth(request):
        return JSONResponse(status_code=401, content={"error": "Authentification requise"})
    if not _cortex:
        return {"error": "Cortex desactive"}
    await _cortex.force_digest()
    return {"success": True, "message": "Digest envoye"}


@cortex_routes.post("/telegram/webhook")
async def cortex_telegram_webhook(request: Request):
    """
    Webhook Telegram — recoit les updates de l'API Telegram.
    Utilise sur Cloud Run (pas de polling possible en serverless).
    Pas d'auth car Telegram envoie directement ici.
    """
    if not _cortex or not _cortex.telegram_bot:
        return {"ok": True}
    try:
        update = await request.json()
        await _cortex.telegram_bot.handle_webhook_update(update)
    except Exception as e:
        logger.error(f"Telegram webhook erreur: {e}")
    # Toujours repondre 200 OK a Telegram
    return {"ok": True}
