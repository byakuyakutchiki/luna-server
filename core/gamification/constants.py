"""Constantes de gamification : niveaux, badges, missions, tables XP."""

# =====================================================================
# NIVEAUX
# =====================================================================

# (xp_threshold, titre) — V2 courbe exponentielle (fev 2026)
CLIENT_LEVELS = [
    (0, "Nouveau Venu"),
    (80, "Curieux"),
    (250, "Habitue"),
    (600, "Compagnon"),
    (1200, "Ami Fidele"),
    (2500, "Confident"),
    (5000, "Pilier"),
    (8000, "Sage"),
    (12000, "Legendaire"),
    (18000, "Etoile de Luna"),
]

# Anciens seuils V1 — reference pour migration joueurs existants
CLIENT_LEVELS_V1 = [
    (0, "Nouveau Venu"),
    (50, "Curieux"),
    (150, "Habitue"),
    (350, "Compagnon"),
    (600, "Ami Fidele"),
    (1000, "Confident"),
    (1500, "Pilier"),
    (2200, "Sage"),
    (3000, "Legendaire"),
    (4000, "Etoile de Luna"),
]

ADMIN_LEVELS = [
    (0, "Debutant"),
    (50, "Apprenti"),
    (150, "Operateur"),
    (350, "Gestionnaire"),
    (600, "Professionnel"),
    (1000, "Operateur Avise"),
    (1500, "Expert"),
    (2200, "Maitre"),
    (3000, "Visionnaire"),
    (4000, "Legende YAWatch"),
]

# =====================================================================
# XP PAR ACTION
# =====================================================================

# {action_key: {"xp": points, "daily_cap_count": max_actions_per_day}}
XP_ACTIONS = {
    "chat_message":       {"xp": 2,  "daily_cap_count": 20},
    "voice_call":         {"xp": 15, "daily_cap_count": 3},
    "visio_session":      {"xp": 25, "daily_cap_count": 2},
    "profile_update":     {"xp": 5,  "daily_cap_count": 10},
    "add_contact":        {"xp": 20, "daily_cap_count": 1},
    "create_instruction": {"xp": 10, "daily_cap_count": 5},
    "create_note":        {"xp": 5,  "daily_cap_count": 5},
    "daily_login":        {"xp": 10, "daily_cap_count": 1},
    # Family Pack
    "family_setup":           {"xp": 30, "daily_cap_count": 1},
    "family_member_added":    {"xp": 20, "daily_cap_count": 3},
    "family_member_verified": {"xp": 15, "daily_cap_count": 3},
    "family_message_sent":    {"xp": 3,  "daily_cap_count": 10},
    "escalation_rule_created":{"xp": 25, "daily_cap_count": 2},
    "family_sos":             {"xp": 5,  "daily_cap_count": 1},
    # Salons Famille
    "room_created":           {"xp": 10, "daily_cap_count": 3},
    "room_message_sent":      {"xp": 1,  "daily_cap_count": 20},
    "game_played":            {"xp": 5,  "daily_cap_count": 5},
    "game_won":               {"xp": 10, "daily_cap_count": 3},
    # Social
    "friend_added":           {"xp": 15, "daily_cap_count": 3},
    "dm_message_sent":        {"xp": 1,  "daily_cap_count": 15},
    "profile_customized":     {"xp": 10, "daily_cap_count": 1},
}

ADMIN_XP_ACTIONS = {
    "first_client":             {"xp": 100, "daily_cap_count": 1},
    "new_client":               {"xp": 50,  "daily_cap_count": 5},
    "client_level_5":           {"xp": 30,  "daily_cap_count": 10},
    "client_level_10":          {"xp": 50,  "daily_cap_count": 10},
    "revenue_milestone":        {"xp": 100, "daily_cap_count": 1},
    "all_services_healthy_7d":  {"xp": 50,  "daily_cap_count": 1},
    "alert_resolved":           {"xp": 15,  "daily_cap_count": 10},
}

# =====================================================================
# BADGES CLIENT (20 badges, 5 categories)
# =====================================================================

# Chaque badge : id, name, description, category, icon, rarity, condition(player_dict) -> bool
ALL_CLIENT_BADGES = {
    # --- Decouverte ---
    "first_chat": {
        "name": "Premier Mot",
        "description": "Envoie ton premier message a Luna",
        "category": "decouverte",
        "icon": "message-circle",
        "rarity": "common",
        "condition": lambda p: int(p.get("total_messages", 0)) >= 1,
    },
    "profile_complete": {
        "name": "Carte d'Identite",
        "description": "Remplis au moins 10 champs de ton profil",
        "category": "decouverte",
        "icon": "user-check",
        "rarity": "common",
        "condition": lambda p: int(p.get("profile_fields", 0)) >= 10,
    },
    "first_contact": {
        "name": "Main Tendue",
        "description": "Ajoute ton premier contact de confiance",
        "category": "decouverte",
        "icon": "users",
        "rarity": "common",
        "condition": lambda p: int(p.get("total_contacts", 0)) >= 1,
    },
    "first_call": {
        "name": "Premiere Voix",
        "description": "Passe ton premier appel vocal avec Luna",
        "category": "decouverte",
        "icon": "phone",
        "rarity": "common",
        "condition": lambda p: int(p.get("total_calls", 0)) >= 1,
    },
    # --- Social ---
    "three_contacts": {
        "name": "Entourage",
        "description": "Ajoute 3 contacts de confiance",
        "category": "social",
        "icon": "heart",
        "rarity": "rare",
        "condition": lambda p: int(p.get("total_contacts", 0)) >= 3,
    },
    "bavard": {
        "name": "Bavard",
        "description": "Envoie 50 messages a Luna",
        "category": "social",
        "icon": "message-square",
        "rarity": "common",
        "condition": lambda p: int(p.get("total_messages", 0)) >= 50,
    },
    "conteur": {
        "name": "Conteur",
        "description": "Envoie 200 messages a Luna",
        "category": "social",
        "icon": "book-open",
        "rarity": "rare",
        "condition": lambda p: int(p.get("total_messages", 0)) >= 200,
    },
    "mille_mots": {
        "name": "Mille Mots",
        "description": "Envoie 500 messages a Luna",
        "category": "social",
        "icon": "feather",
        "rarity": "epic",
        "condition": lambda p: int(p.get("total_messages", 0)) >= 500,
    },
    # --- Fidelite ---
    "week_streak": {
        "name": "Semaine Fidele",
        "description": "Connecte-toi 7 jours de suite",
        "category": "fidelite",
        "icon": "flame",
        "rarity": "rare",
        "condition": lambda p: int(p.get("streak_best", 0)) >= 7,
    },
    "two_week_streak": {
        "name": "Deux Semaines",
        "description": "Connecte-toi 14 jours de suite",
        "category": "fidelite",
        "icon": "flame",
        "rarity": "rare",
        "condition": lambda p: int(p.get("streak_best", 0)) >= 14,
    },
    "month_streak": {
        "name": "Mois Constant",
        "description": "Connecte-toi 30 jours de suite",
        "category": "fidelite",
        "icon": "award",
        "rarity": "epic",
        "condition": lambda p: int(p.get("streak_best", 0)) >= 30,
    },
    "regular": {
        "name": "Regulier",
        "description": "Sois actif pendant 30 jours au total",
        "category": "fidelite",
        "icon": "calendar",
        "rarity": "rare",
        "condition": lambda p: int(p.get("days_active", 0)) >= 30,
    },
    # --- Exploration ---
    "first_instruction": {
        "name": "Organisateur",
        "description": "Cree ta premiere instruction pour Luna",
        "category": "exploration",
        "icon": "clipboard",
        "rarity": "common",
        "condition": lambda p: int(p.get("total_instructions", 0)) >= 1,
    },
    "first_note": {
        "name": "Archiviste",
        "description": "Cree ta premiere note",
        "category": "exploration",
        "icon": "file-text",
        "rarity": "common",
        "condition": lambda p: int(p.get("total_notes", 0)) >= 1,
    },
    "explorateur": {
        "name": "Explorateur",
        "description": "Visite tous les onglets de l'application",
        "category": "exploration",
        "icon": "compass",
        "rarity": "rare",
        "condition": lambda p: len(p.get("tabs_visited", "").split(",")) >= 7 if p.get("tabs_visited") else False,
    },
    "multi_canal": {
        "name": "Multi-Canal",
        "description": "Utilise le chat, la voix et la visio",
        "category": "exploration",
        "icon": "layers",
        "rarity": "epic",
        "condition": lambda p: (
            int(p.get("total_messages", 0)) >= 1
            and int(p.get("total_calls", 0)) >= 1
            and int(p.get("total_visio", 0)) >= 1
        ),
    },
    # --- Famille ---
    "family_pioneer": {
        "name": "Pionnier Famille",
        "description": "Cree ton premier groupe familial",
        "category": "social",
        "icon": "home",
        "rarity": "common",
        "condition": lambda p: int(p.get("total_family_groups", 0)) >= 1,
    },
    "family_builder": {
        "name": "Batisseur",
        "description": "Ajoute 3 membres a ta famille",
        "category": "social",
        "icon": "users",
        "rarity": "rare",
        "condition": lambda p: int(p.get("total_family_members", 0)) >= 3,
    },
    "family_protector": {
        "name": "Protecteur",
        "description": "Cree une regle d'escalade pour proteger tes proches",
        "category": "exploration",
        "icon": "shield",
        "rarity": "rare",
        "condition": lambda p: int(p.get("total_escalation_rules", 0)) >= 1,
    },
    "family_communicator": {
        "name": "Communicant",
        "description": "Envoie 10 messages a ta famille via Luna",
        "category": "social",
        "icon": "send",
        "rarity": "rare",
        "condition": lambda p: int(p.get("total_family_messages", 0)) >= 10,
    },
    "first_visio": {
        "name": "Face a Face",
        "description": "Fais ta premiere session visio avec Luna",
        "category": "decouverte",
        "icon": "video",
        "rarity": "common",
        "condition": lambda p: int(p.get("total_visio", 0)) >= 1,
    },
    # --- Maitrise ---
    "level_5": {
        "name": "Ami Fidele",
        "description": "Atteins le niveau 5",
        "category": "maitrise",
        "icon": "star",
        "rarity": "rare",
        "condition": lambda p: int(p.get("level", 1)) >= 5,
    },
    "level_10": {
        "name": "Etoile de Luna",
        "description": "Atteins le niveau 10",
        "category": "maitrise",
        "icon": "crown",
        "rarity": "legendary",
        "condition": lambda p: int(p.get("level", 1)) >= 10,
    },
    "centenaire": {
        "name": "Centenaire",
        "description": "Reste actif pendant 100 jours",
        "category": "maitrise",
        "icon": "shield",
        "rarity": "epic",
        "condition": lambda p: int(p.get("days_active", 0)) >= 100,
    },
    "stability_90": {
        "name": "Roc Solide",
        "description": "Obtiens un score de stabilite superieur a 90",
        "category": "maitrise",
        "icon": "anchor",
        "rarity": "epic",
        "condition": lambda p: int(p.get("stability_score", 0)) >= 90,
    },
    # --- Social ---
    "first_dm": {
        "name": "Premier Message",
        "description": "Envoie ton premier message prive a un ami",
        "category": "social",
        "icon": "mail",
        "rarity": "common",
        "condition": lambda p: int(p.get("total_dm_messages", 0)) >= 1,
    },
    "social_butterfly": {
        "name": "Papillon Social",
        "description": "Ajoute 5 amis a ton reseau",
        "category": "social",
        "icon": "smile",
        "rarity": "rare",
        "condition": lambda p: int(p.get("total_friends", 0)) >= 5,
    },
    "popular": {
        "name": "Populaire",
        "description": "Ajoute 10 amis a ton reseau",
        "category": "social",
        "icon": "star",
        "rarity": "epic",
        "condition": lambda p: int(p.get("total_friends", 0)) >= 10,
    },
}

# =====================================================================
# BADGES EXPLOITANT (8 badges)
# =====================================================================

ALL_ADMIN_BADGES = {
    "first_client": {
        "name": "Premier Pas",
        "description": "Enregistre ton premier client",
        "category": "croissance",
        "icon": "user-plus",
        "rarity": "common",
        "condition": lambda p: int(p.get("clients_total", 0)) >= 1,
    },
    "five_clients": {
        "name": "Equipe Formee",
        "description": "Atteins 5 clients enregistres",
        "category": "croissance",
        "icon": "users",
        "rarity": "rare",
        "condition": lambda p: int(p.get("clients_total", 0)) >= 5,
    },
    "ten_clients": {
        "name": "Leader",
        "description": "Atteins 10 clients",
        "category": "croissance",
        "icon": "trending-up",
        "rarity": "epic",
        "condition": lambda p: int(p.get("clients_total", 0)) >= 10,
    },
    "revenue_500": {
        "name": "Premier Cap",
        "description": "Atteins 500 EUR de CA mensuel",
        "category": "business",
        "icon": "dollar-sign",
        "rarity": "rare",
        "condition": lambda p: float(p.get("revenue_monthly", 0)) >= 500,
    },
    "revenue_2000": {
        "name": "Croissance",
        "description": "Atteins 2000 EUR de CA mensuel",
        "category": "business",
        "icon": "bar-chart",
        "rarity": "epic",
        "condition": lambda p: float(p.get("revenue_monthly", 0)) >= 2000,
    },
    "all_services_ok": {
        "name": "Infrastructure Solide",
        "description": "Tous les services sont operationnels",
        "category": "technique",
        "icon": "server",
        "rarity": "rare",
        "condition": lambda p: p.get("all_services_healthy") == "true",
    },
    "client_level_10": {
        "name": "Mentor",
        "description": "Un de tes clients atteint le niveau 10",
        "category": "mentorat",
        "icon": "award",
        "rarity": "legendary",
        "condition": lambda p: p.get("has_client_level_10") == "true",
    },
    "zero_alerts_week": {
        "name": "Zen Master",
        "description": "Aucune alerte pendant 7 jours",
        "category": "technique",
        "icon": "sun",
        "rarity": "epic",
        "condition": lambda p: p.get("zero_alerts_7d") == "true",
    },
}

# =====================================================================
# MISSIONS CLIENT
# =====================================================================

ONBOARDING_MISSIONS = [
    {
        "type": "onboarding_profile",
        "title": "Dis-moi qui tu es",
        "description": "Complete 5 champs de ton profil pour que Luna te connaisse mieux",
        "category": "onboarding",
        "target": 5,
        "xp_reward": 50,
        "action_type": "profile_update",
        "counter_field": "profile_fields",
    },
    {
        "type": "onboarding_chat",
        "title": "Premier echange",
        "description": "Envoie 5 messages a Luna",
        "category": "onboarding",
        "target": 5,
        "xp_reward": 30,
        "action_type": "chat_message",
        "counter_field": "total_messages",
    },
    {
        "type": "onboarding_contact",
        "title": "Ton cercle",
        "description": "Ajoute 1 contact de confiance",
        "category": "onboarding",
        "target": 1,
        "xp_reward": 40,
        "action_type": "add_contact",
        "counter_field": "total_contacts",
    },
]

RECURRING_MISSIONS = [
    {
        "type": "weekly_active",
        "title": "Semaine Active",
        "description": "Discute avec Luna 5 jours differents cette semaine",
        "category": "fidelite",
        "target": 5,
        "xp_reward": 60,
        "action_type": "daily_login",
        "counter_field": "streak_days",
    },
    {
        "type": "call_luna",
        "title": "Appelle Luna",
        "description": "Passe un appel vocal avec Luna",
        "category": "exploration",
        "target": 1,
        "xp_reward": 40,
        "action_type": "voice_call",
        "counter_field": "total_calls",
    },
    {
        "type": "new_instruction",
        "title": "Donne une consigne",
        "description": "Cree une nouvelle instruction pour Luna",
        "category": "exploration",
        "target": 1,
        "xp_reward": 30,
        "action_type": "create_instruction",
        "counter_field": "total_instructions",
    },
    {
        "type": "take_note",
        "title": "Note du jour",
        "description": "Cree une note",
        "category": "exploration",
        "target": 1,
        "xp_reward": 20,
        "action_type": "create_note",
        "counter_field": "total_notes",
    },
    {
        "type": "chat_10",
        "title": "Conversation",
        "description": "Envoie 10 messages aujourd'hui",
        "category": "social",
        "target": 10,
        "xp_reward": 35,
        "action_type": "chat_message",
        "counter_field": "total_messages",
    },
    {
        "type": "profile_deep",
        "title": "Profil complet",
        "description": "Remplis 15 champs de profil",
        "category": "decouverte",
        "target": 15,
        "xp_reward": 80,
        "action_type": "profile_update",
        "counter_field": "profile_fields",
    },
    {
        "type": "three_calls",
        "title": "Habitue vocal",
        "description": "Passe 3 appels vocaux",
        "category": "social",
        "target": 3,
        "xp_reward": 60,
        "action_type": "voice_call",
        "counter_field": "total_calls",
    },
]

ADMIN_MISSIONS = [
    {
        "type": "first_registration",
        "title": "Embarque ton premier client",
        "description": "Un client s'inscrit sur ta plateforme",
        "category": "croissance",
        "target": 1,
        "xp_reward": 100,
        "action_type": "new_client",
        "counter_field": "clients_total",
    },
    {
        "type": "diversify_plans",
        "title": "Diversifie les plans",
        "description": "Aie des clients sur au moins 2 forfaits differents",
        "category": "business",
        "target": 2,
        "xp_reward": 80,
        "action_type": "plan_diversity",
        "counter_field": "plan_types_count",
    },
    {
        "type": "services_health",
        "title": "Sante du serveur",
        "description": "Tous les services sont verts pendant 3 jours",
        "category": "technique",
        "target": 3,
        "xp_reward": 60,
        "action_type": "services_healthy",
        "counter_field": "healthy_days",
    },
    {
        "type": "five_clients",
        "title": "Croissance",
        "description": "Atteins 5 clients actifs",
        "category": "croissance",
        "target": 5,
        "xp_reward": 120,
        "action_type": "new_client",
        "counter_field": "clients_total",
    },
    {
        "type": "revenue_target",
        "title": "Objectif CA",
        "description": "Atteins 500 EUR de CA mensuel",
        "category": "business",
        "target": 500,
        "xp_reward": 150,
        "action_type": "revenue_milestone",
        "counter_field": "revenue_monthly",
    },
]

# =====================================================================
# CATEGORIES (pour le frontend)
# =====================================================================

BADGE_CATEGORIES = {
    "decouverte":  {"label": "Decouverte",  "color": "#a78bfa"},
    "social":      {"label": "Social",      "color": "#4ade80"},
    "fidelite":    {"label": "Fidelite",    "color": "#fbbf24"},
    "exploration": {"label": "Exploration", "color": "#60a5fa"},
    "maitrise":    {"label": "Maitrise",    "color": "#f87171"},
    "croissance":  {"label": "Croissance",  "color": "#34d399"},
    "business":    {"label": "Business",    "color": "#fbbf24"},
    "technique":   {"label": "Technique",   "color": "#60a5fa"},
    "mentorat":    {"label": "Mentorat",    "color": "#f472b6"},
}

RARITY_COLORS = {
    "common":    "#9ca3af",
    "rare":      "#60a5fa",
    "epic":      "#a78bfa",
    "legendary": "#fbbf24",
}

# =====================================================================
# ETOILES (monnaie virtuelle)
# =====================================================================

STAR_REWARDS = {
    "daily_login":        2,
    "mission_completed":  5,
    "mission_onboarding": 10,
    "badge_common":       5,
    "badge_rare":         10,
    "badge_epic":         20,
    "badge_legendary":    50,
    "streak_7":           15,
    "streak_30":          50,
    "level_up":           20,
}

# =====================================================================
# BOUTIQUE
# =====================================================================

SHOP_ITEMS = {
    # --- Decorations village ---
    "deco_fountain":       {"name": "Fontaine Lumineuse",    "category": "decoration", "price": 40,  "icon": "\U0001f4a7", "description": "Une fontaine magique qui brille la nuit"},
    "deco_bench":          {"name": "Banc du Parc",         "category": "decoration", "price": 60,  "icon": "\U0001fa91", "description": "Un banc paisible pres du chemin"},
    "deco_flowers":        {"name": "Parterre de Roses",    "category": "decoration", "price": 25,  "icon": "\U0001f339", "description": "Des roses violettes le long du chemin"},
    "deco_lanterns":       {"name": "Lanternes Flottantes", "category": "decoration", "price": 50,  "icon": "\U0001f3ee", "description": "Lanternes magiques dans le ciel"},
    # --- Tenues Luna ---
    "outfit_winter":       {"name": "Tenue d'Hiver",        "category": "tenue",      "price": 80,  "icon": "\U0001f9e5", "description": "Manteau chaud et bonnet etoile"},
    "outfit_star":         {"name": "Cape Etoilee",          "category": "tenue",      "price": 120, "icon": "\u2728",     "description": "Cape scintillante constellee d'etoiles"},
    "outfit_flower":       {"name": "Couronne de Fleurs",    "category": "tenue",      "price": 60,  "icon": "\U0001f338", "description": "Couronne de fleurs dans les cheveux"},
    "outfit_festive":      {"name": "Robe de Fete",          "category": "tenue",      "price": 100, "icon": "\U0001f389", "description": "Robe de gala violette et doree"},
    # --- Bonus actifs (temporaire, reachetable) ---
    "bonus_xp2":           {"name": "XP x2 (24h)",          "category": "bonus",      "price": 35,  "icon": "\u26a1",     "description": "Double les XP pendant 24 heures",               "duration_hours": 24, "reusable": True},
    "bonus_streak_shield": {"name": "Bouclier Streak",       "category": "bonus",      "price": 45,  "icon": "\U0001f6e1", "description": "Protege ton streak pendant 1 jour de grace",    "duration_hours": 48, "reusable": True},
    "bonus_mission":       {"name": "Mission Bonus",         "category": "bonus",      "price": 30,  "icon": "\U0001f3af", "description": "Debloque une 4eme mission active temporairement","duration_hours": 72, "reusable": True},
    "bonus_stars2":        {"name": "Etoiles x2 (24h)",     "category": "bonus",      "price": 50,  "icon": "\U0001f31f", "description": "Double les etoiles gagnees pendant 24h",        "duration_hours": 24, "reusable": True},
    # --- Ameliorations batiments (permanent, 1x) ---
    "upgrade_maison":      {"name": "Etage Maison",          "category": "upgrade",    "price": 150, "icon": "\U0001f3e0", "description": "Ajoute un etage a la Maison de Luna"},
    "upgrade_jardin":      {"name": "Serre Magique",         "category": "upgrade",    "price": 120, "icon": "\U0001f33f", "description": "Serre lumineuse dans le Jardin"},
    "upgrade_biblio":      {"name": "Tour d'Horloge",        "category": "upgrade",    "price": 130, "icon": "\U0001f550", "description": "Tour supplementaire pour la Bibliotheque"},
    "upgrade_obs":         {"name": "Telescope Geant",       "category": "upgrade",    "price": 200, "icon": "\U0001f52d", "description": "Telescope imposant sur l'Observatoire"},
    # --- Premium (argent reel via Stripe) ---
    "premium_aurora_deco":  {"name": "Aurore Boreale",       "category": "premium",    "price": 0, "icon": "\U0001f30c", "description": "Aurore boreale animee dans le ciel du village",    "stripe_price_env": "STRIPE_PRICE_WORLD_AURORA"},
    "premium_luna_wings":   {"name": "Ailes de Luna",        "category": "premium",    "price": 0, "icon": "\U0001fabd", "description": "Ailes scintillantes pour Luna",                    "stripe_price_env": "STRIPE_PRICE_WORLD_WINGS"},
    "premium_crystal_tree": {"name": "Arbre de Cristal",     "category": "premium",    "price": 0, "icon": "\U0001fab7", "description": "Arbre magique en cristal lumineux",                "stripe_price_env": "STRIPE_PRICE_WORLD_CRYSTAL"},
    "premium_golden_path":  {"name": "Chemin Dore",          "category": "premium",    "price": 0, "icon": "\u2728",     "description": "Chemin pave d'or scintillant dans le village",     "stripe_price_env": "STRIPE_PRICE_WORLD_PATH"},
    # --- Cadres Profil ---
    "frame_simple":  {"name": "Cadre Violet",    "category": "cadre", "price": 30,  "icon": "\U0001f5bc", "description": "Cadre violet elegant pour votre avatar"},
    "frame_floral":  {"name": "Cadre Floral",    "category": "cadre", "price": 50,  "icon": "\U0001f33a", "description": "Couronne de fleurs autour du profil"},
    "frame_golden":  {"name": "Cadre Dore",      "category": "cadre", "price": 70,  "icon": "\U0001f451", "description": "Cadre orne d'or etincelant"},
    "frame_stars":   {"name": "Cadre Etoile",    "category": "cadre", "price": 90,  "icon": "\u2b50",     "description": "Cadre parseme d'etoiles scintillantes"},
    "frame_diamond": {"name": "Cadre Diamant",   "category": "cadre", "price": 150, "icon": "\U0001f48e", "description": "Cadre prestige diamants et lumiere"},
    "frame_crown":   {"name": "Cadre Couronne", "category": "cadre", "price": 0,   "icon": "\U0001f451", "description": "Cadre exclusif des maitres du Palais de Luna"},
    # --- World 2 Decorations ---
    "w2_deco_waterfall":  {"name": "Cascade Cristal",    "category": "decoration", "price": 80,  "icon": "\U0001f4a7", "description": "Cascade scintillante sur la montagne"},
    "w2_deco_crystal":    {"name": "Cristal Geant",      "category": "decoration", "price": 100, "icon": "\U0001f48e", "description": "Cristal lumineux plante dans le sol"},
    "w2_deco_rainbow":    {"name": "Arc-en-Ciel",        "category": "decoration", "price": 120, "icon": "\U0001f308", "description": "Arc-en-ciel permanent au-dessus du village"},
    "w2_deco_aurora":     {"name": "Voile Celeste",      "category": "decoration", "price": 90,  "icon": "\U0001f30c", "description": "Voile d'aurore dansante dans le ciel"},
    # --- World 2 Tenues avancees ---
    "outfit_celestial":   {"name": "Tenue Celeste",      "category": "tenue",      "price": 150, "icon": "\u2728",     "description": "Vetements tisses de lumiere stellaire"},
    "outfit_royal":       {"name": "Tenue Royale",       "category": "tenue",      "price": 200, "icon": "\U0001f451", "description": "Parure royale digne du Palais de Luna"},
}

SHOP_CATEGORIES = {
    "decoration": {"label": "Decorations",  "color": "#4ade80"},
    "tenue":      {"label": "Tenues Luna",  "color": "#a78bfa"},
    "cadre":      {"label": "Cadres Profil","color": "#f472b6"},
    "bonus":      {"label": "Bonus",        "color": "#fbbf24"},
    "upgrade":    {"label": "Ameliorations","color": "#60a5fa"},
    "premium":    {"label": "Premium",      "color": "#fbbf24"},
}

# =====================================================================
# FAMILY LEVELS & BLASONS
# =====================================================================

# (xp_threshold, title, blason_tier)
FAMILY_LEVELS = [
    (0,   "Nid Naissant",      "nest"),
    (50,  "Foyer Uni",         "bronze"),
    (150, "Clan Solide",       "silver"),
    (350, "Dynastie Radieuse", "gold"),
    (600, "Legende Familiale", "diamond"),
]

FAMILY_XP_ACTIONS = {
    "family_setup":            30,
    "family_member_added":     20,
    "family_member_verified":  15,
    "family_message_sent":     3,
    "escalation_rule_created": 25,
    "family_sos":              5,
    "room_created":            10,
    "room_message_sent":       1,
    "game_played":             3,
    "game_won":                5,
}

FAMILY_BLASON_TIERS = {
    "nest":    {"label": "Nid Naissant",      "primary": "#8a6a42", "accent": "#b87a42", "symbol": "heart"},
    "bronze":  {"label": "Foyer Uni",         "primary": "#cd7f32", "accent": "#e8a040", "symbol": "star"},
    "silver":  {"label": "Clan Solide",       "primary": "#c0c0c0", "accent": "#e8e8e8", "symbol": "shield"},
    "gold":    {"label": "Dynastie Radieuse", "primary": "#ffd700", "accent": "#fff4a3", "symbol": "crown"},
    "diamond": {"label": "Legende Familiale", "primary": "#b9f2ff", "accent": "#e0f7ff", "symbol": "diamond"},
}

# =====================================================================
# WORLD 2 — PROGRESSION POST-NIVEAU 5
# =====================================================================

# Batiments World 2 (debloquage niveaux 6-10)
WORLD2_BUILDINGS = {
    6:  {"id": "atelier",  "name": "Atelier Creatif",    "icon": "palette",      "description": "Personnalise ton monde avec des creations uniques"},
    7:  {"id": "marche",   "name": "Marche aux Etoiles",  "icon": "shopping-bag", "description": "Marche d'echange avance entre souscripteurs"},
    8:  {"id": "temple",   "name": "Temple de Sagesse",   "icon": "book",         "description": "Meditations guidees et reflexions profondes"},
    9:  {"id": "phare",    "name": "Phare Celeste",       "icon": "sun",          "description": "Guide les autres souscripteurs depuis les hauteurs"},
    10: {"id": "palais",   "name": "Palais de Luna",      "icon": "crown",        "description": "Le sommet de ton voyage — residence royale de Luna"},
}

# Seuil : World 2 accessible des le niveau 6
WORLD2_UNLOCK_LEVEL = 6

# Cout en etoiles pour debloquer le World 2 (paiement unique)
WORLD2_STAR_COST = 400

# Remise offres du jour au Marche aux Etoiles
DAILY_DEAL_DISCOUNT = 0.20

# Missions recurrentes World 2 (cibles plus elevees)
WORLD2_RECURRING_MISSIONS = [
    {
        "type": "w2_chat_mastery",
        "title": "Maitre du Dialogue",
        "description": "Envoie 20 messages a Luna aujourd'hui",
        "category": "maitrise",
        "target": 20,
        "xp_reward": 80,
        "action_type": "chat_message",
        "counter_field": "total_messages",
    },
    {
        "type": "w2_social_reach",
        "title": "Reseau Social",
        "description": "Ajoute 5 amis a ton reseau",
        "category": "social",
        "target": 5,
        "xp_reward": 100,
        "action_type": "friend_added",
        "counter_field": "total_friends",
    },
    {
        "type": "w2_call_expert",
        "title": "Expert Vocal",
        "description": "Passe 5 appels vocaux avec Luna",
        "category": "exploration",
        "target": 5,
        "xp_reward": 90,
        "action_type": "voice_call",
        "counter_field": "total_calls",
    },
    {
        "type": "w2_streak_master",
        "title": "Constance Absolue",
        "description": "Connecte-toi 14 jours de suite",
        "category": "fidelite",
        "target": 14,
        "xp_reward": 120,
        "action_type": "daily_login",
        "counter_field": "streak_days",
    },
    {
        "type": "w2_dm_active",
        "title": "Correspondant Assidu",
        "description": "Envoie 20 messages prives a tes amis",
        "category": "social",
        "target": 20,
        "xp_reward": 70,
        "action_type": "dm_message_sent",
        "counter_field": "total_dm_messages",
    },
]
