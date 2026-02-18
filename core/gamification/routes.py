"""Routes API gamification IA Watch World.

Client: /api/world/*   (auth JWT client via middleware request.state.tenant_id)
Admin:  /api/admin/world/*  (auth JWT admin, verification dans chaque handler)
"""

import os
import json
import logging
from typing import Optional
from datetime import datetime, date, timedelta

from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse

from .redis_ops import GamificationRedisOps
from .engine import (
    get_level_for_xp, award_xp, check_badges, update_missions,
    compute_stability, initialize_player, collect_mission_reward,
    buy_shop_item,
)
from .constants import (
    CLIENT_LEVELS, ADMIN_LEVELS,
    ALL_CLIENT_BADGES, ALL_ADMIN_BADGES, BADGE_CATEGORIES, RARITY_COLORS,
    SHOP_ITEMS, SHOP_CATEGORIES,
    FAMILY_LEVELS, FAMILY_BLASON_TIERS,
)
from .schemas import PlayerState, Mission, StabilityGauge, CollectRewardRequest

logger = logging.getLogger(__name__)

gamification_router = APIRouter()

# =====================================================================
# HELPERS
# =====================================================================

def _get_gops(request: Request) -> Optional[GamificationRedisOps]:
    """Get GamificationRedisOps from app state."""
    rc = getattr(request.app.state, "_redis_client", None)
    if rc is None:
        # Fallback: try module-level variable from luna_web
        try:
            from luna_web import _redis_client
            rc = _redis_client
        except (ImportError, AttributeError):
            return None
    if rc is None:
        return None
    return GamificationRedisOps(rc)


def _get_tenant_id(request: Request) -> Optional[int]:
    """Extract tenant_id from request state (set by middleware)."""
    tid = getattr(request.state, "tenant_id", None)
    if tid is not None:
        try:
            return int(tid)
        except (ValueError, TypeError):
            pass
    return None


def _verify_admin_token(request: Request) -> bool:
    """Verify admin JWT token."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    token = auth[7:]
    try:
        import jwt as pyjwt
        jwt_secret = os.getenv("JWT_SECRET_KEY", "luna-admin-fallback-key")
        payload = pyjwt.decode(token, jwt_secret, algorithms=["HS256"])
        return payload.get("role") == "admin"
    except Exception:
        return False


def _error(msg: str, status: int = 400):
    return JSONResponse(status_code=status, content={"error": msg})


def _unavailable():
    return _error("Gamification non disponible", 503)


# =====================================================================
# CLIENT ENDPOINTS : /api/world/*
# =====================================================================

@gamification_router.get("/api/world/player")
async def get_player(request: Request):
    """Profil joueur client (XP, niveau, progression)."""
    gops = _get_gops(request)
    if not gops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    player_data = gops.get_player(tid)
    if not player_data:
        await initialize_player(gops, tid)
        player_data = gops.get_player(tid)

    player = PlayerState.from_redis(player_data or {})
    level_info = get_level_for_xp(player.xp, CLIENT_LEVELS)

    return {
        "player": {
            "xp": player.xp,
            "level": level_info["level"],
            "title": level_info["title"],
            "xp_for_current_level": level_info["xp_current_level"],
            "xp_for_next_level": level_info["xp_next_level"],
            "progress_percent": level_info["progress_percent"],
            "streak_days": player.streak_days,
            "streak_best": player.streak_best,
            "last_active_date": player.last_active_date,
            "joined_at": player.joined_at,
            "days_active": player.days_active,
            "total_messages": player.total_messages,
            "total_calls": player.total_calls,
            "total_visio": player.total_visio,
            "badges_count": player.badges_count,
            "missions_completed": player.missions_completed,
            "stars": player.stars,
        }
    }


@gamification_router.get("/api/world/badges")
async def get_badges(request: Request):
    """Catalogue badges client (gagnes + verrouilles)."""
    gops = _get_gops(request)
    if not gops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    earned_set = gops.get_badges(tid)
    badges = []
    for badge_id, badge_def in ALL_CLIENT_BADGES.items():
        earned = badge_id in earned_set
        earned_at = None
        if earned:
            detail = gops.get_badge_detail(tid, badge_id)
            if detail:
                earned_at = detail.get("earned_at")
        badges.append({
            "id": badge_id,
            "name": badge_def["name"],
            "description": badge_def["description"],
            "category": badge_def["category"],
            "icon": badge_def["icon"],
            "rarity": badge_def["rarity"],
            "earned": earned,
            "earned_at": earned_at,
        })

    return {
        "badges": badges,
        "earned_count": len(earned_set),
        "total_count": len(ALL_CLIENT_BADGES),
        "categories": BADGE_CATEGORIES,
        "rarity_colors": RARITY_COLORS,
    }


@gamification_router.get("/api/world/missions")
async def get_missions(request: Request):
    """Missions actives client avec progression."""
    gops = _get_gops(request)
    if not gops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    active_ids = gops.get_active_mission_ids(tid)
    missions = []
    for mid in active_ids:
        data = gops.get_mission(tid, mid)
        if not data:
            continue
        m = Mission.from_redis(mid, data)
        # Compute relative progress for display
        start_progress = int(data.get("start_progress", 0))
        rel_progress = max(m.progress - start_progress, 0)
        rel_target = max(m.target - start_progress, 1)
        pct = round((rel_progress / rel_target) * 100, 1)
        missions.append({
            "id": m.id,
            "type": m.type,
            "title": m.title,
            "description": m.description,
            "category": m.category,
            "progress": rel_progress,
            "target": rel_target,
            "progress_percent": min(pct, 100.0),
            "xp_reward": m.xp_reward,
            "status": m.status,
            "started_at": m.started_at,
            "collected": m.collected,
        })

    completed_total = gops.get_completed_missions_count(tid)

    return {
        "missions": missions,
        "active_count": len(missions),
        "completed_total": completed_total,
        "max_active": 3,
    }


@gamification_router.post("/api/world/missions/check")
async def check_missions(request: Request):
    """Force re-evaluation de toutes les missions."""
    gops = _get_gops(request)
    if not gops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    player = gops.get_player(tid)
    if not player:
        return {"checked": 0, "completed": [], "xp_awarded": 0}

    active_ids = list(gops.get_active_mission_ids(tid))
    completed = []
    for mid in active_ids:
        mission = gops.get_mission(tid, mid)
        if not mission or mission.get("status") != "active":
            continue
        counter_field = mission.get("counter_field", "")
        if counter_field and counter_field in player:
            new_progress = int(player.get(counter_field, 0))
            target = int(mission.get("target", 1))
            gops.update_mission_field(tid, mid, "progress", str(new_progress))
            if new_progress >= target:
                gops.complete_mission(tid, mid)
                gops.increment_player_field(tid, "missions_completed", 1)
                completed.append(mid)

    return {
        "checked": len(active_ids),
        "completed": completed,
        "new_missions_assigned": len(completed),
    }


@gamification_router.post("/api/world/collect-reward")
async def collect_reward(request: Request):
    """Collecter la recompense XP d'une mission terminee."""
    gops = _get_gops(request)
    if not gops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    try:
        body = await request.json()
        mission_id = body.get("mission_id", "")
    except Exception:
        return _error("Corps de requete invalide")

    if not mission_id:
        return _error("mission_id requis")

    result = await collect_mission_reward(gops, tid, mission_id)
    if not result.get("success"):
        return _error(result.get("error", "Erreur"))
    return result


@gamification_router.get("/api/world/activity")
async def get_activity(request: Request, limit: int = Query(30, ge=1, le=50)):
    """Fil d'activite client."""
    gops = _get_gops(request)
    if not gops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    raw_events = gops.get_activity(tid, limit)
    events = []
    for raw in raw_events:
        try:
            evt = json.loads(raw)
            events.append({
                "id": evt.get("id", ""),
                "type": evt.get("type", ""),
                "message": evt.get("message", ""),
                "icon": evt.get("icon", ""),
                "timestamp": evt.get("ts", ""),
                "metadata": evt.get("meta", {}),
            })
        except json.JSONDecodeError:
            continue

    return {"events": events, "count": len(events)}


@gamification_router.get("/api/world/stability")
async def get_stability(request: Request):
    """Jauge de stabilite client."""
    gops = _get_gops(request)
    if not gops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    # Check if we have a recent stability value
    existing = gops.get_stability(tid)
    if existing:
        updated = existing.get("updated_at", "")
        if updated:
            try:
                updated_dt = datetime.fromisoformat(updated)
                if (datetime.utcnow() - updated_dt).total_seconds() < 3600:
                    gauge = StabilityGauge.from_redis(existing)
                    score = gauge.score
                    label, color = _stability_label(score)
                    return {
                        "stability": gauge.model_dump(),
                        "status_label": label,
                        "status_color": color,
                    }
            except (ValueError, TypeError):
                pass

    # Recompute
    gauge_data = compute_stability(gops, tid)
    gauge = StabilityGauge.from_redis(gauge_data)
    score = gauge.score
    label, color = _stability_label(score)
    return {
        "stability": gauge.model_dump(),
        "status_label": label,
        "status_color": color,
    }


def _stability_label(score: int):
    if score >= 80:
        return "Excellent", "green"
    elif score >= 60:
        return "Bon", "yellow"
    elif score >= 40:
        return "A ameliorer", "orange"
    return "Fragile", "red"


# =====================================================================
# SHOP ENDPOINTS : /api/world/shop/*
# =====================================================================

@gamification_router.get("/api/world/shop")
async def get_shop(request: Request):
    """Catalogue boutique avec etat (possede, actif, affordable)."""
    gops = _get_gops(request)
    if not gops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    player_data = gops.get_player(tid)
    player_stars = int(player_data.get("stars", 0)) if player_data else 0
    owned = gops.get_inventory(tid)

    items = []
    for item_id, item_def in SHOP_ITEMS.items():
        is_owned = item_id in owned
        is_active = bool(gops.get_active_bonus(tid, item_id)) if item_def.get("duration_hours") else False
        is_premium = bool(item_def.get("stripe_price_env"))
        items.append({
            "id": item_id,
            "name": item_def["name"],
            "category": item_def["category"],
            "price": item_def["price"],
            "icon": item_def["icon"],
            "description": item_def["description"],
            "reusable": item_def.get("reusable", False),
            "owned": is_owned and not item_def.get("reusable", False),
            "active": is_active,
            "affordable": player_stars >= item_def["price"],
            "is_premium": is_premium,
            "stripe_configured": bool(os.getenv(item_def.get("stripe_price_env", ""), "")) if is_premium else False,
        })

    return {
        "items": items,
        "categories": SHOP_CATEGORIES,
        "player_stars": player_stars,
    }


@gamification_router.post("/api/world/shop/buy")
async def shop_buy(request: Request):
    """Acheter un article de la boutique."""
    gops = _get_gops(request)
    if not gops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    try:
        body = await request.json()
        item_id = body.get("item_id", "")
    except Exception:
        return _error("Corps de requete invalide")

    if not item_id:
        return _error("item_id requis")

    result = buy_shop_item(gops, tid, item_id)
    if not result.get("success"):
        return _error(result.get("error", "Erreur"))
    return result


@gamification_router.get("/api/world/inventory")
async def get_inventory(request: Request):
    """Inventaire du joueur : items possedes + bonus actifs."""
    gops = _get_gops(request)
    if not gops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    owned = list(gops.get_inventory(tid))

    # Check active bonuses
    active_bonuses = []
    for item_id in owned:
        item_def = SHOP_ITEMS.get(item_id, {})
        if item_def.get("duration_hours"):
            bonus = gops.get_active_bonus(tid, item_id)
            if bonus:
                active_bonuses.append(item_id)

    active_outfit = gops.get_active_outfit(tid)
    active_frame = gops.get_active_frame(tid)
    avatar_type = gops.get_avatar_type(tid) or "adult_man"
    return {
        "owned": owned,
        "active_bonuses": active_bonuses,
        "active_outfit": active_outfit or None,
        "active_frame": active_frame or None,
        "avatar_type": avatar_type,
    }


@gamification_router.post("/api/world/outfit/equip")
async def equip_outfit(request: Request):
    """Equip or unequip an outfit for Luna."""
    gops = _get_gops(request)
    if not gops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    try:
        body = await request.json()
        outfit_id = body.get("outfit_id", "")
    except Exception:
        return _error("Corps de requete invalide")

    # Unequip
    if not outfit_id:
        gops.set_active_outfit(tid, "")
        return {"success": True, "active_outfit": None}

    # Validate
    item = SHOP_ITEMS.get(outfit_id)
    if not item or item.get("category") != "tenue":
        return _error("Article non valide")
    owned = gops.get_inventory(tid)
    if outfit_id not in owned:
        return _error("Article non possede")

    gops.set_active_outfit(tid, outfit_id)
    return {"success": True, "active_outfit": outfit_id}


@gamification_router.post("/api/world/frame/equip")
async def equip_frame(request: Request):
    """Equip or unequip a profile frame."""
    gops = _get_gops(request)
    if not gops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    try:
        body = await request.json()
        frame_id = body.get("frame_id", "")
    except Exception:
        return _error("Corps de requete invalide")

    if not frame_id:
        gops.set_active_frame(tid, "")
        return {"success": True, "active_frame": None}

    item = SHOP_ITEMS.get(frame_id)
    if not item or item.get("category") != "cadre":
        return _error("Article non valide")
    owned = gops.get_inventory(tid)
    if frame_id not in owned:
        return _error("Article non possede")

    gops.set_active_frame(tid, frame_id)
    return {"success": True, "active_frame": frame_id}


@gamification_router.post("/api/world/avatar/type")
async def set_avatar_type_endpoint(request: Request):
    """Set subscriber avatar sprite type."""
    gops = _get_gops(request)
    if not gops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    try:
        body = await request.json()
        avatar_type = body.get("avatar_type", "adult_man")
    except Exception:
        return _error("Corps de requete invalide")

    valid_types = ["adult_man", "adult_woman", "child_boy", "child_girl"]
    if avatar_type not in valid_types:
        return _error("Type d'avatar invalide")

    gops.set_avatar_type(tid, avatar_type)
    return {"success": True, "avatar_type": avatar_type}


@gamification_router.post("/api/world/shop/checkout")
async def shop_checkout(request: Request):
    """Create a Stripe Checkout Session for a premium shop item."""
    gops = _get_gops(request)
    if not gops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    try:
        body = await request.json()
        item_id = body.get("item_id", "")
    except Exception:
        return _error("Corps de requete invalide")

    item = SHOP_ITEMS.get(item_id)
    if not item:
        return _error("Article inconnu")

    stripe_env = item.get("stripe_price_env")
    if not stripe_env:
        return _error("Cet article ne supporte pas le paiement Stripe")

    owned = gops.get_inventory(tid)
    if item_id in owned:
        return _error("Deja possede")

    price_id = os.getenv(stripe_env, "")
    if not price_id:
        return _error(f"Prix Stripe non configure ({stripe_env})")

    stripe_key = os.getenv("STRIPE_API_KEY", "")
    if not stripe_key:
        return JSONResponse(status_code=500, content={"error": "STRIPE_API_KEY non configure"})

    try:
        import stripe
        stripe.api_key = stripe_key
        host = request.headers.get("host", "localhost:8888")
        base_url = f"https://{host}"

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=[{"price": price_id, "quantity": 1}],
            metadata={
                "tenant_id": str(tid),
                "world_item_id": item_id,
                "type": "world_premium",
            },
            success_url=f"{base_url}/world?purchase=success&item={item_id}",
            cancel_url=f"{base_url}/world?purchase=cancel",
        )
        logger.info(f"WORLD_CHECKOUT tenant_id={tid} item={item_id}")
        return {"checkout_url": session.url}
    except ImportError:
        return JSONResponse(status_code=500, content={"error": "Module stripe non installe"})
    except Exception as e:
        logger.error(f"Stripe world checkout error: {e}")
        return JSONResponse(status_code=500, content={"error": f"Erreur Stripe: {e}"})


@gamification_router.get("/api/world/family")
async def get_world_family(request: Request):
    """Family data enriched for world display: level, blason, member sprites."""
    gops = _get_gops(request)
    if not gops:
        return _unavailable()
    tid = _get_tenant_id(request)
    if tid is None:
        return _error("Non authentifie", 401)

    # Get or init family level data
    fam_level_data = gops.get_family_level(tid)
    if not fam_level_data:
        fam_level_data = {
            "family_xp": "0", "family_level": "1",
            "blason_tier": "nest", "updated_at": datetime.utcnow().isoformat(),
        }
        gops.set_family_level(tid, fam_level_data)

    family_xp = int(fam_level_data.get("family_xp", "0"))
    family_levels_2 = [(xp, title) for xp, title, _tier in FAMILY_LEVELS]
    level_info = get_level_for_xp(family_xp, family_levels_2)
    blason_tier = fam_level_data.get("blason_tier", "nest")
    blason_info = FAMILY_BLASON_TIERS.get(blason_tier, FAMILY_BLASON_TIERS["nest"])

    # Get family members for sprite data (via RedisClient)
    rc = gops.rc
    members_sprites = []
    try:
        all_members = rc.get_all_family_members(tid)
        for m in all_members[:6]:
            if m.get("is_active", "1") in ("1", "True", "true"):
                members_sprites.append({
                    "name": m.get("name", "?"),
                    "relation": m.get("relation", ""),
                    "member_type": m.get("member_type", "adult"),
                    "is_verified": m.get("is_verified") in ("1", "True", "true"),
                })
    except Exception as e:
        logger.warning(f"Family members fetch failed: {e}")

    return {
        "family_level": level_info["level"],
        "family_title": level_info["title"],
        "family_xp": family_xp,
        "xp_for_current_level": level_info["xp_current_level"],
        "xp_for_next_level": level_info["xp_next_level"],
        "progress_percent": level_info["progress_percent"],
        "blason_tier": blason_tier,
        "blason": blason_info,
        "members": members_sprites,
        "member_count": len(members_sprites),
    }


# =====================================================================
# ADMIN ENDPOINTS : /api/admin/world/*
# =====================================================================

@gamification_router.get("/api/admin/world/player")
async def admin_get_player(request: Request):
    """Profil gamifie exploitant."""
    if not _verify_admin_token(request):
        return _error("Non autorise", 401)
    gops = _get_gops(request)
    if not gops:
        return _unavailable()

    player_data = gops.get_player("admin")
    if not player_data:
        await initialize_player(gops, "admin", is_admin=True)
        player_data = gops.get_player("admin")

    player = PlayerState.from_redis(player_data or {})
    level_info = get_level_for_xp(player.xp, ADMIN_LEVELS)

    return {
        "player": {
            "xp": player.xp,
            "level": level_info["level"],
            "title": level_info["title"],
            "xp_for_next_level": level_info["xp_next_level"],
            "progress_percent": level_info["progress_percent"],
            "badges_count": player.badges_count,
            "missions_completed": player.missions_completed,
        }
    }


@gamification_router.get("/api/admin/world/badges")
async def admin_get_badges(request: Request):
    """Badges exploitant."""
    if not _verify_admin_token(request):
        return _error("Non autorise", 401)
    gops = _get_gops(request)
    if not gops:
        return _unavailable()

    earned_set = gops.get_badges("admin")
    badges = []
    for badge_id, badge_def in ALL_ADMIN_BADGES.items():
        earned = badge_id in earned_set
        earned_at = None
        if earned:
            detail = gops.get_badge_detail("admin", badge_id)
            if detail:
                earned_at = detail.get("earned_at")
        badges.append({
            "id": badge_id,
            "name": badge_def["name"],
            "description": badge_def["description"],
            "category": badge_def["category"],
            "icon": badge_def["icon"],
            "rarity": badge_def["rarity"],
            "earned": earned,
            "earned_at": earned_at,
        })

    return {
        "badges": badges,
        "earned_count": len(earned_set),
        "total_count": len(ALL_ADMIN_BADGES),
    }


@gamification_router.get("/api/admin/world/missions")
async def admin_get_missions(request: Request):
    """Missions exploitant actives."""
    if not _verify_admin_token(request):
        return _error("Non autorise", 401)
    gops = _get_gops(request)
    if not gops:
        return _unavailable()

    active_ids = gops.get_active_mission_ids("admin")
    missions = []
    for mid in active_ids:
        data = gops.get_mission("admin", mid)
        if not data:
            continue
        m = Mission.from_redis(mid, data)
        start_progress = int(data.get("start_progress", 0))
        rel_progress = max(m.progress - start_progress, 0)
        rel_target = max(m.target - start_progress, 1)
        pct = round((rel_progress / rel_target) * 100, 1)
        missions.append({
            "id": m.id,
            "type": m.type,
            "title": m.title,
            "description": m.description,
            "category": m.category,
            "progress": rel_progress,
            "target": rel_target,
            "progress_percent": min(pct, 100.0),
            "xp_reward": m.xp_reward,
            "status": m.status,
            "collected": m.collected,
        })

    return {
        "missions": missions,
        "active_count": len(missions),
        "completed_total": gops.get_completed_missions_count("admin"),
    }


@gamification_router.post("/api/admin/world/missions/check")
async def admin_check_missions(request: Request):
    """Re-evaluation missions exploitant."""
    if not _verify_admin_token(request):
        return _error("Non autorise", 401)
    gops = _get_gops(request)
    if not gops:
        return _unavailable()

    # Compute admin metrics and update player fields
    metrics = _compute_admin_context(gops)
    player = gops.get_player("admin")
    if not player:
        return {"checked": 0, "completed": []}

    for k, v in metrics.items():
        gops.set_player_field("admin", k, str(v))

    # Re-read player with updated fields
    player = gops.get_player("admin")

    # Evaluate each active mission
    active_ids = list(gops.get_active_mission_ids("admin"))
    completed = []
    for mid in active_ids:
        mission = gops.get_mission("admin", mid)
        if not mission or mission.get("status") != "active":
            continue
        counter_field = mission.get("counter_field", "")
        if counter_field and counter_field in player:
            new_progress = int(player.get(counter_field, 0))
            target = int(mission.get("target", 1))
            gops.update_mission_field("admin", mid, "progress", str(new_progress))
            if new_progress >= target:
                gops.complete_mission("admin", mid)
                gops.increment_player_field("admin", "missions_completed", 1)
                completed.append(mid)

    return {"checked": len(active_ids), "completed": completed}


@gamification_router.get("/api/admin/world/activity")
async def admin_get_activity(request: Request, limit: int = Query(30, ge=1, le=50)):
    """Fil d'activite exploitant."""
    if not _verify_admin_token(request):
        return _error("Non autorise", 401)
    gops = _get_gops(request)
    if not gops:
        return _unavailable()

    raw_events = gops.get_activity("admin", limit)
    events = []
    for raw in raw_events:
        try:
            evt = json.loads(raw)
            events.append({
                "id": evt.get("id", ""),
                "type": evt.get("type", ""),
                "message": evt.get("message", ""),
                "icon": evt.get("icon", ""),
                "timestamp": evt.get("ts", ""),
                "metadata": evt.get("meta", {}),
            })
        except json.JSONDecodeError:
            continue

    return {"events": events, "count": len(events)}


@gamification_router.get("/api/admin/world/metrics")
async def admin_get_metrics(request: Request):
    """KPIs exploitant (clients, CA, stabilite moyenne)."""
    if not _verify_admin_token(request):
        return _error("Non autorise", 401)
    gops = _get_gops(request)
    if not gops:
        return _unavailable()

    # Check cache
    cached = gops.get_admin_metrics()
    if cached:
        return {"metrics": {k: _auto_cast(v) for k, v in cached.items()}}

    metrics = _compute_admin_context(gops)
    gops.set_admin_metrics({k: str(v) for k, v in metrics.items()})
    return {"metrics": metrics}


@gamification_router.get("/api/admin/world/clients-rank")
async def admin_clients_rank(request: Request):
    """Classement clients pour la constellation."""
    if not _verify_admin_token(request):
        return _error("Non autorise", 401)
    gops = _get_gops(request)
    if not gops:
        return _unavailable()

    tenant_ids = gops.rc.get_all_tenant_ids()
    clients = []
    for tid in tenant_ids:
        player_data = gops.get_player(tid)
        if not player_data:
            continue
        profile = gops.rc.get_profile(tid)
        auth_record = gops.rc.get_auth_by_tenant_id(tid)

        name = "Client"
        if profile:
            first = profile.get("first_name", "")
            last = profile.get("last_name", "")
            name = f"{first} {last}".strip() or f"Client {tid}"
        elif auth_record:
            name = auth_record.get("email", f"Client {tid}").split("@")[0]

        plan = "essentiel"
        if auth_record:
            plan = auth_record.get("plan", "essentiel")

        stability_data = gops.get_stability(tid)
        stability_score = int(stability_data.get("score", 0)) if stability_data else 0

        last_active = player_data.get("last_active_date", "")
        active_recently = False
        if last_active:
            try:
                la = date.fromisoformat(last_active)
                active_recently = (date.today() - la).days <= 7
            except (ValueError, TypeError):
                pass

        clients.append({
            "tenant_id": tid,
            "name": name,
            "level": int(player_data.get("level", 1)),
            "xp": int(player_data.get("xp", 0)),
            "title": player_data.get("title", "Nouveau Venu"),
            "stability_score": stability_score,
            "last_active": last_active,
            "plan": plan,
            "active_recently": active_recently,
        })

    clients.sort(key=lambda c: c["xp"], reverse=True)
    return {"clients": clients, "total": len(clients)}


# =====================================================================
# ADMIN HELPERS
# =====================================================================

def _compute_admin_context(gops: GamificationRedisOps) -> dict:
    """Compute admin metrics from all tenants."""
    tenant_ids = gops.rc.get_all_tenant_ids()
    total = len(tenant_ids)
    active_7d = 0
    stability_sum = 0
    stability_count = 0
    level_sum = 0

    cutoff = (date.today() - timedelta(days=7)).isoformat()

    for tid in tenant_ids:
        player = gops.get_player(tid)
        if player:
            level_sum += int(player.get("level", 1))
            last = player.get("last_active_date", "")
            if last >= cutoff:
                active_7d += 1
        stab = gops.get_stability(tid)
        if stab:
            stability_sum += int(stab.get("score", 0))
            stability_count += 1

    avg_stability = round(stability_sum / max(stability_count, 1))
    avg_level = round(level_sum / max(total, 1), 1)

    return {
        "clients_total": total,
        "clients_active_7d": active_7d,
        "avg_client_stability": avg_stability,
        "avg_client_level": avg_level,
        "updated_at": datetime.utcnow().isoformat(),
    }


def _auto_cast(value: str):
    """Auto-cast string to int or float if possible."""
    try:
        if "." in value:
            return float(value)
        return int(value)
    except (ValueError, TypeError):
        return value
