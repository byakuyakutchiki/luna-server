"""Routes API sociales : interactions entre souscripteurs.

/api/social/*  (auth JWT client via middleware request.state.tenant_id)
"""

import os
import re
import json
import html
import logging
import time
from collections import defaultdict
from datetime import datetime, date

from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse

from .redis_ops import SocialRedisOps

logger = logging.getLogger(__name__)

social_router = APIRouter()

# =====================================================================
# RATE LIMITER (per-tenant, in-memory)
# =====================================================================
_rate_buckets: dict = defaultdict(lambda: defaultdict(list))  # {action: {tid: [timestamps]}}

_RATE_LIMITS = {
    "heartbeat": (30, 60),       # 30 req / 60s
    "friend_request": (10, 60),  # 10 req / 60s
    "dm_send": (20, 60),         # 20 msg / 60s
    "report": (3, 300),          # 3 reports / 5 min
    "discover": (10, 60),        # 10 req / 60s
    "profile_update": (5, 60),   # 5 req / 60s
}


def _rate_check(action: str, tid: int) -> bool:
    """Retourne True si autorise, False si rate-limited."""
    if action not in _RATE_LIMITS:
        return True
    max_req, window = _RATE_LIMITS[action]
    now = time.time()
    bucket = _rate_buckets[action][tid]
    # Purge old entries
    cutoff = now - window
    while bucket and bucket[0] < cutoff:
        bucket.pop(0)
    if len(bucket) >= max_req:
        return False
    bucket.append(now)
    return True


def _rate_limited():
    return JSONResponse(status_code=429, content={"error": "Trop de requetes. Reessaie dans un instant."})


# =====================================================================
# INPUT SANITIZATION (anti-XSS)
# =====================================================================
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _sanitize(text: str) -> str:
    """Echappe les balises HTML pour eviter le XSS stocke."""
    if not text:
        return text
    return _HTML_TAG_RE.sub("", html.escape(text, quote=True))


# =====================================================================
# HELPERS
# =====================================================================

def _get_sops(request: Request):
    """Get SocialRedisOps from app state. Retourne None si Redis indisponible."""
    try:
        from luna_web import _redis_available
        if not _redis_available():
            return None
    except (ImportError, AttributeError):
        pass
    rc = getattr(request.app.state, "_redis_client", None)
    if rc is None:
        try:
            from luna_web import _redis_client
            rc = _redis_client
        except (ImportError, AttributeError):
            return None
    if rc is None:
        return None
    return SocialRedisOps(rc)


def _get_tenant_id(request: Request):
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
    return _error("Social non disponible", 503)


def _check_minor(sops: SocialRedisOps, tid) -> bool:
    """Retourne True si le souscripteur est mineur (social restreint)."""
    profile = sops.get_social_profile(tid)
    if not profile:
        return False  # Pas de profil = pas verifie, on laisse passer pour le setup
    return profile.get("is_minor") == "true"


def _compute_age(date_of_birth_str: str) -> int:
    """Calcule l'age a partir d'une date de naissance ISO."""
    try:
        dob = date.fromisoformat(date_of_birth_str)
        today = date.today()
        age = today.year - dob.year
        if (today.month, today.day) < (dob.month, dob.day):
            age -= 1
        return age
    except (ValueError, TypeError):
        return 99  # Default : majeur si date invalide


# =====================================================================
# PROFILE
# =====================================================================

@social_router.get("/api/social/profile")
async def get_my_profile(request: Request):
    """Mon profil social."""
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    profile = sops.get_social_profile(tid)
    if not profile:
        # Auto-init du profil social a partir du profil Luna
        rc = sops.rc
        luna_profile = rc.get_profile(tid)
        nickname = ""
        is_minor = "false"
        age_verified = "false"

        if luna_profile:
            first_name = luna_profile.get("first_name", "")
            nickname = first_name or f"User{tid}"
            dob = luna_profile.get("date_of_birth", "")
            if dob:
                age = _compute_age(dob)
                is_minor = "true" if age < 16 else "false"
                age_verified = "true"

        # Default avatar based on subscriber gender
        _default_avatar = "adult_man"
        if luna_profile:
            _gender = (luna_profile.get("gender", "") or "").upper()
            if _gender == "F":
                _default_avatar = "adult_woman"

        profile = {
            "tid": str(tid),
            "nickname": nickname,
            "bio": "",
            "avatar_type": _default_avatar,
            "avatar_skin": "0",
            "frame": "",
            "level": "1",
            "age_verified": age_verified,
            "is_minor": is_minor,
            "created_at": datetime.utcnow().isoformat(),
            "last_seen": datetime.utcnow().isoformat(),
        }
        sops.set_social_profile(tid, profile)

    # Enrich with live data
    from core.gamification.redis_ops import GamificationRedisOps
    gops = GamificationRedisOps(sops.rc)
    player = gops.get_player(tid)
    if player:
        profile["level"] = player.get("level", "1")
    inv_outfit = gops.get_active_outfit(tid)
    inv_frame = gops.get_active_frame(tid)
    inv_avatar = gops.get_avatar_type(tid)
    if inv_outfit:
        profile["outfit"] = inv_outfit
    if inv_frame:
        profile["frame"] = inv_frame
    if inv_avatar:
        profile["avatar_type"] = inv_avatar

    friend_code = sops.get_friend_code(tid)
    pending = sops.get_pending_request_count(tid)

    return {
        "profile": profile,
        "friend_code": friend_code,
        "pending_requests": pending,
        "friend_count": sops.get_friend_count(tid),
    }


@social_router.post("/api/social/profile")
async def update_my_profile(request: Request):
    """Mettre a jour pseudo et bio."""
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)
    if not _rate_check("profile_update", tid):
        return _rate_limited()

    try:
        body = await request.json()
    except Exception:
        return _error("Corps invalide")

    nickname = _sanitize(body.get("nickname", "").strip())
    bio = _sanitize(body.get("bio", "").strip())
    date_of_birth = body.get("date_of_birth", "").strip()
    avatar_type = body.get("avatar_type", "").strip()
    avatar_skin = str(body.get("avatar_skin", "")).strip()

    if nickname:
        if len(nickname) < 2 or len(nickname) > 20:
            return _error("Pseudo entre 2 et 20 caracteres")
        sops.update_social_profile(tid, "nickname", nickname)

    if bio is not None:
        if len(bio) > 100:
            return _error("Bio max 100 caracteres")
        sops.update_social_profile(tid, "bio", bio)

    _VALID_AVATAR_TYPES = {"adult_man", "adult_woman", "elder_man", "elder_woman", "boy", "girl"}
    if avatar_type and avatar_type in _VALID_AVATAR_TYPES:
        sops.update_social_profile(tid, "avatar_type", avatar_type)

    if avatar_skin in {"0", "1", "2", "3", "4", "5"}:
        sops.update_social_profile(tid, "avatar_skin", avatar_skin)

    if date_of_birth:
        age = _compute_age(date_of_birth)
        sops.update_social_profile(tid, "age_verified", "true")
        sops.update_social_profile(tid, "is_minor", "true" if age < 16 else "false")
        # Also store in Luna profile
        rc = sops.rc
        profile_key = rc.get_profile_key(tid) if hasattr(rc, "get_profile_key") else None
        if profile_key:
            rc.client.hset(profile_key, "date_of_birth", date_of_birth)

    # Award XP for profile customization
    try:
        from core.gamification.engine import award_xp
        from core.gamification.redis_ops import GamificationRedisOps
        gops = GamificationRedisOps(sops.rc)
        await award_xp(gops, tid, "profile_customized")
    except Exception:
        pass

    return {"success": True}


@social_router.get("/api/social/profile/{target_tid}")
async def get_public_profile(request: Request, target_tid: int):
    """Profil public d'un autre souscripteur."""
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    if _check_minor(sops, tid):
        return _error("Fonctionnalite sociale non disponible", 403)

    # Check not blocked
    if sops.is_blocked(target_tid, tid):
        return _error("Profil non disponible", 404)

    profile = sops.get_social_profile(target_tid)
    if not profile:
        return _error("Profil non trouve", 404)

    # Return only public fields
    is_friend = sops.client.sismember(
        sops._key("friends", tid), str(target_tid)
    )
    return {
        "profile": {
            "tid": str(target_tid),
            "nickname": profile.get("nickname", ""),
            "bio": profile.get("bio", ""),
            "avatar_type": profile.get("avatar_type", "adult_man"),
            "frame": profile.get("frame", ""),
            "level": profile.get("level", "1"),
        },
        "is_friend": bool(is_friend),
        "is_online": sops.is_online(target_tid),
    }


# =====================================================================
# DISCOVER
# =====================================================================

@social_router.get("/api/social/discover")
async def discover(request: Request):
    """Liste des souscripteurs visibles (hors bloques et mineurs). Max 50 resultats."""
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)
    if not _rate_check("discover", tid):
        return _rate_limited()

    if _check_minor(sops, tid):
        return _error("Fonctionnalite sociale non disponible pour les mineurs", 403)

    all_profiles = sops.get_all_social_profiles()
    blocked = sops.get_blocked(tid)
    friends = sops.get_friends(tid)
    online_set = sops.get_online_tids()

    users = []
    for p in all_profiles:
        p_tid = p.get("tid", "")
        if p_tid == str(tid):
            continue
        if p_tid in blocked:
            continue
        if sops.is_blocked(p_tid, tid):
            continue
        if p.get("is_minor") == "true":
            continue

        users.append({
            "tid": p_tid,
            "nickname": p.get("nickname", ""),
            "avatar_type": p.get("avatar_type", "adult_man"),
            "frame": p.get("frame", ""),
            "level": p.get("level", "1"),
            "is_friend": p_tid in friends,
            "is_online": p_tid in online_set,
        })

    # Sort: online first, then by level desc — cap at 50 results
    users.sort(key=lambda u: (not u["is_online"], -int(u.get("level", "1"))))
    users = users[:50]
    return {"users": users, "count": len(users)}


# =====================================================================
# FRIEND CODE
# =====================================================================

@social_router.get("/api/social/friend-code")
async def get_friend_code(request: Request):
    """Mon code ami unique."""
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)
    code = sops.get_friend_code(tid)
    return {"friend_code": code}


@social_router.post("/api/social/friend-code/use")
async def use_friend_code(request: Request):
    """Ajouter un ami via son code."""
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    if _check_minor(sops, tid):
        return _error("Fonctionnalite sociale non disponible pour les mineurs", 403)

    try:
        body = await request.json()
        code = body.get("code", "").strip().upper()
    except Exception:
        return _error("Corps invalide")

    if not code or len(code) != 6:
        return _error("Code ami invalide")

    target_tid = sops.resolve_friend_code(code)
    if not target_tid:
        return _error("Code ami introuvable")

    if str(target_tid) == str(tid):
        return _error("C'est ton propre code !")

    ok = sops.send_friend_request(tid, target_tid)
    if not ok:
        return _error("Demande impossible (deja ami, bloque, ou deja envoyee)")

    return {"success": True, "target_tid": target_tid}


# =====================================================================
# FRIENDS
# =====================================================================

@social_router.get("/api/social/friends")
async def get_friends(request: Request):
    """Mes amis avec statut en ligne."""
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    friend_tids = sops.get_friends(tid)
    online_set = sops.get_online_tids()

    friends = []
    for f_tid in friend_tids:
        profile = sops.get_social_profile(f_tid)
        if not profile:
            continue
        friends.append({
            "tid": f_tid,
            "nickname": profile.get("nickname", ""),
            "avatar_type": profile.get("avatar_type", "adult_man"),
            "avatar_skin": profile.get("avatar_skin", "0"),
            "frame": profile.get("frame", ""),
            "level": profile.get("level", "1"),
            "is_online": f_tid in online_set,
        })

    friends.sort(key=lambda f: (not f["is_online"], f["nickname"]))
    return {"friends": friends, "count": len(friends)}


@social_router.post("/api/social/friends/request")
async def send_friend_request(request: Request):
    """Envoyer une demande d'ami."""
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)
    if not _rate_check("friend_request", tid):
        return _rate_limited()

    if _check_minor(sops, tid):
        return _error("Fonctionnalite sociale non disponible pour les mineurs", 403)

    try:
        body = await request.json()
        target_tid = body.get("target_tid")
    except Exception:
        return _error("Corps invalide")

    if not target_tid or str(target_tid) == str(tid):
        return _error("Cible invalide")

    ok = sops.send_friend_request(tid, target_tid)
    if not ok:
        return _error("Demande impossible (deja ami, bloque, ou deja envoyee)")

    return {"success": True}


@social_router.get("/api/social/friends/requests")
async def get_friend_requests(request: Request):
    """Demandes d'amis recues en attente."""
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    requester_tids = sops.get_friend_requests(tid)
    requests_list = []
    for r_tid in requester_tids:
        profile = sops.get_social_profile(r_tid)
        requests_list.append({
            "tid": r_tid,
            "nickname": profile.get("nickname", "") if profile else f"User{r_tid}",
            "avatar_type": profile.get("avatar_type", "adult_man") if profile else "adult_man",
            "avatar_skin": profile.get("avatar_skin", "0") if profile else "0",
            "level": profile.get("level", "1") if profile else "1",
        })

    return {"requests": requests_list, "count": len(requests_list)}


@social_router.post("/api/social/friends/accept")
async def accept_friend(request: Request):
    """Accepter une demande d'ami."""
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    try:
        body = await request.json()
        requester_tid = body.get("requester_tid")
    except Exception:
        return _error("Corps invalide")

    if not requester_tid:
        return _error("requester_tid requis")

    ok = sops.accept_friend_request(tid, requester_tid)
    if not ok:
        return _error("Demande non trouvee ou limite d'amis atteinte")

    # Award XP to both
    try:
        from core.gamification.engine import award_xp
        from core.gamification.redis_ops import GamificationRedisOps
        gops = GamificationRedisOps(sops.rc)
        await award_xp(gops, tid, "friend_added")
        await award_xp(gops, requester_tid, "friend_added")
        # Update total_friends counter
        count_me = sops.get_friend_count(tid)
        count_them = sops.get_friend_count(requester_tid)
        gops.set_player_field(tid, "total_friends", str(count_me))
        gops.set_player_field(requester_tid, "total_friends", str(count_them))
    except Exception as e:
        logger.warning(f"Social XP award error: {e}")

    return {"success": True}


@social_router.post("/api/social/friends/decline")
async def decline_friend(request: Request):
    """Refuser une demande d'ami."""
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    try:
        body = await request.json()
        requester_tid = body.get("requester_tid")
    except Exception:
        return _error("Corps invalide")

    if not requester_tid:
        return _error("requester_tid requis")

    sops.decline_friend_request(tid, requester_tid)
    return {"success": True}


@social_router.post("/api/social/friends/remove")
async def remove_friend(request: Request):
    """Retirer un ami."""
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    try:
        body = await request.json()
        friend_tid = body.get("friend_tid")
    except Exception:
        return _error("Corps invalide")

    if not friend_tid:
        return _error("friend_tid requis")

    sops.remove_friend(tid, friend_tid)

    # Update total_friends counter
    try:
        from core.gamification.redis_ops import GamificationRedisOps
        gops = GamificationRedisOps(sops.rc)
        gops.set_player_field(tid, "total_friends", str(sops.get_friend_count(tid)))
        gops.set_player_field(friend_tid, "total_friends", str(sops.get_friend_count(friend_tid)))
    except Exception:
        pass

    return {"success": True}


@social_router.delete("/api/social/friends/{friend_tid}")
async def delete_friend_full(request: Request, friend_tid: int):
    """Retire un ami et TOUTES ses données (amitié + messages DM + unread)."""
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    # FIX-AMIS-GUARDIAN-P0-001 : bloque le retrait si cet ami est le dernier contact
    # Guardian (canal alerte par message interne) et que Guardian est actuellement actif ;
    # sinon nettoie l'entree Guardian orpheline correspondante.
    try:
        guardian_friends = sops.rc.get_guardian_friends(tid) or set()
    except Exception:
        guardian_friends = set()
    if str(friend_tid) in guardian_friends:
        remaining_guardian_friends = {t for t in guardian_friends if t != str(friend_tid)}
        try:
            from luna_web import _get_guardian
            engine = _get_guardian()
            active_sessions = engine.get_active_sessions(tid) if engine else []
        except Exception:
            active_sessions = []
        if not remaining_guardian_friends and active_sessions:
            return JSONResponse(status_code=409, content={
                "error": (
                    "Impossible de retirer cet ami : il est actuellement ton dernier "
                    "contact Guardian (alerte par message) et Guardian est actif. "
                    "Arrete Guardian ou designe un autre ami comme contact avant de "
                    "continuer."
                ),
                "code": "guardian_would_have_no_dm_contact",
            })
        try:
            sops.rc.remove_guardian_friend(tid, friend_tid)
        except Exception:
            pass

    # FIX-AMIS-FRIENDSHIP-CHECK-P3-001 : verifie que c'etait bien un ami avant de
    # repondre success=true (avant, un retrait sur un non-ami etait un no-op silencieux
    # renvoye comme un succes).
    if str(friend_tid) not in sops.get_friends(tid):
        return _error("Ami introuvable", 404)

    result = sops.delete_friend_and_data(tid, friend_tid)

    try:
        from core.gamification.redis_ops import GamificationRedisOps
        gops = GamificationRedisOps(sops.rc)
        gops.set_player_field(tid, "total_friends", str(sops.get_friend_count(tid)))
        gops.set_player_field(friend_tid, "total_friends", str(sops.get_friend_count(friend_tid)))
    except Exception:
        pass

    logger.info(f"delete_friend_full: tid={tid} supprime ami={friend_tid} — {result}")
    return {"success": True, "deleted": result}


# =====================================================================
# AMIS EXTERNES (non-inscrits sur la plateforme)
# =====================================================================

_PHONE_RE = re.compile(r"^\+?[\d\s\-().]{6,20}$")

@social_router.get("/api/social/friends-extern")
async def get_extern_friends(request: Request):
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)
    return {"friends": sops.get_extern_friends(tid)}


@social_router.post("/api/social/friend-extern")
async def add_extern_friend(request: Request):
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    try:
        body = await request.json()
    except Exception:
        return _error("Corps invalide")

    name = _sanitize(body.get("name", "")).strip()
    phone = (body.get("phone", "") or "").strip().replace(" ", "")
    email = _sanitize(body.get("email", "")).strip()

    if not name:
        return _error("Le nom est requis")
    if not phone or not _PHONE_RE.match(phone):
        return _error("Numero de telephone invalide")

    existing = sops.get_extern_friends(tid)
    if len(existing) >= 50:
        return _error("Limite de 50 amis externes atteinte")
    if any(f.get("phone") == phone for f in existing):
        return _error("Cet ami est deja dans ta liste")

    entry = sops.add_extern_friend(tid, name, phone, email)
    return {"success": True, "friend": entry}


@social_router.delete("/api/social/friend-extern/{phone}")
async def remove_extern_friend(request: Request, phone: str):
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)
    phone_dec = phone.replace("%2B", "+")
    sops.remove_extern_friend(tid, phone_dec)
    return {"success": True}


# =====================================================================
# BLOCK / REPORT
# =====================================================================

@social_router.post("/api/social/block")
async def block_user(request: Request):
    """Bloquer un utilisateur."""
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    try:
        body = await request.json()
        target_tid = body.get("target_tid")
    except Exception:
        return _error("Corps invalide")

    if not target_tid or str(target_tid) == str(tid):
        return _error("Cible invalide")

    ok = sops.block_user(tid, target_tid)
    if not ok:
        return _error("Limite de blocages atteinte")

    return {"success": True}


@social_router.post("/api/social/unblock")
async def unblock_user(request: Request):
    """Debloquer un utilisateur."""
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    try:
        body = await request.json()
        target_tid = body.get("target_tid")
    except Exception:
        return _error("Corps invalide")

    if not target_tid:
        return _error("target_tid requis")

    sops.unblock_user(tid, target_tid)
    return {"success": True}


@social_router.post("/api/social/report")
async def report_user(request: Request):
    """Signaler un utilisateur."""
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)
    if not _rate_check("report", tid):
        return _rate_limited()

    try:
        body = await request.json()
        target_tid = body.get("target_tid")
        reason = _sanitize(body.get("reason", "").strip())
    except Exception:
        return _error("Corps invalide")

    if not target_tid:
        return _error("target_tid requis")
    if not reason or len(reason) < 5:
        return _error("Raison requise (min 5 caracteres)")
    if len(reason) > 500:
        return _error("Raison trop longue (max 500 caracteres)")

    sops.report_user(tid, target_tid, reason)
    logger.info(f"SOCIAL_REPORT reporter={tid} target={target_tid} reason={reason[:50]}")
    return {"success": True, "message": "Signalement enregistre. Merci."}


# =====================================================================
# DM (Messages Prives)
# =====================================================================

@social_router.get("/api/social/dm/rooms")
async def get_dm_rooms(request: Request):
    """Mes conversations DM."""
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    if _check_minor(sops, tid):
        return _error("Messages prives non disponibles pour les mineurs", 403)

    rooms = sops.get_dm_rooms(tid)
    unread_per_room = sops.get_unread_dm_per_room(tid)
    enriched = []
    for room in rooms:
        # Find the other participant
        tid1 = room.get("tid1", "")
        tid2 = room.get("tid2", "")
        other_tid = tid2 if str(tid1) == str(tid) else tid1
        other_profile = sops.get_social_profile(other_tid)

        # Check if blocked
        if sops.is_blocked(tid, other_tid) or sops.is_blocked(other_tid, tid):
            continue

        _rid = room.get("room_id", "")
        enriched.append({
            "room_id": _rid,
            "other_tid": other_tid,
            "other_nickname": other_profile.get("nickname", "") if other_profile else f"User{other_tid}",
            "other_avatar_type": other_profile.get("avatar_type", "adult_man") if other_profile else "adult_man",
            "other_avatar_skin": other_profile.get("avatar_skin", "0") if other_profile else "0",
            "other_frame": other_profile.get("frame", "") if other_profile else "",
            "other_online": sops.is_online(other_tid),
            "last_message_at": room.get("last_message_at", ""),
            "last_msg_text": room.get("last_msg_text", ""),
            "last_msg_sender": room.get("last_msg_sender", ""),
            "unread": unread_per_room.get(_rid, 0),
        })

    return {"rooms": enriched, "count": len(enriched)}


@social_router.post("/api/social/dm/create")
async def create_dm(request: Request):
    """Creer ou ouvrir un DM avec un ami."""
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    if _check_minor(sops, tid):
        return _error("Messages prives non disponibles pour les mineurs", 403)

    try:
        body = await request.json()
        friend_tid = body.get("friend_tid")
    except Exception:
        return _error("Corps invalide")

    if not friend_tid:
        return _error("friend_tid requis")

    room_id = sops.create_dm_room(tid, friend_tid)
    if not room_id:
        return _error("Impossible de creer le DM (pas amis ou bloque)")

    return {"success": True, "room_id": room_id}


@social_router.get("/api/social/dm/{room_id}/messages")
async def get_dm_messages(request: Request, room_id: str):
    """Historique des messages d'un DM."""
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    # Verify access
    room = sops.get_dm_room(room_id)
    if not room:
        return _error("Conversation non trouvee", 404)
    if str(tid) not in (room.get("tid1", ""), room.get("tid2", "")):
        return _error("Acces refuse", 403)

    messages = sops.get_dm_messages(room_id)
    # Mark as read when user views the messages
    sops.mark_dm_read(tid, room_id)
    return {"messages": messages, "count": len(messages)}


@social_router.post("/api/social/dm/{room_id}/send")
async def send_dm_message(request: Request, room_id: str):
    """Envoyer un message dans un DM."""
    sops = _get_sops(request)
    if not sops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)
    if not _rate_check("dm_send", tid):
        return _rate_limited()

    if _check_minor(sops, tid):
        return _error("Messages prives non disponibles pour les mineurs", 403)

    # Verify access
    room = sops.get_dm_room(room_id)
    if not room:
        return _error("Conversation non trouvee", 404)
    if str(tid) not in (room.get("tid1", ""), room.get("tid2", "")):
        return _error("Acces refuse", 403)

    # Check block
    other_tid = room.get("tid2") if str(room.get("tid1")) == str(tid) else room.get("tid1")
    if sops.is_blocked(tid, other_tid) or sops.is_blocked(other_tid, tid):
        return _error("Conversation bloquee")

    try:
        body = await request.json()
        text = _sanitize(body.get("text", "").strip())
    except Exception:
        return _error("Corps invalide")

    if not text:
        return _error("Message vide")
    if len(text) > 500:
        return _error("Message trop long (max 500 caracteres)")

    msg = sops.add_dm_message(room_id, tid, text)

    # Award XP
    try:
        from core.gamification.engine import award_xp
        from core.gamification.redis_ops import GamificationRedisOps
        gops = GamificationRedisOps(sops.rc)
        await award_xp(gops, tid, "dm_message_sent")
        # Update total_dm_messages counter
        gops.increment_player_field(tid, "total_dm_messages", 1)
    except Exception:
        pass

    return {"success": True, "message": msg}


# =====================================================================
# PRESENCE (heartbeat)
# =====================================================================

@social_router.post("/api/social/heartbeat")
async def heartbeat(request: Request):
    """Heartbeat de presence en ligne."""
    sops = _get_sops(request)
    if not sops:
        return JSONResponse({"online": True, "pending_requests": 0, "unread_dm_count": 0})
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)
    if not _rate_check("heartbeat", tid):
        return _rate_limited()

    sops.set_online(tid)

    # Auto-init social profile if missing (so friends can see us)
    if not sops.get_social_profile(tid):
        rc = sops.rc
        luna_profile = rc.get_profile(tid)
        nickname = ""
        is_minor = "false"
        age_verified = "false"
        if luna_profile:
            nickname = luna_profile.get("first_name", "") or f"User{tid}"
            dob = luna_profile.get("date_of_birth", "")
            if dob:
                age = _compute_age(dob)
                is_minor = "true" if age < 16 else "false"
                age_verified = "true"
        sops.set_social_profile(tid, {
            "tid": str(tid), "nickname": nickname or f"User{tid}",
            "bio": "", "avatar_type": "adult_man", "frame": "",
            "level": "1", "age_verified": age_verified, "is_minor": is_minor,
            "created_at": datetime.utcnow().isoformat(),
            "last_seen": datetime.utcnow().isoformat(),
        })

    # Return pending friend requests count + unread DMs for notification badge
    pending = sops.get_pending_request_count(tid)
    online_friends_set = sops.get_online_friends(tid)
    online_friends_list = list(online_friends_set)
    unread_dms = sops.get_unread_dm_count(tid)

    return {
        "online": True,
        "pending_requests": pending,
        "unread_dm_count": unread_dms,
        "online_friends": online_friends_list,
        "online_friends_count": len(online_friends_list),
    }
