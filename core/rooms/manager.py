"""WebSocket manager + logique jeux pour les salons famille."""

import json
import logging
import random
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import WebSocket

from .models import (
    QUIZ_SETS, MEMORY_EMOJIS,
    new_morpion_state, new_memory_state, new_quiz_state,
    check_morpion_winner,
)

logger = logging.getLogger(__name__)


def _get_sender_level(room_ops, tenant_id: int) -> int:
    """Lit le level du joueur depuis Redis (leger, pas de gamification lourde)."""
    try:
        from core.gamification.redis_ops import GamificationRedisOps
        from core.gamification.engine import get_level_for_xp
        gops = GamificationRedisOps(room_ops.rc)
        xp_str = gops.get_player_field(tenant_id, "xp")
        xp = int(xp_str) if xp_str else 0
        return get_level_for_xp(xp)["level"]
    except Exception:
        return 1


class RoomManager:
    """Gère les connexions WebSocket par salon."""

    def __init__(self):
        # {room_id: {phone: WebSocket}}
        self.connections: Dict[str, Dict[str, WebSocket]] = {}

    async def connect(self, room_id: str, phone: str, ws: WebSocket) -> None:
        if room_id not in self.connections:
            self.connections[room_id] = {}
        self.connections[room_id][phone] = ws

    async def disconnect(self, room_id: str, phone: str) -> None:
        if room_id in self.connections:
            self.connections[room_id].pop(phone, None)
            if not self.connections[room_id]:
                del self.connections[room_id]

    async def broadcast(self, room_id: str, message: dict,
                        exclude_phone: str = None) -> None:
        if room_id not in self.connections:
            return
        dead = []
        for phone, ws in self.connections[room_id].items():
            if phone == exclude_phone:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(phone)
        for p in dead:
            self.connections[room_id].pop(p, None)

    async def send_to(self, room_id: str, phone: str, message: dict) -> None:
        if room_id in self.connections and phone in self.connections[room_id]:
            try:
                await self.connections[room_id][phone].send_json(message)
            except Exception:
                pass

    def get_connected_phones(self, room_id: str) -> list:
        if room_id not in self.connections:
            return []
        return list(self.connections[room_id].keys())

    # ═══════════════════════════════════════════════════════════════════════
    # MESSAGE HANDLING
    # ═══════════════════════════════════════════════════════════════════════

    async def handle_message(self, room_id: str, phone: str, name: str,
                             data: dict, room_ops, tenant_id: int,
                             room_data: dict) -> List[str]:
        """Route un message WebSocket entrant vers le bon handler.
        Retourne une liste d'events gamification a declencher."""
        msg_type = data.get("type", "")
        now = datetime.utcnow().isoformat()
        is_host = (room_data.get("host_phone") == phone)
        events: List[str] = []

        if msg_type == "chat":
            content = data.get("content", "").strip()
            if not content or len(content) > 1000:
                return events
            level = _get_sender_level(room_ops, tenant_id)
            msg = {
                "type": "chat",
                "id": uuid.uuid4().hex[:8],
                "from_phone": phone,
                "from": name,
                "content": content,
                "level": level,
                "ts": now,
            }
            room_ops.add_message(tenant_id, room_id, json.dumps(msg))
            await self.broadcast(room_id, msg)
            room_ops.touch_room(tenant_id, room_id)
            events.append("room_message_sent")

        elif msg_type == "typing":
            await self.broadcast(room_id, {
                "type": "typing", "from": name, "from_phone": phone,
            }, exclude_phone=phone)

        elif msg_type == "reaction":
            emoji = data.get("emoji", "❤️")
            await self.broadcast(room_id, {
                "type": "reaction", "from": name, "emoji": emoji, "ts": now,
            })

        # ── Cinema / Karaoke controls (host only) ──
        elif msg_type == "youtube_set" and is_host:
            url = data.get("url", "").strip()
            title = data.get("title", "")
            room_ops.update_room(tenant_id, room_id, {
                "youtube_url": url, "youtube_title": title,
                "playback_state": "paused", "playback_time": "0",
            })
            await self.broadcast(room_id, {
                "type": "youtube_sync", "url": url, "title": title,
                "state": "paused", "time": 0,
            })

        elif msg_type == "youtube_play" and is_host:
            t = data.get("time", 0)
            room_ops.update_room(tenant_id, room_id, {
                "playback_state": "playing", "playback_time": str(t),
            })
            await self.broadcast(room_id, {
                "type": "youtube_sync",
                "url": room_data.get("youtube_url", ""),
                "state": "playing", "time": t,
            })

        elif msg_type == "youtube_pause" and is_host:
            t = data.get("time", 0)
            room_ops.update_room(tenant_id, room_id, {
                "playback_state": "paused", "playback_time": str(t),
            })
            await self.broadcast(room_id, {
                "type": "youtube_sync",
                "url": room_data.get("youtube_url", ""),
                "state": "paused", "time": t,
            })

        elif msg_type == "youtube_seek" and is_host:
            t = data.get("time", 0)
            room_ops.update_room(tenant_id, room_id, {
                "playback_time": str(t),
            })
            await self.broadcast(room_id, {
                "type": "youtube_sync",
                "url": room_data.get("youtube_url", ""),
                "state": room_data.get("playback_state", "paused"),
                "time": t,
            })

        # ── Karaoke spotlight ──
        elif msg_type == "karaoke_spotlight" and is_host:
            target = data.get("phone", "")
            target_name = data.get("name", "")
            await self.broadcast(room_id, {
                "type": "karaoke_spotlight",
                "phone": target, "name": target_name,
            })

        # ── Karaoke score (broadcast live score to others) ──
        elif msg_type == "karaoke_score":
            await self.broadcast(room_id, {
                "type": "karaoke_score",
                "phone": phone, "from": name,
                "score": data.get("score", 0),
                "streak": data.get("streak", 0),
            }, exclude_phone=phone)

        # ── Karaoke performance done (broadcast final result) ──
        elif msg_type == "karaoke_perf_done":
            await self.broadcast(room_id, {
                "type": "karaoke_perf_done",
                "phone": phone, "from": name,
                "score": data.get("score", 0),
                "grade": data.get("grade", ""),
                "song": data.get("song", ""),
                "artist": data.get("artist", ""),
            })

        # ── Karaoke rating (send rating to target performer) ──
        elif msg_type == "karaoke_rating":
            target = data.get("target_phone", "")
            await self.send_to(room_id, target, {
                "type": "karaoke_rating",
                "from": name, "from_phone": phone,
                "rating": data.get("rating", 0),
            })

        # ── Gift (broadcast gift animation to all) ──
        elif msg_type == "gift":
            gift_name = data.get("gift", "")
            await self.broadcast(room_id, {
                "type": "gift",
                "from": name, "from_phone": phone,
                "name": gift_name,
                "emoji": data.get("emoji", "🎁"),
                "stars": data.get("stars", 0),
                "full": data.get("full", False),
                "ts": now,
            }, exclude_phone=phone)

        # ── Game actions ──
        elif msg_type == "game_action":
            game_events = await self._handle_game_action(
                room_id, phone, name, data, room_ops, tenant_id, room_data, is_host
            )
            events.extend(game_events)

        elif msg_type == "game_start" and is_host:
            await self._start_game(
                room_id, phone, data, room_ops, tenant_id
            )
            events.append("game_played")

        elif msg_type == "ping":
            await self.send_to(room_id, phone, {"type": "pong"})

        return events

    # ═══════════════════════════════════════════════════════════════════════
    # GAME LOGIC
    # ═══════════════════════════════════════════════════════════════════════

    async def _start_game(self, room_id, host_phone, data, room_ops, tid):
        game_type = data.get("game_type", "quiz")
        players = self.get_connected_phones(room_id)

        if game_type == "quiz":
            quiz_idx = data.get("quiz_index", random.randint(0, len(QUIZ_SETS) - 1))
            state = new_quiz_state(quiz_idx, players)
            state["status"] = "question"
        elif game_type == "morpion":
            if len(players) < 2:
                await self.send_to(room_id, host_phone, {
                    "type": "system",
                    "content": "Il faut au moins 2 joueurs pour le Morpion. Invite un proche en cliquant sur le bouton Participants puis Inviter !",
                    "action": "show_invite",
                })
                return
            random.shuffle(players)
            state = new_morpion_state(players[0], players[1])
        elif game_type == "memory":
            state = new_memory_state(players)
        else:
            return

        room_ops.update_room(tid, room_id, {
            "game_type": game_type,
            "game_state": json.dumps(state),
            "status": "playing",
        })
        await self.broadcast(room_id, {
            "type": "game_update", "game_type": game_type, "state": state,
        })

    async def _handle_game_action(self, room_id, phone, name, data,
                                   room_ops, tid, room_data, is_host) -> List[str]:
        events: List[str] = []
        raw = room_data.get("game_state", "{}")
        try:
            state = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return events
        game_type = state.get("game_type", "")
        changed = False

        if game_type == "quiz":
            changed = self._process_quiz(state, phone, data)
        elif game_type == "morpion":
            changed = self._process_morpion(state, phone, data)
        elif game_type == "memory":
            changed = self._process_memory(state, phone, data)

        if changed:
            room_ops.update_room(tid, room_id, {
                "game_state": json.dumps(state),
            })
            await self.broadcast(room_id, {
                "type": "game_update", "game_type": game_type, "state": state,
            })
            # Detecter victoire
            status = state.get("status", "")
            if status in ("won", "finished"):
                winner = state.get("winner")
                if winner == phone:
                    events.append("game_won")
                elif status == "finished" and game_type in ("quiz", "memory"):
                    # Pour quiz/memory: le joueur avec le meilleur score gagne
                    scores = state.get("scores", {})
                    if scores and phone in scores:
                        max_score = max(scores.values())
                        if scores[phone] == max_score:
                            events.append("game_won")
        return events

    # ── Quiz ──

    def _process_quiz(self, state: dict, phone: str, data: dict) -> bool:
        if state.get("status") != "question":
            return False
        action = data.get("action", {})
        answer_idx = action.get("answer")
        if answer_idx is None:
            return False

        q_idx = state["current_question"]
        questions = state.get("questions", [])
        if q_idx >= len(questions):
            return False

        # Already answered this round?
        if phone in state.get("answers", {}):
            return False

        state.setdefault("answers", {})[phone] = answer_idx

        # Check if correct
        correct = questions[q_idx].get("answer", -1)
        if answer_idx == correct:
            state.setdefault("scores", {})[phone] = state["scores"].get(phone, 0) + 1

        # All answered? → next question or finish
        connected = set(state.get("scores", {}).keys())
        answered = set(state.get("answers", {}).keys())
        if connected <= answered:
            state["current_question"] = q_idx + 1
            state["answers"] = {}
            if state["current_question"] >= state.get("total_questions", 5):
                state["status"] = "finished"
            else:
                state["status"] = "question"

        return True

    # ── Morpion ──

    def _process_morpion(self, state: dict, phone: str, data: dict) -> bool:
        if state.get("status") != "playing":
            return False
        if state.get("turn") != phone:
            return False

        action = data.get("action", {})
        cell = action.get("cell")
        if cell is None or cell < 0 or cell > 8:
            return False

        board = state.get("board", [0] * 9)
        if board[cell] != 0:
            return False

        player_num = 1 if phone == state["player_x"] else 2
        board[cell] = player_num
        state["board"] = board

        winner = check_morpion_winner(board)
        if winner > 0:
            state["status"] = "won"
            state["winner"] = state["player_x"] if winner == 1 else state["player_o"]
        elif winner == -1:
            state["status"] = "draw"
            state["winner"] = None
        else:
            # Switch turn
            if phone == state["player_x"]:
                state["turn"] = state["player_o"]
            else:
                state["turn"] = state["player_x"]

        return True

    # ── Memory ──

    def _process_memory(self, state: dict, phone: str, data: dict) -> bool:
        if state.get("status") != "playing":
            return False
        if state.get("current_turn") != phone:
            return False

        action = data.get("action", {})
        card_idx = action.get("card")
        if card_idx is None or card_idx < 0 or card_idx >= 16:
            return False

        matched = state.get("matched", [False] * 16)
        selected = state.get("selected", [])

        if matched[card_idx] or card_idx in selected:
            return False

        selected.append(card_idx)
        state["selected"] = selected

        if len(selected) == 2:
            cards = state.get("cards", [])
            a, b = selected
            if cards[a] == cards[b]:
                # Match found
                matched[a] = True
                matched[b] = True
                state["matched"] = matched
                state["scores"][phone] = state["scores"].get(phone, 0) + 1
                # Check if all matched
                if all(matched):
                    state["status"] = "finished"
            # Next turn (rotate)
            turn_order = state.get("turn_order", [])
            if turn_order:
                cur_idx = turn_order.index(phone) if phone in turn_order else 0
                state["current_turn"] = turn_order[(cur_idx + 1) % len(turn_order)]
            state["selected"] = []
            # Reveal temporarily (client handles animation then hides)
            state["_last_reveal"] = [a, b]
            state["_last_matched"] = cards[a] == cards[b]

        return True


# Singleton
room_manager = RoomManager()
