"""Operations Redis pour le form filler (sessions, profils, historique)."""

import json
import secrets
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

TTL_SESSION = 2 * 60 * 60       # 2h — session d'analyse active
TTL_FILLED = 24 * 60 * 60       # 24h — PDF rempli téléchargeable
TTL_PROFILE = 365 * 24 * 60 * 60  # 1 an — profil utilisateur
MAX_HISTORY = 50


class FormFillerRedisOps:
    """CRUD Redis pour sessions form filler, profils et historique."""

    def __init__(self, redis_client, tenant_id: int):
        self.rc = redis_client
        self.client = redis_client.client
        self.tid = tenant_id
        self.prefix = f"luna:t:{tenant_id}:formfiller"

    # ── Sessions ──────────────────────────────────────────────────

    def create_session(self, analysis: dict, pdf_b64: str, filename: str) -> str:
        """Crée une session d'analyse. Retourne session_id."""
        sid = secrets.token_hex(12)
        key = f"{self.prefix}:session:{sid}"
        data = {
            "analysis": json.dumps(analysis),
            "pdf_b64": pdf_b64,
            "filename": filename,
            "created": datetime.utcnow().isoformat(),
        }
        self.client.hset(key, mapping=data)
        self.client.expire(key, TTL_SESSION)
        return sid

    def get_session(self, sid: str) -> dict | None:
        """Récupère une session."""
        key = f"{self.prefix}:session:{sid}"
        data = self.client.hgetall(key)
        if not data:
            return None
        result = {}
        for k, v in data.items():
            dk = k.decode() if isinstance(k, bytes) else k
            dv = v.decode() if isinstance(v, bytes) else v
            result[dk] = dv
        if "analysis" in result:
            result["analysis"] = json.loads(result["analysis"])
        return result

    def save_filled_pdf(self, sid: str, filled_b64: str):
        """Sauvegarde le PDF rempli dans la session."""
        key = f"{self.prefix}:session:{sid}"
        self.client.hset(key, "filled_pdf_b64", filled_b64)
        self.client.expire(key, TTL_FILLED)

    def get_filled_pdf(self, sid: str) -> str | None:
        """Récupère le PDF rempli."""
        key = f"{self.prefix}:session:{sid}"
        val = self.client.hget(key, "filled_pdf_b64")
        if val:
            return val.decode() if isinstance(val, bytes) else val
        return None

    # ── Profil utilisateur ────────────────────────────────────────

    def save_profile(self, profile: dict):
        """Sauvegarde le profil de l'utilisateur."""
        key = f"{self.prefix}:profile"
        self.client.set(key, json.dumps(profile, ensure_ascii=False))
        self.client.expire(key, TTL_PROFILE)

    def get_profile(self) -> dict:
        """Récupère le profil."""
        key = f"{self.prefix}:profile"
        val = self.client.get(key)
        if val:
            return json.loads(val.decode() if isinstance(val, bytes) else val)
        return {}

    # ── Historique ────────────────────────────────────────────────

    def add_to_history(self, entry: dict):
        """Ajoute une entrée à l'historique."""
        key = f"{self.prefix}:history"
        entry["date"] = datetime.utcnow().isoformat()
        self.client.lpush(key, json.dumps(entry, ensure_ascii=False))
        self.client.ltrim(key, 0, MAX_HISTORY - 1)
        self.client.expire(key, TTL_PROFILE)

    def get_history(self, limit: int = 20) -> list[dict]:
        """Récupère l'historique."""
        key = f"{self.prefix}:history"
        items = self.client.lrange(key, 0, limit - 1)
        result = []
        for item in items:
            raw = item.decode() if isinstance(item, bytes) else item
            result.append(json.loads(raw))
        return result
