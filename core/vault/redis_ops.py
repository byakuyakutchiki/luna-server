"""Opérations Redis pour le coffre-fort documentaire."""
import json
import time
import uuid
from datetime import date, datetime, timedelta
from typing import Optional


class VaultRedisOps:
    """Toutes les opérations Redis du vault pour un tenant donné."""

    _DOCS_KEY = "vault:docs"          # sorted set: doc_id → timestamp création
    _DOC_KEY = "vault:doc:{doc_id}"   # hash: métadonnées
    _REM_KEY = "vault:reminders"      # sorted set: json → timestamp rappel
    _CONSENT_KEY = "vault:consent"    # string: timestamp consentement
    TTL_DOC = 86400 * 365             # 1 an max

    def __init__(self, redis_client, tenant_id: int):
        self.rc = redis_client
        self.tid = tenant_id

    def _k(self, key: str, **kwargs) -> str:
        return f"luna:{self.tid}:{key.format(**kwargs)}"

    # ── Consentement RGPD ─────────────────────────────────────────────

    def has_consent(self) -> bool:
        return bool(self.rc.client.get(self._k(self._CONSENT_KEY)))

    def record_consent(self) -> None:
        self.rc.client.set(self._k(self._CONSENT_KEY), datetime.utcnow().isoformat())

    def revoke_consent(self) -> None:
        """Révocation → supprime tout (RGPD droit à l'effacement)."""
        self.delete_all()
        self.rc.client.delete(self._k(self._CONSENT_KEY))

    # ── Documents ─────────────────────────────────────────────────────

    def save_doc(self, metadata: dict) -> str:
        doc_id = uuid.uuid4().hex
        now = time.time()
        key = self._k(self._DOC_KEY, doc_id=doc_id)
        self.rc.client.hset(key, mapping={
            "id": doc_id,
            "created_at": datetime.utcnow().isoformat(),
            **{k: json.dumps(v) if isinstance(v, (dict, list)) else (str(v) if v is not None else "") for k, v in metadata.items()},
        })
        self.rc.client.expire(key, self.TTL_DOC)
        self.rc.client.zadd(self._k(self._DOCS_KEY), {doc_id: now})
        # Planifier les rappels
        for rem in metadata.get("reminders", []):
            self._schedule_reminder(doc_id, rem, metadata)
        return doc_id

    def list_docs(self, limit: int = 100) -> list[dict]:
        doc_ids = self.rc.client.zrevrange(self._k(self._DOCS_KEY), 0, limit - 1)
        docs = []
        for did in doc_ids:
            d = self._load_doc(did)
            if d:
                docs.append(d)
        return docs

    def get_doc(self, doc_id: str) -> Optional[dict]:
        return self._load_doc(doc_id)

    def delete_doc(self, doc_id: str) -> bool:
        key = self._k(self._DOC_KEY, doc_id=doc_id)
        deleted = self.rc.client.delete(key)
        self.rc.client.zrem(self._k(self._DOCS_KEY), doc_id)
        # Supprimer ses rappels
        self._remove_reminders_for_doc(doc_id)
        return bool(deleted)

    def delete_all(self) -> int:
        doc_ids = self.rc.client.zrange(self._k(self._DOCS_KEY), 0, -1)
        count = 0
        for did in doc_ids:
            self.rc.client.delete(self._k(self._DOC_KEY, doc_id=did))
            count += 1
        self.rc.client.delete(self._k(self._DOCS_KEY))
        self.rc.client.delete(self._k(self._REM_KEY))
        return count

    def _load_doc(self, doc_id: str) -> Optional[dict]:
        raw = self.rc.client.hgetall(self._k(self._DOC_KEY, doc_id=doc_id))
        if not raw:
            return None
        d = {}
        for k, v in raw.items():
            try:
                d[k] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                d[k] = v
        return d

    # ── Rappels ───────────────────────────────────────────────────────

    def _schedule_reminder(self, doc_id: str, rem: dict, doc_meta: dict) -> None:
        from datetime import datetime
        try:
            ts = datetime.fromisoformat(rem["date"]).timestamp()
        except (KeyError, ValueError):
            return
        payload = json.dumps({
            "doc_id": doc_id,
            "tenant_id": self.tid,
            "message": rem["message"],
            "doc_type": doc_meta.get("doc_type", "autre"),
            "titre": doc_meta.get("titre", "Document"),
        })
        self.rc.client.zadd(self._k(self._REM_KEY), {payload: ts})

    def _remove_reminders_for_doc(self, doc_id: str) -> None:
        rems = self.rc.client.zrange(self._k(self._REM_KEY), 0, -1)
        to_remove = [r for r in rems if f'"doc_id": "{doc_id}"' in r or f'"doc_id":"{doc_id}"' in r]
        for r in to_remove:
            self.rc.client.zrem(self._k(self._REM_KEY), r)

    def get_due_reminders(self) -> list[dict]:
        """Rappels dont la date est passée (score <= maintenant)."""
        import time
        rems_raw = self.rc.client.zrangebyscore(self._k(self._REM_KEY), 0, time.time())
        result = []
        for r in rems_raw:
            try:
                result.append(json.loads(r))
                result[-1]["_raw"] = r
            except json.JSONDecodeError:
                pass
        return result

    def mark_reminder_sent(self, raw: str) -> None:
        self.rc.client.zrem(self._k(self._REM_KEY), raw)

    def get_upcoming_reminders(self, days: int = 30) -> list[dict]:
        """Rappels à venir dans les N prochains jours."""
        import time
        now = time.time()
        horizon = now + days * 86400
        rems_raw = self.rc.client.zrangebyscore(self._k(self._REM_KEY), now, horizon)
        result = []
        for r in rems_raw:
            try:
                result.append(json.loads(r))
            except json.JSONDecodeError:
                pass
        return result
