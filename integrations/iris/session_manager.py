"""
Iris Session Manager — sessions collaboratives multi-participants.

Redis pour la persistance (TTL 8h).
Registre WS en mémoire pour le broadcast (in-process, single-instance).
"""
import json
import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

SESSION_TTL   = 8 * 3600   # 8h
INVITE_TTL    = 3600        # 1h
PENDING_TTL   = 600         # 10 min


class IrisSessionManager:
    """Gère les sessions Iris multi-participants."""

    # Registre WS en mémoire : {session_id: {participant_id: ws}}
    _ws_registry: Dict[str, Dict[str, Any]] = {}

    def __init__(self, redis_client):
        # redis_client = instance Luna RedisClient (redis_client.client = connexion raw)
        self._r = redis_client.client

    # ─── Clés Redis ────────────────────────────────────────────────────────────

    def _sk(self, sid: str) -> str:
        return f"luna:iris:session:{sid}"

    def _pk(self, sid: str) -> str:
        return f"luna:iris:session:{sid}:participants"

    def _ek(self, sid: str) -> str:
        return f"luna:iris:session:{sid}:pending"

    def _ik(self, token: str) -> str:
        return f"luna:iris:invite:{token}"

    # ─── Sessions ──────────────────────────────────────────────────────────────

    def create_session(self, tenant_id: int, name: str) -> dict:
        sid = str(uuid.uuid4())[:8]
        data = {
            "session_id": sid,
            "tenant_id": str(tenant_id),
            "name": name,
            "created_at": datetime.utcnow().isoformat(),
            "status": "active",
        }
        self._r.hset(self._sk(sid), mapping=data)
        self._r.expire(self._sk(sid), SESSION_TTL)
        IrisSessionManager._ws_registry[sid] = {}
        logger.info(f"IrisSession created: {sid} (tenant {tenant_id})")
        return data

    def get_session(self, sid: str) -> Optional[dict]:
        raw = self._r.hgetall(self._sk(sid))
        if not raw:
            return None
        return {k: v for k, v in raw.items()}

    def close_session(self, sid: str):
        self._r.delete(self._sk(sid))
        self._r.delete(self._pk(sid))
        self._r.delete(self._ek(sid))
        IrisSessionManager._ws_registry.pop(sid, None)
        logger.info(f"IrisSession closed: {sid}")

    # ─── Participants ──────────────────────────────────────────────────────────

    def add_participant(self, sid: str, participant: dict):
        pid = participant["participant_id"]
        self._r.hset(self._pk(sid), pid, json.dumps(participant))
        self._r.expire(self._pk(sid), SESSION_TTL)
        if sid not in IrisSessionManager._ws_registry:
            IrisSessionManager._ws_registry[sid] = {}

    def remove_participant(self, sid: str, pid: str):
        self._r.hdel(self._pk(sid), pid)
        IrisSessionManager._ws_registry.get(sid, {}).pop(pid, None)

    def get_participants(self, sid: str) -> List[dict]:
        raw = self._r.hgetall(self._pk(sid))
        ws_reg = IrisSessionManager._ws_registry.get(sid, {})
        result = []
        for pid, pjson in raw.items():
            try:
                p = json.loads(pjson)
                p["online"] = pid in ws_reg
                result.append(p)
            except Exception:
                pass
        return result

    # ─── WebSocket registry ────────────────────────────────────────────────────

    def register_ws(self, sid: str, pid: str, ws):
        if sid not in IrisSessionManager._ws_registry:
            IrisSessionManager._ws_registry[sid] = {}
        IrisSessionManager._ws_registry[sid][pid] = ws
        logger.info(f"IrisSession WS registered: {sid}/{pid}")

    def unregister_ws(self, sid: str, pid: str):
        IrisSessionManager._ws_registry.get(sid, {}).pop(pid, None)
        logger.info(f"IrisSession WS unregistered: {sid}/{pid}")

    async def broadcast(self, sid: str, message: dict):
        """Envoie un message à tous les WS actifs de la session."""
        ws_reg = IrisSessionManager._ws_registry.get(sid, {})
        if not ws_reg:
            return
        msg_str = json.dumps(message, ensure_ascii=False)
        dead = []
        for pid, ws in list(ws_reg.items()):
            try:
                await ws.send_text(msg_str)
            except Exception as e:
                logger.warning(f"IrisSession broadcast failed {sid}/{pid}: {e}")
                dead.append(pid)
        for pid in dead:
            ws_reg.pop(pid, None)

    async def notify_owner(self, sid: str, message: dict):
        """Envoie uniquement au propriétaire de la session."""
        participants = self.get_participants(sid)
        owner = next((p for p in participants if p.get("role") == "owner"), None)
        if not owner:
            return
        ws_reg = IrisSessionManager._ws_registry.get(sid, {})
        ows = ws_reg.get(owner["participant_id"])
        if ows:
            try:
                await ows.send_text(json.dumps(message, ensure_ascii=False))
            except Exception as e:
                logger.warning(f"IrisSession notify_owner failed {sid}: {e}")

    # ─── Actions en attente ────────────────────────────────────────────────────

    def create_pending_action(self, sid: str, action: dict) -> str:
        aid = str(uuid.uuid4())[:8]
        action = {**action, "action_id": aid, "status": "pending",
                  "created_at": datetime.utcnow().isoformat()}
        self._r.hset(self._ek(sid), aid, json.dumps(action))
        self._r.expire(self._ek(sid), PENDING_TTL)
        return aid

    def get_pending_actions(self, sid: str) -> List[dict]:
        raw = self._r.hgetall(self._ek(sid))
        result = []
        for aid, ajson in raw.items():
            try:
                a = json.loads(ajson)
                if a.get("status") == "pending":
                    result.append(a)
            except Exception:
                pass
        return result

    def resolve_action(self, sid: str, aid: str, approved: bool) -> Optional[dict]:
        raw = self._r.hget(self._ek(sid), aid)
        if not raw:
            return None
        action = json.loads(raw)
        action["status"] = "approved" if approved else "rejected"
        self._r.hset(self._ek(sid), aid, json.dumps(action))
        return action

    # ─── Invitations ──────────────────────────────────────────────────────────

    def create_invite(self, sid: str, pid: str) -> str:
        token = str(uuid.uuid4())
        self._r.setex(
            self._ik(token),
            INVITE_TTL,
            json.dumps({"session_id": sid, "participant_id": pid}),
        )
        return token

    def consume_invite(self, token: str) -> Optional[dict]:
        raw = self._r.get(self._ik(token))
        if not raw:
            return None
        return json.loads(raw)
