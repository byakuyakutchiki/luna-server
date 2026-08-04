"""Constantes et helpers pour les salons famille."""

import hashlib
import hmac
import json
import random
import uuid
from datetime import datetime

# TTLs
TTL_ROOM = 2 * 60 * 60          # 2 heures
TTL_ROOM_MESSAGES = 2 * 60 * 60  # suit la room
TTL_DM_ROOM = 30 * 24 * 60 * 60  # 30 jours pour les DMs
MAX_ROOM_MESSAGES = 200
MAX_PARTICIPANTS = 10
MAX_DM_PARTICIPANTS = 2

# Types de salons
ROOM_TYPES = ["chat", "cinema", "karaoke", "games", "dm"]

# Types de jeux
GAME_TYPES = ["quiz", "morpion", "memory"]

# Emojis pour Memory (8 paires)
MEMORY_EMOJIS = ["🌙", "⭐", "🏠", "🌸", "🎵", "💜", "🦋", "🔮"]

# Réactions rapides
QUICK_REACTIONS = ["❤️", "😂", "👏", "🎉", "😮", "🔥"]

# ─── Quiz prédéfinis ────────────────────────────────────────────────────────

QUIZ_SETS = [
    {
        "name": "Culture Générale",
        "questions": [
            {"q": "Quelle planète est la plus proche du Soleil ?", "choices": ["Venus", "Mercure", "Mars", "Terre"], "answer": 1},
            {"q": "Combien de continents y a-t-il ?", "choices": ["5", "6", "7", "8"], "answer": 2},
            {"q": "Quel animal est le plus rapide ?", "choices": ["Lion", "Guépard", "Aigle", "Faucon pèlerin"], "answer": 3},
            {"q": "En quelle année l'homme a marché sur la Lune ?", "choices": ["1965", "1969", "1972", "1967"], "answer": 1},
            {"q": "Quel est le plus grand océan ?", "choices": ["Atlantique", "Indien", "Arctique", "Pacifique"], "answer": 3},
        ],
    },
    {
        "name": "Devinettes",
        "questions": [
            {"q": "Je suis toujours devant toi mais tu ne peux jamais me voir. Qui suis-je ?", "choices": ["L'ombre", "Le futur", "Le vent", "Le soleil"], "answer": 1},
            {"q": "Plus je sèche, plus je suis mouillée. Qui suis-je ?", "choices": ["L'éponge", "La serviette", "La pluie", "La rivière"], "answer": 1},
            {"q": "J'ai des villes mais pas de maisons. Qui suis-je ?", "choices": ["Un pays", "Une carte", "Un rêve", "Un livre"], "answer": 1},
            {"q": "Je monte et je descends sans bouger. Qui suis-je ?", "choices": ["L'ascenseur", "La température", "L'escalier", "Le soleil"], "answer": 1},
            {"q": "On me casse avant de m'utiliser. Qui suis-je ?", "choices": ["Un verre", "Un œuf", "Un code", "Un silence"], "answer": 1},
        ],
    },
    {
        "name": "Sciences & Nature",
        "questions": [
            {"q": "De quoi est composée l'eau ?", "choices": ["H2O", "CO2", "NaCl", "O2"], "answer": 0},
            {"q": "Quelle est la plus grande forêt du monde ?", "choices": ["Forêt Noire", "Taïga", "Amazonie", "Congo"], "answer": 2},
            {"q": "Combien d'os a le corps humain adulte ?", "choices": ["186", "206", "226", "256"], "answer": 1},
            {"q": "Quel gaz les plantes absorbent-elles ?", "choices": ["Oxygène", "Azote", "CO2", "Hydrogène"], "answer": 2},
            {"q": "Quelle étoile est la plus proche de la Terre ?", "choices": ["Sirius", "Le Soleil", "Proxima", "Polaris"], "answer": 1},
        ],
    },
    {
        "name": "Animaux",
        "questions": [
            {"q": "Quel animal peut dormir debout ?", "choices": ["Vache", "Cheval", "Éléphant", "Girafe"], "answer": 1},
            {"q": "Combien de pattes a une araignée ?", "choices": ["6", "8", "10", "12"], "answer": 1},
            {"q": "Quel est le plus grand animal vivant ?", "choices": ["Éléphant", "Baleine bleue", "Girafe", "Requin baleine"], "answer": 1},
            {"q": "Quel oiseau ne sait pas voler ?", "choices": ["Autruche", "Aigle", "Perroquet", "Albatros"], "answer": 0},
            {"q": "Combien d'estomacs a une vache ?", "choices": ["1", "2", "3", "4"], "answer": 3},
        ],
    },
    {
        "name": "Musique & Cinéma",
        "questions": [
            {"q": "Qui a composé 'La Lettre à Élise' ?", "choices": ["Mozart", "Bach", "Beethoven", "Chopin"], "answer": 2},
            {"q": "Dans quel film dit-on 'Que la Force soit avec toi' ?", "choices": ["Star Trek", "Star Wars", "Dune", "Avatar"], "answer": 1},
            {"q": "Combien de cordes a une guitare classique ?", "choices": ["4", "5", "6", "8"], "answer": 2},
            {"q": "Qui a réalisé Le Roi Lion (1994) ?", "choices": ["Pixar", "DreamWorks", "Disney", "Warner"], "answer": 2},
            {"q": "Quel instrument a 88 touches ?", "choices": ["Orgue", "Piano", "Accordéon", "Synthétiseur"], "answer": 1},
        ],
    },
]

# ─── Helpers ────────────────────────────────────────────────────────────────


def generate_room_id() -> str:
    # FIX-SALON-ROOMID-ENTROPY-P3-001 : room_id sert de secret de facto pour le lien
    # "ami" cross-tenant (partage sans SMS) -- 24 caracteres hex (96 bits) au lieu de 12
    # (48 bits).
    return uuid.uuid4().hex + uuid.uuid4().hex[:8]


def generate_member_token(phone: str, tenant_id: int, secret: str) -> str:
    """HMAC token pour authentifier un membre famille dans un salon."""
    msg = f"{phone}:{tenant_id}".encode()
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()[:32]


def verify_member_token(phone: str, tenant_id: int, token: str, secret: str) -> bool:
    expected = generate_member_token(phone, tenant_id, secret)
    return hmac.compare_digest(expected, token)


def new_room_data(name: str, room_type: str, host_phone: str, host_name: str,
                  tenant_id: int) -> dict:
    now = datetime.utcnow().isoformat()
    return {
        "id": generate_room_id(),
        "tenant_id": str(tenant_id),
        "name": name,
        "type": room_type,
        "host_phone": host_phone,
        "host_name": host_name,
        "status": "open",
        "max_participants": str(MAX_PARTICIPANTS),
        "created_at": now,
        "updated_at": now,
        "youtube_url": "",
        "youtube_title": "",
        "playback_state": "paused",
        "playback_time": "0",
        "game_type": "",
        "game_state": "{}",
    }


def new_morpion_state(player_x: str, player_o: str) -> dict:
    return {
        "game_type": "morpion",
        "board": [0] * 9,
        "player_x": player_x,
        "player_o": player_o,
        "turn": player_x,
        "status": "playing",
        "winner": None,
    }


def new_memory_state(players: list) -> dict:
    cards = list(range(8)) * 2
    random.shuffle(cards)
    return {
        "game_type": "memory",
        "cards": cards,
        "revealed": [False] * 16,
        "matched": [False] * 16,
        "current_turn": players[0] if players else "",
        "turn_order": players,
        "scores": {p: 0 for p in players},
        "selected": [],
        "status": "playing",
    }


def new_quiz_state(quiz_set_index: int = 0, players: list = None) -> dict:
    qs = QUIZ_SETS[quiz_set_index % len(QUIZ_SETS)]
    return {
        "game_type": "quiz",
        "quiz_name": qs["name"],
        "status": "waiting",
        "current_question": 0,
        "total_questions": len(qs["questions"]),
        "questions": qs["questions"],
        "scores": {p: 0 for p in (players or [])},
        "answers": {},
        "timer": 15,
    }


def check_morpion_winner(board: list) -> int:
    """Returns 0 (no winner), 1 (X wins), 2 (O wins), -1 (draw)."""
    wins = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
    for a, b, c in wins:
        if board[a] == board[b] == board[c] != 0:
            return board[a]
    if 0 not in board:
        return -1
    return 0
