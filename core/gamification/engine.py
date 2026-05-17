"""Moteur de gamification IA Watch World.

Logique XP, level-up, badges, missions, stabilite.
Toutes les fonctions sont async-safe et fire-and-forget.
"""

import json
import uuid
import random
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple

from .constants import (
    CLIENT_LEVELS, CLIENT_LEVELS_V1, ADMIN_LEVELS,
    XP_ACTIONS, ADMIN_XP_ACTIONS,
    ALL_CLIENT_BADGES, ALL_ADMIN_BADGES,
    ONBOARDING_MISSIONS, RECURRING_MISSIONS, ADMIN_MISSIONS,
    STAR_REWARDS, SHOP_ITEMS,
    FAMILY_XP_ACTIONS, FAMILY_LEVELS, FAMILY_BLASON_TIERS,
    WORLD2_RECURRING_MISSIONS, WORLD2_UNLOCK_LEVEL,
    PRESTIGE_TIERS,
)
from .redis_ops import GamificationRedisOps, MAX_ACTIVE_MISSIONS
from .schemas import PlayerState, StabilityGauge

logger = logging.getLogger(__name__)


# =====================================================================
# LEVEL COMPUTATION
# =====================================================================

def get_level_for_xp(xp: int, levels: list = None) -> dict:
    """Retourne le niveau, titre et progression pour un montant d'XP."""
    if levels is None:
        levels = CLIENT_LEVELS
    current_level = 1
    current_title = levels[0][1]
    current_threshold = 0
    next_threshold = levels[1][0] if len(levels) > 1 else xp + 1000

    for i, (threshold, title) in enumerate(levels):
        if xp >= threshold:
            current_level = i + 1
            current_title = title
            current_threshold = threshold
            next_threshold = levels[i + 1][0] if i + 1 < len(levels) else threshold + 1000
        else:
            break

    denom = max(next_threshold - current_threshold, 1)
    progress = ((xp - current_threshold) / denom) * 100
    return {
        "level": current_level,
        "title": current_title,
        "xp_current_level": current_threshold,
        "xp_next_level": next_threshold,
        "progress_percent": round(min(progress, 100.0), 1),
    }


def get_prestige_tier(level: int) -> dict:
    """Retourne le palier de prestige pour un niveau donne."""
    for tier_name, tier_data in PRESTIGE_TIERS.items():
        if level in tier_data["levels"]:
            return {
                "tier": tier_name,
                "label": tier_data["label"],
                "color": tier_data["color"],
                "glow": tier_data["glow"],
                "gradient": tier_data["gradient"],
            }
    return {
        "tier": "decouverte",
        "label": "Decouverte",
        "color": "#9ca3af",
        "glow": "rgba(156,163,175,0.3)",
        "gradient": "linear-gradient(135deg, #9ca3af, #d1d5db)",
    }


# =====================================================================
# XP AWARD
# =====================================================================

async def award_xp(gops: GamificationRedisOps, tenant_id, action: str,
                   metadata: dict = None, is_admin: bool = False) -> dict:
    """Award XP for an action. Returns result dict."""
    xp_table = ADMIN_XP_ACTIONS if is_admin else XP_ACTIONS
    action_def = xp_table.get(action)
    if not action_def:
        return {"xp_gained": 0, "reason": "unknown_action"}

    # Check daily cap
    count = gops.check_and_increment_daily_cap(tenant_id, action)
    if count > action_def["daily_cap_count"]:
        return {"xp_gained": 0, "reason": "daily_cap_reached"}

    xp_amount = action_def["xp"]

    # Check XP x2 bonus
    if not is_admin:
        xp_bonus = gops.get_active_bonus(tenant_id, "bonus_xp2")
        if xp_bonus:
            xp_amount *= 2

    # Streak bonus for daily_login
    if action == "daily_login" and not is_admin:
        player = gops.get_player(tenant_id)
        if player:
            streak = int(player.get("streak_days", 0))
            xp_amount += min(streak, 30)

    # Award XP
    new_xp = gops.increment_player_field(tenant_id, "xp", xp_amount)

    # Increment action counter
    counter_map = {
        "chat_message": "total_messages",
        "voice_call": "total_calls",
        "visio_session": "total_visio",
        "profile_update": "profile_fields",
        "add_contact": "total_contacts",
        "create_instruction": "total_instructions",
        "create_note": "total_notes",
        # Family Pack
        "family_setup": "total_family_groups",
        "family_member_added": "total_family_members",
        "family_member_verified": "total_family_verified",
        "family_message_sent": "total_family_messages",
        "escalation_rule_created": "total_escalation_rules",
        "family_sos": "total_sos",
        # Admin
        "new_client": "clients_total",
    }
    counter_field = counter_map.get(action)
    if counter_field:
        gops.increment_player_field(tenant_id, counter_field, 1)

    # Award family XP for family actions
    if action in FAMILY_XP_ACTIONS and not is_admin:
        award_family_xp(gops, tenant_id, action)

    # Update streak for daily_login
    if action == "daily_login":
        _update_streak(gops, tenant_id)

    # Check level up
    levels = ADMIN_LEVELS if is_admin else CLIENT_LEVELS
    level_info = get_level_for_xp(new_xp, levels)
    old_level = int(gops.get_player_field(tenant_id, "level") or "1")
    leveled_up = level_info["level"] > old_level

    if leveled_up:
        gops.set_player_field(tenant_id, "level", str(level_info["level"]))
        gops.set_player_field(tenant_id, "title", level_info["title"])
        prestige = get_prestige_tier(level_info["level"])
        gops.set_player_field(tenant_id, "prestige_tier", prestige["tier"])
        gops.set_player_field(tenant_id, "prestige_color", prestige["color"])
        # Activity event enrichi avec prestige
        gops.add_activity(tenant_id, json.dumps({
            "id": str(uuid.uuid4()),
            "type": "level_up",
            "message": f"Niveau {level_info['level']} atteint : {level_info['title']} !",
            "icon": "arrow-up",
            "ts": datetime.utcnow().isoformat(),
            "meta": {
                "level": level_info["level"],
                "title": level_info["title"],
                "prestige_tier": prestige["tier"],
                "prestige_label": prestige["label"],
                "prestige_color": prestige["color"],
            },
        }))
        # Award stars for level up
        if not is_admin:
            award_stars(gops, tenant_id, "level_up")
        # Push notification for level-up
        try:
            from core.notifications.engine import NotificationEngine
            _ne = NotificationEngine(gops.rc)
            _ne.deliver_level_up(tenant_id, level_info["level"], level_info["title"])
        except Exception:
            pass

    # XP activity event (only for significant gains)
    if xp_amount >= 5:
        action_labels = {
            "chat_message": "message envoye",
            "voice_call": "appel vocal",
            "visio_session": "session visio",
            "profile_update": "profil mis a jour",
            "add_contact": "contact ajoute",
            "create_instruction": "instruction creee",
            "create_note": "note creee",
            "daily_login": "connexion du jour",
            # Family Pack
            "family_setup": "groupe familial cree",
            "family_member_added": "membre ajoute",
            "family_member_verified": "membre verifie",
            "family_message_sent": "message famille",
            "escalation_rule_created": "regle d'escalade creee",
            "family_sos": "alerte SOS",
            # Admin
            "new_client": "nouveau client",
            "first_client": "premier client",
            "alert_resolved": "alerte resolue",
        }
        label = action_labels.get(action, action)
        gops.add_activity(tenant_id, json.dumps({
            "id": str(uuid.uuid4()),
            "type": "xp_gained",
            "message": f"+{xp_amount} XP : {label}",
            "icon": "zap",
            "ts": datetime.utcnow().isoformat(),
            "meta": {"xp": xp_amount, "action": action},
        }))

    # Check badges
    new_badges = check_badges(gops, tenant_id, is_admin)

    # Award stars for new badges
    if not is_admin:
        for badge_id in new_badges:
            badge_def = ALL_CLIENT_BADGES.get(badge_id, {})
            rarity = badge_def.get("rarity", "common")
            award_stars(gops, tenant_id, f"badge_{rarity}")

    # Award stars for daily login
    if action == "daily_login" and not is_admin:
        award_stars(gops, tenant_id, "daily_login")

    # Update missions
    completed_missions = update_missions(gops, tenant_id, action)

    return {
        "xp_gained": xp_amount,
        "new_xp_total": new_xp,
        "leveled_up": leveled_up,
        "new_level": level_info["level"] if leveled_up else None,
        "new_title": level_info["title"] if leveled_up else None,
        "new_badges": new_badges,
        "completed_missions": completed_missions,
    }


async def award_xp_safe(gops: GamificationRedisOps, tenant_id, action: str,
                        metadata: dict = None, is_admin: bool = False) -> None:
    """Fire-and-forget wrapper. Never raises."""
    try:
        await award_xp(gops, tenant_id, action, metadata, is_admin)
    except Exception as e:
        logger.warning(f"Gamification XP award failed (tenant={tenant_id}, action={action}): {e}")


# =====================================================================
# STREAK MANAGEMENT
# =====================================================================

def _update_streak(gops: GamificationRedisOps, tenant_id) -> None:
    """Update login streak for a tenant."""
    player = gops.get_player(tenant_id)
    if not player:
        return

    today_str = date.today().isoformat()
    last_active = player.get("last_active_date", "")
    streak = int(player.get("streak_days", 0))
    best = int(player.get("streak_best", 0))

    if last_active == today_str:
        return  # Already counted today

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    if last_active == yesterday:
        streak += 1
    else:
        streak = 1  # Reset streak

    if streak > best:
        best = streak

    # Update days_active
    days_active = int(player.get("days_active", 0)) + 1

    gops.set_player_field(tenant_id, "streak_days", str(streak))
    gops.set_player_field(tenant_id, "streak_best", str(best))
    gops.set_player_field(tenant_id, "last_active_date", today_str)
    gops.set_player_field(tenant_id, "days_active", str(days_active))

    # Award stars for streak milestones
    if streak == 7:
        award_stars(gops, tenant_id, "streak_7")
    elif streak == 30:
        award_stars(gops, tenant_id, "streak_30")


# =====================================================================
# BADGE EVALUATION
# =====================================================================

def check_badges(gops: GamificationRedisOps, tenant_id,
                 is_admin: bool = False) -> List[str]:
    """Evaluate badge conditions. Returns list of newly earned badge IDs."""
    player = gops.get_player(tenant_id)
    if not player:
        return []

    badges_catalog = ALL_ADMIN_BADGES if is_admin else ALL_CLIENT_BADGES
    earned = gops.get_badges(tenant_id)
    newly_earned = []

    for badge_id, badge_def in badges_catalog.items():
        if badge_id in earned:
            continue
        try:
            if badge_def["condition"](player):
                gops.add_badge(tenant_id, badge_id, {
                    "earned_at": datetime.utcnow().isoformat(),
                    "category": badge_def["category"],
                    "rarity": badge_def["rarity"],
                })
                gops.increment_player_field(tenant_id, "badges_count", 1)
                newly_earned.append(badge_id)
                gops.add_activity(tenant_id, json.dumps({
                    "id": str(uuid.uuid4()),
                    "type": "badge_earned",
                    "message": f"Nouveau badge : {badge_def['name']} !",
                    "icon": "award",
                    "ts": datetime.utcnow().isoformat(),
                    "meta": {"badge": badge_id, "name": badge_def["name"],
                             "rarity": badge_def["rarity"]},
                }))
        except Exception as e:
            logger.warning(f"Badge check failed for {badge_id}: {e}")

    return newly_earned


# =====================================================================
# MISSION MANAGEMENT
# =====================================================================

def update_missions(gops: GamificationRedisOps, tenant_id,
                    action: str) -> List[str]:
    """Update mission progress based on action. Returns completed mission IDs."""
    completed = []
    active_ids = gops.get_active_mission_ids(tenant_id)
    player = gops.get_player(tenant_id)
    if not player:
        return []

    for mid in active_ids:
        mission = gops.get_mission(tenant_id, mid)
        if not mission or mission.get("status") != "active":
            continue
        if mission.get("action_type") != action:
            continue

        # Update progress from player counter
        counter_field = mission.get("counter_field", "")
        if counter_field and counter_field in player:
            new_progress = int(player.get(counter_field, 0))
            target = int(mission.get("target", 1))
            gops.update_mission_field(tenant_id, mid, "progress", str(new_progress))

            if new_progress >= target:
                gops.complete_mission(tenant_id, mid)
                gops.increment_player_field(tenant_id, "missions_completed", 1)
                completed.append(mid)

                mission_title = mission.get("title", "?")
                gops.add_activity(tenant_id, json.dumps({
                    "id": str(uuid.uuid4()),
                    "type": "mission_completed",
                    "message": f"Mission completee : {mission_title} !",
                    "icon": "flag",
                    "ts": datetime.utcnow().isoformat(),
                    "meta": {"mission_id": mid, "title": mission_title,
                             "xp_reward": mission.get("xp_reward", "0")},
                }))

                # Auto-assign new mission if slot opened
                _assign_new_mission(gops, tenant_id)

    return completed


def _assign_new_mission(gops: GamificationRedisOps, tenant_id) -> Optional[str]:
    """Assign a new recurring mission if there's a free slot."""
    active_ids = gops.get_active_mission_ids(tenant_id)
    if len(active_ids) >= MAX_ACTIVE_MISSIONS:
        return None

    active_types = gops.get_active_mission_types(tenant_id)
    recent_types = gops.get_recently_completed_types(tenant_id, days=7)
    exclude = active_types | recent_types

    # Build candidate pool: base missions + World 2 if level >= 6
    pool = list(RECURRING_MISSIONS)
    player = gops.get_player(tenant_id)
    if player:
        level = int(player.get("level", 1))
        if level >= WORLD2_UNLOCK_LEVEL:
            pool = pool + list(WORLD2_RECURRING_MISSIONS)

    candidates = [m for m in pool if m["type"] not in exclude]
    if not candidates:
        # All missions done recently, allow repeats
        candidates = [m for m in pool if m["type"] not in active_types]
    if not candidates:
        return None

    template = random.choice(candidates)
    mission_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    # Get current progress from player
    player = gops.get_player(tenant_id)
    current_progress = int(player.get(template["counter_field"], 0)) if player else 0

    data = {
        "type": template["type"],
        "title": template["title"],
        "description": template["description"],
        "category": template["category"],
        "progress": str(current_progress),
        "start_progress": str(current_progress),
        "target": str(current_progress + template["target"]),
        "xp_reward": str(template["xp_reward"]),
        "started_at": now,
        "status": "active",
        "completed_at": "",
        "action_type": template["action_type"],
        "counter_field": template["counter_field"],
        "collected": "false",
    }
    gops.add_mission(tenant_id, mission_id, data)
    return mission_id


# =====================================================================
# PLAYER INITIALIZATION
# =====================================================================

async def initialize_player(gops: GamificationRedisOps, tenant_id,
                            is_admin: bool = False) -> None:
    """Create initial player state and assign onboarding missions."""
    existing = gops.get_player(tenant_id)
    if existing:
        return  # Already initialized

    now = datetime.utcnow().isoformat()
    player = PlayerState(joined_at=now)
    gops.set_player(tenant_id, player.to_redis())

    # Assign missions: admin gets ADMIN_MISSIONS, client gets ONBOARDING_MISSIONS
    templates = ADMIN_MISSIONS[:3] if is_admin else ONBOARDING_MISSIONS
    for template in templates:
        mission_id = str(uuid.uuid4())
        data = {
            "type": template["type"],
            "title": template["title"],
            "description": template["description"],
            "category": template["category"],
            "progress": "0",
            "start_progress": "0",
            "target": str(template["target"]),
            "xp_reward": str(template["xp_reward"]),
            "started_at": now,
            "status": "active",
            "completed_at": "",
            "action_type": template["action_type"],
            "counter_field": template["counter_field"],
            "collected": "false",
        }
        gops.add_mission(tenant_id, mission_id, data)

    # Welcome activity
    welcome_msg = "Bienvenue dans IA Watch World !" if is_admin else "Bienvenue dans le Monde Luna !"
    gops.add_activity(tenant_id, json.dumps({
        "id": str(uuid.uuid4()),
        "type": "welcome",
        "message": welcome_msg,
        "icon": "sparkles",
        "ts": now,
        "meta": {},
    }))


async def initialize_player_safe(gops: GamificationRedisOps, tenant_id,
                                 is_admin: bool = False) -> None:
    """Safe wrapper for initialize_player."""
    try:
        await initialize_player(gops, tenant_id, is_admin=is_admin)
    except Exception as e:
        logger.warning(f"Gamification init failed (tenant={tenant_id}): {e}")


# =====================================================================
# STABILITY GAUGE
# =====================================================================

def compute_stability(gops: GamificationRedisOps, tenant_id) -> dict:
    """Compute stability gauge for a client."""
    player = gops.get_player(tenant_id)
    if not player:
        return StabilityGauge().to_redis()

    # --- Regularity (40%) ---
    active_days = int(player.get("days_active", 0))
    # Rough estimation based on days_active vs account age
    joined = player.get("joined_at", "")
    if joined:
        try:
            joined_date = datetime.fromisoformat(joined).date()
            total_days = max((date.today() - joined_date).days, 1)
            day_ratio = min(active_days / total_days, 1.0)
        except (ValueError, TypeError):
            day_ratio = 0.5
    else:
        day_ratio = 0.5

    day_score = day_ratio * 100
    streak_bonus = min(int(player.get("streak_days", 0)), 20)
    regularity = min(round(day_score * 0.8 + streak_bonus), 100)

    # --- Engagement (35%) ---
    total_msgs = int(player.get("total_messages", 0))
    total_calls = int(player.get("total_calls", 0))
    total_visio = int(player.get("total_visio", 0))
    missions_done = int(player.get("missions_completed", 0))

    eng_score = 0
    eng_score += min(total_msgs / 5, 40)
    channels_used = sum(1 for v in [total_msgs, total_calls, total_visio] if v > 0)
    eng_score += channels_used * 10
    eng_score += min(missions_done * 5, 30)
    engagement = min(round(eng_score), 100)

    # --- Mood (25%) ---
    # Try to get session mood from Redis
    mood = 70  # Default
    try:
        session = gops.rc.get_session(tenant_id)
        if session and session.get("mood"):
            mood_map = {
                "joyeux": 95, "content": 85, "neutre": 70,
                "fatigue": 55, "triste": 40, "anxieux": 35, "en_colere": 30,
            }
            mood = mood_map.get(session["mood"], 70)
    except Exception:
        pass

    # --- Composite ---
    score = round(regularity * 0.40 + engagement * 0.35 + mood * 0.25)

    # --- Trend ---
    old_stability = gops.get_stability(tenant_id)
    old_score = int(old_stability.get("score", score)) if old_stability else score
    if score - old_score > 5:
        trend = "up"
    elif old_score - score > 5:
        trend = "down"
    else:
        trend = "stable"

    gauge = {
        "score": str(score),
        "trend": trend,
        "regularity": str(regularity),
        "engagement": str(engagement),
        "mood": str(mood),
        "updated_at": datetime.utcnow().isoformat(),
    }
    gops.set_stability(tenant_id, gauge)
    # Copier le score dans le player hash pour que le badge stability_90 fonctionne
    gops.set_player_field(tenant_id, "stability_score", str(score))
    return gauge


# =====================================================================
# REWARD COLLECTION
# =====================================================================

async def collect_mission_reward(gops: GamificationRedisOps, tenant_id,
                                 mission_id: str) -> dict:
    """Collect XP reward from a completed mission."""
    mission = gops.get_mission(tenant_id, mission_id)
    if not mission:
        return {"success": False, "error": "Mission introuvable"}
    if mission.get("status") != "completed":
        return {"success": False, "error": "Mission non completee"}
    if mission.get("collected") in ("true", "True", "1"):
        return {"success": False, "error": "Recompense deja collectee"}

    xp_reward = int(mission.get("xp_reward", 0))

    # Award XP directly
    new_xp = gops.increment_player_field(tenant_id, "xp", xp_reward)

    # Mark as collected
    gops.update_mission_field(tenant_id, mission_id, "collected", "true")

    # Check level up
    level_info = get_level_for_xp(new_xp)
    old_level = int(gops.get_player_field(tenant_id, "level") or "1")
    leveled_up = level_info["level"] > old_level

    if leveled_up:
        gops.set_player_field(tenant_id, "level", str(level_info["level"]))
        gops.set_player_field(tenant_id, "title", level_info["title"])
        gops.add_activity(tenant_id, json.dumps({
            "id": str(uuid.uuid4()),
            "type": "level_up",
            "message": f"Niveau {level_info['level']} atteint : {level_info['title']} !",
            "icon": "arrow-up",
            "ts": datetime.utcnow().isoformat(),
            "meta": {"level": level_info["level"], "title": level_info["title"]},
        }))

    # Check badges after XP gain
    new_badges = check_badges(gops, tenant_id)

    # Award stars for mission collection
    award_stars(gops, tenant_id, "mission_completed")

    return {
        "success": True,
        "xp_awarded": xp_reward,
        "new_xp_total": new_xp,
        "leveled_up": leveled_up,
        "new_level": level_info["level"] if leveled_up else None,
        "new_title": level_info["title"] if leveled_up else None,
        "new_badges": new_badges,
    }


# =====================================================================
# STAR ECONOMY
# =====================================================================

def award_stars(gops: GamificationRedisOps, tenant_id, reason: str,
                base_amount: int = None) -> int:
    """Award stars to a player. Returns amount awarded."""
    if base_amount is None:
        base_amount = STAR_REWARDS.get(reason, 0)
    if base_amount <= 0:
        return 0

    # Check x2 bonus
    bonus = gops.get_active_bonus(tenant_id, "bonus_stars2")
    multiplier = 2 if bonus else 1
    amount = base_amount * multiplier

    new_total = gops.increment_player_field(tenant_id, "stars", amount)

    # Activity event for significant gains
    if amount >= 5:
        reason_labels = {
            "daily_login": "connexion du jour",
            "mission_completed": "mission completee",
            "mission_onboarding": "mission decouverte",
            "level_up": "montee de niveau",
            "streak_7": "streak 7 jours",
            "streak_30": "streak 30 jours",
        }
        if reason.startswith("badge_"):
            label = "badge debloque"
        else:
            label = reason_labels.get(reason, reason)
        gops.add_activity(tenant_id, json.dumps({
            "id": str(uuid.uuid4()),
            "type": "stars_earned",
            "message": f"+{amount} etoiles : {label}",
            "icon": "star",
            "ts": datetime.utcnow().isoformat(),
            "meta": {"stars": amount, "reason": reason},
        }))

    return amount


# =====================================================================
# FAMILY XP & LEVEL
# =====================================================================

def award_family_xp(gops: GamificationRedisOps, tenant_id, action: str) -> dict:
    """Award family XP when a family-related action occurs. Returns level info."""
    xp_amount = FAMILY_XP_ACTIONS.get(action, 0)
    if xp_amount <= 0:
        return {"family_xp_gained": 0}

    new_xp = gops.increment_family_xp(tenant_id, xp_amount)

    # Compute family level using FAMILY_LEVELS (which has 3-tuples: xp, title, tier)
    family_levels_2 = [(xp, title) for xp, title, _tier in FAMILY_LEVELS]
    level_info = get_level_for_xp(new_xp, family_levels_2)

    # Check if family leveled up
    fam_data = gops.get_family_level(tenant_id)
    old_level = int(fam_data.get("family_level", "1")) if fam_data else 1
    new_level = level_info["level"]
    tier_idx = min(new_level - 1, len(FAMILY_LEVELS) - 1)
    blason_tier = FAMILY_LEVELS[tier_idx][2]

    gops.set_family_level(tenant_id, {
        "family_xp": str(new_xp),
        "family_level": str(new_level),
        "blason_tier": blason_tier,
        "updated_at": datetime.utcnow().isoformat(),
    })

    leveled_up = new_level > old_level
    if leveled_up:
        tier_name = FAMILY_LEVELS[tier_idx][1]
        gops.add_activity(tenant_id, json.dumps({
            "id": str(uuid.uuid4()),
            "type": "family_level_up",
            "message": f"Famille niveau {new_level} : {tier_name} !",
            "icon": "shield",
            "ts": datetime.utcnow().isoformat(),
            "meta": {"family_level": new_level, "blason_tier": blason_tier},
        }))

    return {
        "family_xp_gained": xp_amount,
        "family_xp_total": new_xp,
        "family_level": new_level,
        "leveled_up": leveled_up,
    }


def buy_shop_item(gops: GamificationRedisOps, tenant_id, item_id: str) -> dict:
    """Purchase a shop item with stars."""
    item = SHOP_ITEMS.get(item_id)
    if not item:
        return {"success": False, "error": "Article inconnu"}

    # Check already owned (non-reusable)
    if not item.get("reusable"):
        owned = gops.get_inventory(tenant_id)
        if item_id in owned:
            return {"success": False, "error": "Deja possede"}

    # Check balance
    stars = int(gops.get_player_field(tenant_id, "stars") or "0")
    if stars < item["price"]:
        return {"success": False, "error": "Pas assez d'etoiles",
                "stars": stars, "price": item["price"]}

    # Debit stars
    gops.increment_player_field(tenant_id, "stars", -item["price"])
    new_balance = stars - item["price"]

    # Add to inventory
    now = datetime.utcnow().isoformat()
    gops.add_to_inventory(tenant_id, item_id, {
        "purchased_at": now,
        "category": item["category"],
    })

    # Activate bonus with TTL if applicable
    if item.get("duration_hours"):
        ttl = item["duration_hours"] * 3600
        gops.set_active_bonus(tenant_id, item_id, {"activated_at": now}, ttl)

    # Activity event
    gops.add_activity(tenant_id, json.dumps({
        "id": str(uuid.uuid4()),
        "type": "shop_purchase",
        "message": f"Achat : {item['name']} (-{item['price']} etoiles)",
        "icon": "shopping-bag",
        "ts": now,
        "meta": {"item_id": item_id, "price": item["price"]},
    }))

    return {
        "success": True,
        "stars_spent": item["price"],
        "new_balance": new_balance,
        "item": item_id,
    }


# =====================================================================
# XP MIGRATION V1 -> V2
# =====================================================================

def migrate_xp_curve(gops: GamificationRedisOps, tenant_id) -> bool:
    """Migre un joueur de la courbe XP V1 vers V2.

    Regle : aucun joueur n'est retrograde. Si son ancien niveau est
    superieur a celui que son XP donnerait avec la nouvelle courbe,
    on booste son XP au seuil du niveau conserve.
    Retourne True si une migration a eu lieu.
    """
    player = gops.get_player(tenant_id)
    if not player:
        return False
    if player.get("xp_v2_migrated") == "true":
        return False

    old_level = int(player.get("level", 1))
    current_xp = int(player.get("xp", 0))

    # Niveau avec la nouvelle courbe
    new_level_info = get_level_for_xp(current_xp, CLIENT_LEVELS)
    new_level = new_level_info["level"]

    if old_level > new_level:
        # Booste l'XP au seuil du niveau conserve
        target_xp = CLIENT_LEVELS[old_level - 1][0]
        xp_boost = target_xp - current_xp
        if xp_boost > 0:
            gops.increment_player_field(tenant_id, "xp", xp_boost)
            gops.add_activity(tenant_id, json.dumps({
                "id": str(uuid.uuid4()),
                "type": "migration",
                "message": f"Migration XP : +{xp_boost} XP (maintien niveau {old_level})",
                "icon": "refresh-cw",
                "ts": datetime.utcnow().isoformat(),
                "meta": {"xp_boost": xp_boost, "preserved_level": old_level},
            }))
        # Mettre a jour le titre (peut avoir change entre V1 et V2)
        gops.set_player_field(tenant_id, "title", CLIENT_LEVELS[old_level - 1][1])
    else:
        # Le joueur est au bon niveau ou plus haut, juste mettre a jour le titre
        gops.set_player_field(tenant_id, "level", str(new_level))
        gops.set_player_field(tenant_id, "title", new_level_info["title"])

    gops.set_player_field(tenant_id, "xp_v2_migrated", "true")
    logger.info(f"Migration XP V2 tenant {tenant_id}: level {old_level} -> {max(old_level, new_level)}")
    return True
