"""Routes API pour la couche sociale du Monde de Luna.

/api/world/privacy       — GET/POST paramètres confidentialité
/api/world/avatar        — GET/POST configuration avatar
/api/world/invitations   — GET liste, POST envoyer, POST répondre
/api/world/visitors      — GET visiteurs dans mon monde
/api/world/presence      — POST mise à jour présence, DELETE quitter
/api/world/chat          — GET messages, POST envoyer
/api/world/notifications — GET notifications, DELETE effacer
/api/world/map/players   — (déjà existant dans gamification/routes.py)
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from .redis_ops import WorldRedisOps
from .schemas import (
    PrivacySettings, AvatarConfig,
    WorldInvitationCreate, WorldInvitationResponse,
    WorldChatMessage, WorldPresenceUpdate,
)

logger = logging.getLogger(__name__)

world_router = APIRouter()

# =====================================================================
# HELPERS
# =====================================================================

def _get_wops(request: Request) -> Optional[WorldRedisOps]:
    """Get WorldRedisOps from app state."""
    rc = getattr(request.app.state, "_redis_client", None)
    if rc is None:
        try:
            from luna_web import _redis_client
            rc = _redis_client
        except (ImportError, AttributeError):
            return None
    if rc is None:
        return None
    return WorldRedisOps(rc)

def _get_sops(request: Request):
    """Get SocialRedisOps from app state."""
    rc = getattr(request.app.state, "_redis_client", None)
    if rc is None:
        try:
            from luna_web import _redis_client
            rc = _redis_client
        except (ImportError, AttributeError):
            return None
    if rc is None:
        return None
    from core.social.redis_ops import SocialRedisOps
    return SocialRedisOps(rc)

def _get_gops(request: Request):
    """Get GamificationRedisOps from app state."""
    rc = getattr(request.app.state, "_redis_client", None)
    if rc is None:
        try:
            from luna_web import _redis_client
            rc = _redis_client
        except (ImportError, AttributeError):
            return None
    if rc is None:
        return None
    from core.gamification.redis_ops import GamificationRedisOps
    return GamificationRedisOps(rc)

def _get_tenant_id(request: Request) -> Optional[int]:
    tid = getattr(request.state, "tenant_id", None)
    if tid is not None:
        try:
            return int(tid)
        except (ValueError, TypeError):
            pass
    return None

def _error(msg: str, status: int = 400):
    return JSONResponse(status_code=status, content={"error": msg})

def _unavailable():
    return _error("Monde social non disponible", 503)

def _sanitize(text: str) -> str:
    """Nettoie le texte pour éviter XSS."""
    import html, re
    if not text:
        return text
    tag_re = re.compile(r"<[^>]+>")
    return tag_re.sub("", html.escape(text, quote=True))

# =====================================================================
# PRIVACY
# =====================================================================

@world_router.get("/api/world/privacy")
async def get_privacy(request: Request):
    """Récupère les paramètres de confidentialité."""
    wops = _get_wops(request)
    if not wops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    data = wops.get_privacy(tid)
    return {
        "visible_on_map": data.get("visible_on_map", "true") == "true",
        "visible_in_world": data.get("visible_in_world", "true") == "true",
        "accept_friend_requests": data.get("accept_friend_requests", "true") == "true",
        "accept_world_invites": data.get("accept_world_invites", "true") == "true",
        "approximate_location_only": data.get("approximate_location_only", "true") == "true",
        "total_invisible": data.get("total_invisible", "false") == "true",
        "world_public": data.get("world_public", "false") == "true",
    }

@world_router.post("/api/world/privacy")
async def set_privacy(request: Request):
    """Met à jour les paramètres de confidentialité."""
    wops = _get_wops(request)
    if not wops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    try:
        body = await request.json()
    except Exception:
        return _error("Corps invalide")

    settings = {
        "visible_on_map": "true" if body.get("visible_on_map", True) else "false",
        "visible_in_world": "true" if body.get("visible_in_world", True) else "false",
        "accept_friend_requests": "true" if body.get("accept_friend_requests", True) else "false",
        "accept_world_invites": "true" if body.get("accept_world_invites", True) else "false",
        "approximate_location_only": "true" if body.get("approximate_location_only", True) else "false",
        "total_invisible": "true" if body.get("total_invisible", False) else "false",
        "world_public": "true" if body.get("world_public", False) else "false",
    }
    wops.set_privacy(tid, settings)

    # Si total_invisible, on désactive aussi map_visible dans gamification
    gops = _get_gops(request)
    if gops and settings["total_invisible"] == "true":
        gops.set_player_field(tid, "map_visible", "false")
    elif gops and settings["total_invisible"] == "false" and body.get("visible_on_map", True):
        gops.set_player_field(tid, "map_visible", "true")

    return {"success": True, "settings": {k: v == "true" for k, v in settings.items()}}

# =====================================================================
# AVATAR
# =====================================================================

@world_router.get("/api/world/avatar")
async def get_avatar(request: Request):
    """Récupère la configuration avatar."""
    wops = _get_wops(request)
    if not wops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    data = wops.get_avatar(tid)
    # Enrichir avec les données gamification (niveau, prestige, cadre actif)
    gops = _get_gops(request)
    if gops:
        player = gops.get_player(tid)
        if player:
            data["level"] = player.get("level", "1")
            data["prestige_tier"] = player.get("prestige_tier", "decouverte")
            data["prestige_color"] = player.get("prestige_color", "#9ca3af")
            # Cadre actif depuis l'inventaire
            active_frame = gops.get_active_frame(tid)
            if active_frame:
                data["frame"] = active_frame
            # Tenue active
            active_outfit = gops.get_active_outfit(tid)
            if active_outfit:
                data["outfit"] = active_outfit

    return {"avatar": data}

@world_router.post("/api/world/avatar")
async def set_avatar(request: Request):
    """Met à jour la configuration avatar."""
    wops = _get_wops(request)
    if not wops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    try:
        body = await request.json()
    except Exception:
        return _error("Corps invalide")

    valid_genders = {"male", "female", "neutral"}
    gender = body.get("gender", "neutral")
    if gender not in valid_genders:
        return _error("Genre invalide (male, female, neutral)")

    config = {
        "gender": gender,
        "body_style": _sanitize(body.get("body_style", "standard"))[:30],
        "hair": _sanitize(body.get("hair", "default"))[:30],
        "outfit": _sanitize(body.get("outfit", "default"))[:30],
        "aura": _sanitize(body.get("aura", "none"))[:30],
        "frame": _sanitize(body.get("frame", "none"))[:30],
        "primary_color": _sanitize(body.get("primary_color", "#a78bfa"))[:20],
        "badge_featured": _sanitize(body.get("badge_featured", ""))[:50],
        "face_expression": _sanitize(body.get("face_expression", "smile"))[:20],
    }
    wops.set_avatar(tid, config)

    # Award XP pour personnalisation
    try:
        from core.gamification.engine import award_xp
        gops = _get_gops(request)
        if gops:
            await award_xp(gops, tid, "profile_customized")
    except Exception:
        pass

    return {"success": True, "avatar": config}

# =====================================================================
# INVITATIONS MONDE
# =====================================================================

@world_router.get("/api/world/invitations")
async def get_invitations(request: Request):
    """Récupère les invitations reçues et envoyées."""
    wops = _get_wops(request)
    sops = _get_sops(request)
    if not wops or not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    # Nettoyer les expirées
    pending = wops.get_pending_invitations(tid)
    sent = wops.get_sent_invitations(tid)

    # Enrichir avec les profils
    def _enrich(invites):
        enriched = []
        for inv in invites:
            from_tid = inv.get("from_tid", "")
            to_tid = inv.get("to_tid", "")
            other_tid = from_tid if str(to_tid) == str(tid) else to_tid
            profile = sops.get_social_profile(other_tid)
            inv["other_nickname"] = profile.get("nickname", f"User{other_tid}") if profile else f"User{other_tid}"
            inv["other_avatar_type"] = profile.get("avatar_type", "adult_man") if profile else "adult_man"
            enriched.append(inv)
        return enriched

    return {
        "received": _enrich(pending),
        "sent": _enrich(sent),
        "received_count": len(pending),
        "sent_count": len(sent),
    }

@world_router.post("/api/world/invitations/send")
async def send_invitation(request: Request):
    """Envoie une invitation à un ami pour rejoindre son monde."""
    wops = _get_wops(request)
    sops = _get_sops(request)
    if not wops or not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    try:
        body = await request.json()
        target_tid = body.get("target_tid")
        message = _sanitize(body.get("message", ""))[:200]
    except Exception:
        return _error("Corps invalide")

    if not target_tid or str(target_tid) == str(tid):
        return _error("Cible invalide")

    # Vérifier que c'est un ami
    friends = sops.get_friends(tid)
    if str(target_tid) not in friends:
        return _error("Vous devez être amis pour inviter dans le monde", 403)

    # Vérifier que le destinataire accepte les invitations
    if not wops.accepts_world_invites(target_tid):
        return _error("Cet utilisateur n'accepte pas les invitations", 403)

    # Vérifier pas déjà visiteur
    visitors = wops.get_visitors(tid)
    if str(target_tid) in visitors:
        return _error("Cet utilisateur est déjà dans votre monde")

    invite_id = wops.create_invitation(tid, target_tid, message)
    if not invite_id:
        return _error("Impossible d'envoyer l'invitation (limite atteinte ou utilisateur inaccessible)")

    # Notifier le destinataire
    wops.add_notification(target_tid, {
        "type": "world_invitation",
        "message": f"Vous avez reçu une invitation dans le Monde de Luna !",
        "from_tid": str(tid),
        "invite_id": invite_id,
        "ts": datetime.utcnow().isoformat(),
    })

    return {"success": True, "invitation_id": invite_id}

@world_router.post("/api/world/invitations/respond")
async def respond_invitation(request: Request):
    """Accepte ou refuse une invitation."""
    wops = _get_wops(request)
    if not wops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    try:
        body = await request.json()
        invite_id = body.get("invitation_id")
        action = body.get("action")
    except Exception:
        return _error("Corps invalide")

    if not invite_id or action not in ("accept", "decline"):
        return _error("Paramètres invalides")

    # Vérifier que l'invitation est bien pour ce user
    inv = wops.get_invitation(invite_id)
    if not inv or inv.get("to_tid") != str(tid):
        return _error("Invitation non trouvée", 404)

    ok = wops.respond_invitation(invite_id, action)
    if not ok:
        return _error("Action impossible")

    if action == "accept":
        # Mettre à jour la présence du visiteur
        from_tid = inv.get("from_tid", "")
        wops.set_presence(tid, "world1", status="online")
        # Award XP
        try:
            from core.gamification.engine import award_xp
            gops = _get_gops(request)
            if gops:
                await award_xp(gops, tid, "friend_added")
        except Exception:
            pass

    return {"success": True, "action": action}

@world_router.post("/api/world/invitations/cancel")
async def cancel_invitation(request: Request):
    """Annule une invitation envoyée."""
    wops = _get_wops(request)
    if not wops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    try:
        body = await request.json()
        invite_id = body.get("invitation_id")
    except Exception:
        return _error("Corps invalide")

    if not invite_id:
        return _error("invitation_id requis")

    ok = wops.cancel_invitation(tid, invite_id)
    if not ok:
        return _error("Invitation non trouvée ou déjà traitée")

    return {"success": True}

# =====================================================================
# VISITORS & PRESENCE
# =====================================================================

@world_router.get("/api/world/visitors")
async def get_visitors(request: Request):
    """Récupère les visiteurs actuels dans mon monde."""
    wops = _get_wops(request)
    sops = _get_sops(request)
    gops = _get_gops(request)
    if not wops or not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    visitors = wops.get_visitors(tid)
    result = []
    for v_tid in visitors:
        profile = sops.get_social_profile(v_tid)
        avatar = wops.get_avatar(v_tid)
        presence = wops.get_presence(v_tid)

        visitor_data = {
            "tid": v_tid,
            "nickname": profile.get("nickname", f"User{v_tid}") if profile else f"User{v_tid}",
            "avatar_type": profile.get("avatar_type", "adult_man") if profile else "adult_man",
            "level": profile.get("level", "1") if profile else "1",
            "status": presence.get("status", "online") if presence else "online",
            "primary_color": avatar.get("primary_color", "#a78bfa"),
            "aura": avatar.get("aura", "none"),
            "frame": avatar.get("frame", "none"),
        }

        # Enrichir avec prestige gamification
        if gops:
            player = gops.get_player(v_tid)
            if player:
                visitor_data["level"] = player.get("level", "1")
                visitor_data["prestige_tier"] = player.get("prestige_tier", "decouverte")
                visitor_data["prestige_color"] = player.get("prestige_color", "#9ca3af")

        result.append(visitor_data)

    return {"visitors": result, "count": len(result)}

@world_router.get("/api/world/friends-worlds")
async def get_friends_worlds(request: Request):
    """Retourne les amis dont le monde est public (accessible sans invitation)."""
    wops = _get_wops(request)
    sops = _get_sops(request)
    gops = _get_gops(request)
    if not wops or not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    friends = sops.get_friends(tid)
    result = []
    for f_tid in friends:
        if not wops.is_world_public(f_tid):
            continue
        profile = sops.get_social_profile(f_tid)
        avatar = wops.get_avatar(f_tid)
        presence = wops.get_presence(f_tid)
        visitors = wops.get_visitors(f_tid)

        entry = {
            "tid": f_tid,
            "nickname": profile.get("nickname", f"User{f_tid}") if profile else f"User{f_tid}",
            "avatar_type": profile.get("avatar_type", "adult_man") if profile else "adult_man",
            "primary_color": avatar.get("primary_color", "#a78bfa"),
            "aura": avatar.get("aura", "none"),
            "visitor_count": len(visitors),
            "online": bool(presence),
        }
        if gops:
            player = gops.get_player(f_tid)
            if player:
                entry["level"] = player.get("level", "1")
                entry["prestige_tier"] = player.get("prestige_tier", "decouverte")
                entry["prestige_color"] = player.get("prestige_color", "#9ca3af")
        result.append(entry)

    return {"worlds": result, "count": len(result)}

@world_router.post("/api/world/join/{host_tid}")
async def join_public_world(request: Request, host_tid: str):
    """Rejoindre directement le monde public d'un ami (sans invitation)."""
    wops = _get_wops(request)
    sops = _get_sops(request)
    if not wops or not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    if str(host_tid) == str(tid):
        return _error("Vous ne pouvez pas rejoindre votre propre monde")

    # Vérifier amitié
    friends = sops.get_friends(tid)
    if str(host_tid) not in friends:
        return _error("Vous devez être amis pour rejoindre ce monde", 403)

    # Vérifier que le monde est public
    if not wops.is_world_public(host_tid):
        return _error("Ce monde n'est pas ouvert au public", 403)

    # Quitter l'éventuel monde précédent
    current_host = wops.get_host(tid)
    if current_host:
        wops.remove_visitor(current_host, tid)
        wops.add_notification(current_host, {
            "type": "visitor_left",
            "message": "Un visiteur a quitté votre monde.",
            "from_tid": str(tid),
            "ts": datetime.utcnow().isoformat(),
        })

    # Rejoindre le monde public
    wops.add_visitor(host_tid, tid)
    wops.set_presence(tid, "world1", status="online")

    # Notifier l'hôte
    host_profile = sops.get_social_profile(tid)
    visitor_name = host_profile.get("nickname", f"User{tid}") if host_profile else f"User{tid}"
    wops.add_notification(host_tid, {
        "type": "visitor_joined",
        "message": f"{visitor_name} a rejoint votre Monde !",
        "from_tid": str(tid),
        "ts": datetime.utcnow().isoformat(),
    })

    return {"success": True, "host_tid": str(host_tid)}

@world_router.post("/api/world/presence")
async def update_presence(request: Request):
    """Met à jour la présence dans le monde."""
    wops = _get_wops(request)
    if not wops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    try:
        body = await request.json()
        world_id = body.get("world_id", "world1")
        x = body.get("x")
        y = body.get("y")
        status = body.get("status", "online")
    except Exception:
        return _error("Corps invalide")

    if world_id not in ("world1", "world2"):
        return _error("Monde invalide")

    wops.set_presence(tid, world_id, x, y, status)
    return {"success": True}

@world_router.delete("/api/world/presence")
async def leave_world(request: Request):
    """Quitte le monde (supprime la présence et notifie l'hôte)."""
    wops = _get_wops(request)
    if not wops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    # Vérifier si on est visiteur d'un hôte
    host_tid = wops.get_host(tid)
    if host_tid:
        wops.remove_visitor(host_tid, tid)
        # Notifier l'hôte
        wops.add_notification(host_tid, {
            "type": "visitor_left",
            "message": "Un ami a quitté votre Monde de Luna.",
            "visitor_tid": str(tid),
            "ts": datetime.utcnow().isoformat(),
        })

    wops.clear_presence(tid)
    return {"success": True, "message": "Vous avez quitté le monde"}

# =====================================================================
# CHAT MONDE
# =====================================================================

@world_router.get("/api/world/chat")
async def get_chat(request: Request):
    """Récupère les messages du chat du monde actuel."""
    wops = _get_wops(request)
    if not wops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    # Déterminer dans quel monde on est
    presence = wops.get_presence(tid)
    if not presence:
        return {"messages": [], "count": 0}

    # Si on est visiteur, le chat est celui de l'hôte
    host_tid = wops.get_host(tid)
    world_host = host_tid if host_tid else str(tid)

    messages = wops.get_chat_messages(world_host, limit=50)
    return {"messages": messages, "count": len(messages)}

@world_router.post("/api/world/chat")
async def send_chat(request: Request):
    """Envoie un message dans le chat du monde."""
    wops = _get_wops(request)
    sops = _get_sops(request)
    if not wops or not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    try:
        body = await request.json()
        text = _sanitize(body.get("text", "")).strip()
    except Exception:
        return _error("Corps invalide")

    if not text:
        return _error("Message vide")
    if len(text) > 300:
        return _error("Message trop long (max 300 caractères)")

    # Anti-spam basique : vérifier le dernier message
    presence = wops.get_presence(tid)
    if not presence:
        return _error("Vous n'êtes dans aucun monde", 404)

    host_tid = wops.get_host(tid)
    world_host = host_tid if host_tid else str(tid)

    # Vérifier qu'on est bien dans ce monde (visiteur ou hôte)
    if host_tid:
        visitors = wops.get_visitors(host_tid)
        if str(tid) not in visitors:
            return _error("Vous n'êtes pas autorisé à chatter ici", 403)

    # Récupérer le nom d'affichage
    profile = sops.get_social_profile(tid)
    sender_name = profile.get("nickname", f"User{tid}") if profile else f"User{tid}"

    msg = wops.add_chat_message(world_host, tid, sender_name, text)

    # Award XP pour message social
    try:
        from core.gamification.engine import award_xp
        gops = _get_gops(request)
        if gops:
            await award_xp(gops, tid, "dm_message_sent")
    except Exception:
        pass

    return {"success": True, "message": msg}

# =====================================================================
# NOTIFICATIONS
# =====================================================================

@world_router.get("/api/world/notifications")
async def get_notifications(request: Request):
    """Récupère les notifications non lues."""
    wops = _get_wops(request)
    if not wops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    notifications = wops.get_notifications(tid, limit=20)
    count = wops.get_notification_count(tid)
    return {"notifications": notifications, "count": count}

@world_router.delete("/api/world/notifications")
async def clear_notifications(request: Request):
    """Efface toutes les notifications."""
    wops = _get_wops(request)
    if not wops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    wops.clear_notifications(tid)
    return {"success": True}

# =====================================================================
# MAP ENRICHED — profil utilisateur cliquable
# =====================================================================

@world_router.get("/api/world/map/user/{target_tid}")
async def get_map_user_profile(request: Request, target_tid: int):
    """Profil public d'un utilisateur visible sur la carte."""
    wops = _get_wops(request)
    sops = _get_sops(request)
    gops = _get_gops(request)
    if not wops or not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    # Vérifier que la cible est visible
    if not wops.is_visible_on_map(target_tid):
        return _error("Profil non disponible", 404)

    # Vérifier pas bloqué
    if sops.is_blocked(str(tid), str(target_tid)) or sops.is_blocked(str(target_tid), str(tid)):
        return _error("Profil non disponible", 404)

    profile = sops.get_social_profile(target_tid)
    avatar = wops.get_avatar(target_tid)

    result = {
        "tid": target_tid,
        "nickname": profile.get("nickname", f"User{target_tid}") if profile else f"User{target_tid}",
        "avatar_type": profile.get("avatar_type", "adult_man") if profile else "adult_man",
        "level": "1",
        "prestige_tier": "decouverte",
        "prestige_color": "#9ca3af",
        "primary_color": avatar.get("primary_color", "#a78bfa"),
        "aura": avatar.get("aura", "none"),
        "frame": avatar.get("frame", "none"),
        "badge_featured": avatar.get("badge_featured", ""),
        "is_friend": str(target_tid) in sops.get_friends(tid),
        "is_online": sops.is_online(target_tid),
    }

    if gops:
        player = gops.get_player(target_tid)
        if player:
            result["level"] = player.get("level", "1")
            result["prestige_tier"] = player.get("prestige_tier", "decouverte")
            result["prestige_color"] = player.get("prestige_color", "#9ca3af")

    return result
