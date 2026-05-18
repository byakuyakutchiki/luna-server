"""Operations Redis pour le module Secretaire (documents, budget, rappels).

Architecture dossiers :
  Dossier auto-cree par type_doc : "Factures", "Assurances", "Impots", etc.
  Sous-dossier par emetteur : "Factures/EDF", "Factures/Orange", etc.
  Deduplication par hash (emetteur + reference + montant + date_document).
"""

import json
import hashlib
import re
import secrets
import logging
from datetime import datetime, date
from typing import Optional, Dict, List
from zoneinfo import ZoneInfo

_TZ_PARIS = ZoneInfo("Europe/Paris")

logger = logging.getLogger(__name__)

TTL_DOCUMENT = 365 * 24 * 60 * 60      # 1 an
TTL_BUDGET = 365 * 24 * 60 * 60        # 1 an
TTL_REMINDER = 90 * 24 * 60 * 60       # 90 jours
MAX_DOCUMENTS = 500
MAX_BUDGET_ENTRIES = 2000
MAX_REMINDERS = 200

# Mapping type_doc -> nom de dossier
FOLDER_NAMES = {
    "facture": "Factures",
    "relance": "Relances",
    "courrier": "Courrier",
    "contrat": "Contrats",
    "fiche_de_paie": "Fiches de paie",
    "impot": "Impots",
    "assurance": "Assurances",
    "abonnement": "Abonnements",
    "devis": "Devis",
    "recu": "Recus",
    "email": "Emails",
    "autre": "Divers",
}


def _doc_fingerprint(doc: Dict) -> str:
    """Hash de deduplication : emetteur + reference + montant + date."""
    parts = [
        (doc.get("emetteur") or "").strip().lower(),
        (doc.get("reference") or "").strip().lower(),
        str(doc.get("montant") or ""),
        (doc.get("date_document") or "").strip(),
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _reminder_timestamp(due_date: str, due_time: str, text: str = "") -> float:
    """
    Calcule le timestamp UTC d'un rappel en tenant compte de l'heure (TZ Paris).

    Priorité : due_time explicite > heure extraite du texte (titre/description)
    Si aucune heure → 9h00 Paris (heure raisonnable par défaut).
    """
    # --- Normalise la date ---
    if not due_date:
        return datetime.now(_TZ_PARIS).timestamp()
    try:
        d = date.fromisoformat(due_date[:10])
    except ValueError:
        return datetime.now(_TZ_PARIS).timestamp()

    # --- Résout l'heure ---
    hour, minute = 9, 0  # défaut : 9h00

    # 1) due_time explicite : "HH:MM" ou "HH"
    if due_time:
        m = re.match(r"^(\d{1,2})(?::(\d{2}))?$", str(due_time).strip())
        if m:
            h = int(m.group(1))
            mn = int(m.group(2) or 0)
            if 0 <= h <= 23 and 0 <= mn <= 59:
                hour, minute = h, mn

    # 2) Fallback : extraire "à 20h", "a 8h30", "20:00", "8h" du texte
    elif text:
        m = re.search(r"\b(?:a|à)\s*(\d{1,2})h(\d{2})?\b", text, re.IGNORECASE)
        if not m:
            m = re.search(r"\b(\d{1,2})[h:](\d{2})\b", text)
        if m:
            h = int(m.group(1))
            mn = int(m.group(2) or 0) if m.group(2) else 0
            if 0 <= h <= 23 and 0 <= mn <= 59:
                hour, minute = h, mn

    dt_paris = datetime(d.year, d.month, d.day, hour, minute, tzinfo=_TZ_PARIS)
    return dt_paris.timestamp()


class SecretaryRedisOps:
    """CRUD Redis pour documents, budget et rappels."""

    def __init__(self, redis_client, tenant_id: int):
        self.rc = redis_client
        self.client = redis_client.client
        self.tid = tenant_id

    def _key(self, *parts) -> str:
        return f"luna:{self.tid}:secretary:" + ":".join(str(p) for p in parts)

    # =================================================================
    # DOSSIERS & DOCUMENTS
    # =================================================================

    def _folder_path(self, doc: Dict) -> str:
        """Genere le chemin dossier/sous-dossier a partir du document."""
        type_doc = doc.get("type_doc", "autre")
        folder = FOLDER_NAMES.get(type_doc, "Divers")
        emetteur = (doc.get("emetteur") or "").strip()
        if emetteur:
            # Nettoyer le nom pour en faire un sous-dossier
            emetteur = emetteur.replace("/", "-").replace("\\", "-")[:40]
            return f"{folder}/{emetteur}"
        return folder

    def _check_duplicate(self, doc: Dict) -> Optional[str]:
        """Verifie si un document identique existe deja. Retourne l'ID existant ou None."""
        fp = _doc_fingerprint(doc)
        existing_id = self.client.hget(self._key("doc_fingerprints"), fp)
        return existing_id

    def add_document(self, doc: Dict) -> tuple:
        """Ajoute un document. Retourne (doc_id, is_duplicate).
        Si doublon detecte, retourne l'ID existant sans creer de doublon."""

        # Deduplication
        fp = _doc_fingerprint(doc)
        existing_id = self.client.hget(self._key("doc_fingerprints"), fp)
        if existing_id:
            logger.info(f"Document doublon detecte: {existing_id} (fingerprint {fp})")
            return existing_id, True

        doc_id = secrets.token_hex(8)
        doc["id"] = doc_id
        doc["created_at"] = datetime.utcnow().isoformat()
        doc["status"] = doc.get("status", "pending")
        doc["folder"] = self._folder_path(doc)
        doc["fingerprint"] = fp

        # Store document metadata
        doc_key = self._key("doc", doc_id)
        self.client.hset(doc_key, mapping={k: str(v) if v is not None else "" for k, v in doc.items()})
        self.client.expire(doc_key, TTL_DOCUMENT)

        # Register fingerprint for dedup
        self.client.hset(self._key("doc_fingerprints"), fp, doc_id)
        self.client.expire(self._key("doc_fingerprints"), TTL_DOCUMENT)

        # Index by timestamp
        ts = datetime.utcnow().timestamp()
        self.client.zadd(self._key("documents"), {doc_id: ts})

        # Index in folder
        self.client.sadd(self._key("folder", doc["folder"]), doc_id)
        self.client.expire(self._key("folder", doc["folder"]), TTL_DOCUMENT)

        # Register folder in folder list
        self.client.sadd(self._key("folders"), doc["folder"])
        self.client.expire(self._key("folders"), TTL_DOCUMENT)

        # Trim oldest if too many
        count = self.client.zcard(self._key("documents"))
        if count and count > MAX_DOCUMENTS:
            old_ids = self.client.zrange(self._key("documents"), 0, count - MAX_DOCUMENTS - 1)
            for old_id in old_ids:
                self._delete_document(old_id)

        # Auto-create reminder if echeance exists
        echeance = doc.get("echeance", "")
        if echeance and doc.get("montant"):
            self.add_reminder({
                "type": "echeance",
                "doc_id": doc_id,
                "title": f"{doc.get('type_doc', 'Document')} — {doc.get('emetteur', '')}",
                "description": f"Echeance {doc.get('montant', '')}€ le {echeance}",
                "due_date": echeance,
                "montant": doc.get("montant", ""),
            })

        return doc_id, False

    def _delete_document(self, doc_id: str):
        """Supprime un document et ses index."""
        doc = self.client.hgetall(self._key("doc", doc_id))
        if doc:
            fp = doc.get("fingerprint", "")
            if fp:
                self.client.hdel(self._key("doc_fingerprints"), fp)
            folder = doc.get("folder", "")
            if folder:
                self.client.srem(self._key("folder", folder), doc_id)
        self.client.delete(self._key("doc", doc_id))
        self.client.zrem(self._key("documents"), doc_id)

    def get_document(self, doc_id: str) -> Optional[Dict]:
        doc_key = self._key("doc", doc_id)
        data = self.client.hgetall(doc_key)
        return data if data else None

    def update_document(self, doc_id: str, updates: Dict) -> bool:
        doc_key = self._key("doc", doc_id)
        if not self.client.exists(doc_key):
            return False
        updates["updated_at"] = datetime.utcnow().isoformat()
        # If folder-related fields change, update folder index
        if "type_doc" in updates or "emetteur" in updates:
            old_doc = self.client.hgetall(doc_key)
            old_folder = old_doc.get("folder", "")
            merged = {**old_doc, **updates}
            new_folder = self._folder_path(merged)
            if old_folder != new_folder:
                self.client.srem(self._key("folder", old_folder), doc_id)
                self.client.sadd(self._key("folder", new_folder), doc_id)
                self.client.expire(self._key("folder", new_folder), TTL_DOCUMENT)
                self.client.sadd(self._key("folders"), new_folder)
                updates["folder"] = new_folder
        self.client.hset(doc_key, mapping={k: str(v) for k, v in updates.items()})
        return True

    def get_folders(self) -> List[Dict]:
        """Retourne l'arborescence des dossiers avec le nombre de docs par dossier."""
        folder_names = self.client.smembers(self._key("folders")) or set()
        folders = []
        for name in sorted(folder_names):
            count = self.client.scard(self._key("folder", name)) or 0
            if count == 0:
                continue
            parts = name.split("/")
            folders.append({
                "path": name,
                "name": parts[-1],
                "parent": parts[0] if len(parts) > 1 else None,
                "count": count,
            })
        return folders

    def get_folder_documents(self, folder_path: str) -> List[Dict]:
        """Retourne tous les documents d'un dossier."""
        doc_ids = self.client.smembers(self._key("folder", folder_path)) or set()
        docs = []
        for doc_id in doc_ids:
            data = self.client.hgetall(self._key("doc", doc_id))
            if data:
                docs.append(data)
        # Trier par date_document desc
        docs.sort(key=lambda d: d.get("date_document", ""), reverse=True)
        return docs

    def get_documents(self, limit: int = 50, doc_type: str = None, status: str = None) -> List[Dict]:
        """Retourne les documents recents, filtrables par type et statut."""
        doc_ids = self.client.zrevrange(self._key("documents"), 0, limit * 2 - 1) or []
        docs = []
        for doc_id in doc_ids:
            data = self.client.hgetall(self._key("doc", doc_id))
            if not data:
                continue
            if doc_type and data.get("type_doc", "") != doc_type:
                continue
            if status and data.get("status", "") != status:
                continue
            docs.append(data)
            if len(docs) >= limit:
                break
        return docs

    def get_pending_documents(self) -> List[Dict]:
        return self.get_documents(limit=100, status="pending")

    def get_overdue_documents(self) -> List[Dict]:
        return self.get_documents(limit=100, status="overdue")

    def search_documents(self, query: str) -> List[Dict]:
        """Recherche dans les documents par emetteur, reference, objet."""
        query_lower = query.lower()
        all_docs = self.get_documents(limit=200)
        results = []
        for d in all_docs:
            searchable = f"{d.get('emetteur','')} {d.get('reference','')} {d.get('objet','')} {d.get('type_doc','')}".lower()
            if query_lower in searchable:
                results.append(d)
        return results[:20]

    def get_documents_summary(self) -> Dict:
        """Resume : combien par type, combien en attente, total a payer."""
        all_docs = self.get_documents(limit=200)
        summary = {
            "total": len(all_docs),
            "pending": 0,
            "paid": 0,
            "overdue": 0,
            "total_pending_amount": 0.0,
            "total_overdue_amount": 0.0,
            "by_type": {},
            "folders_count": self.client.scard(self._key("folders")) or 0,
        }
        for d in all_docs:
            status = d.get("status", "pending")
            if status == "pending":
                summary["pending"] += 1
                try:
                    summary["total_pending_amount"] += float(d.get("montant", 0))
                except (ValueError, TypeError):
                    pass
            elif status == "paid":
                summary["paid"] += 1
            elif status == "overdue":
                summary["overdue"] += 1
                try:
                    summary["total_overdue_amount"] += float(d.get("montant", 0))
                except (ValueError, TypeError):
                    pass
            t = d.get("type_doc", "autre")
            summary["by_type"][t] = summary["by_type"].get(t, 0) + 1
        return summary

    def mark_document_status(self, doc_id: str, status: str) -> bool:
        return self.update_document(doc_id, {"status": status})

    # =================================================================
    # BUDGET
    # =================================================================

    def set_budget_profile(self, data: Dict) -> None:
        """Definit le profil budget (revenus, charges fixes)."""
        key = self._key("budget_profile")
        self.client.hset(key, mapping={k: str(v) for k, v in data.items()})
        self.client.expire(key, TTL_BUDGET)

    def get_budget_profile(self) -> Optional[Dict]:
        key = self._key("budget_profile")
        data = self.client.hgetall(key)
        return data if data else None

    def add_budget_entry(self, entry: Dict) -> str:
        """Ajoute une entree de depense ou revenu."""
        entry_id = secrets.token_hex(6)
        entry["id"] = entry_id
        entry["created_at"] = datetime.utcnow().isoformat()
        if "date" not in entry:
            entry["date"] = date.today().isoformat()
        if "month" not in entry:
            entry["month"] = date.today().strftime("%Y-%m")

        entry_json = json.dumps(entry, ensure_ascii=False)
        key = self._key("budget_entries", entry.get("month", date.today().strftime("%Y-%m")))
        self.client.lpush(key, entry_json)
        self.client.ltrim(key, 0, MAX_BUDGET_ENTRIES - 1)
        self.client.expire(key, TTL_BUDGET)

        self._update_monthly_totals(entry)
        return entry_id

    def _update_monthly_totals(self, entry: Dict) -> None:
        month = entry.get("month", date.today().strftime("%Y-%m"))
        key = self._key("budget_totals", month)
        try:
            amount = float(entry.get("montant", 0))
        except (ValueError, TypeError):
            return

        cat = entry.get("categorie", "autre")
        direction = entry.get("direction", "depense")

        if direction == "depense":
            self.client.hincrbyfloat(key, "total_depenses", amount)
            self.client.hincrbyfloat(key, f"cat_{cat}", amount)
        else:
            self.client.hincrbyfloat(key, "total_revenus", amount)

        self.client.expire(key, TTL_BUDGET)

    def get_monthly_totals(self, month: str = None) -> Dict:
        if not month:
            month = date.today().strftime("%Y-%m")
        key = self._key("budget_totals", month)
        data = self.client.hgetall(key)
        if not data:
            return {"month": month, "total_depenses": 0, "total_revenus": 0}
        result = {"month": month}
        for k, v in data.items():
            try:
                result[k] = round(float(v), 2)
            except (ValueError, TypeError):
                result[k] = v
        return result

    def get_budget_entries(self, month: str = None, limit: int = 50) -> List[Dict]:
        if not month:
            month = date.today().strftime("%Y-%m")
        key = self._key("budget_entries", month)
        raw = self.client.lrange(key, 0, limit - 1) or []
        entries = []
        for r in raw:
            try:
                entries.append(json.loads(r))
            except (json.JSONDecodeError, TypeError):
                continue
        return entries

    def get_budget_analysis(self) -> Dict:
        """Analyse complete : revenus - charges = reste a vivre, prevision fin de mois."""
        profile = self.get_budget_profile() or {}
        current_month = date.today().strftime("%Y-%m")
        totals = self.get_monthly_totals(current_month)

        try:
            revenus_fixes = float(profile.get("revenus_mensuels", 0))
        except (ValueError, TypeError):
            revenus_fixes = 0
        try:
            charges_fixes = float(profile.get("charges_fixes", 0))
        except (ValueError, TypeError):
            charges_fixes = 0

        total_depenses = totals.get("total_depenses", 0)
        total_revenus_variable = totals.get("total_revenus", 0)

        reste_a_vivre = revenus_fixes + total_revenus_variable - charges_fixes - total_depenses
        jour_actuel = date.today().day
        jours_dans_mois = 30
        jours_restants = max(1, jours_dans_mois - jour_actuel)

        depense_jour_moy = total_depenses / max(1, jour_actuel)
        depenses_prevues = depense_jour_moy * jours_restants
        solde_prevu_fin_mois = reste_a_vivre - depenses_prevues

        categories = {}
        for k, v in totals.items():
            if k.startswith("cat_"):
                try:
                    categories[k[4:]] = round(float(v), 2)
                except (ValueError, TypeError):
                    pass

        return {
            "month": current_month,
            "revenus_fixes": revenus_fixes,
            "charges_fixes": charges_fixes,
            "total_depenses": round(total_depenses, 2),
            "total_revenus_variable": round(total_revenus_variable, 2),
            "reste_a_vivre": round(reste_a_vivre, 2),
            "depense_moyenne_jour": round(depense_jour_moy, 2),
            "jours_restants": jours_restants,
            "solde_prevu_fin_mois": round(solde_prevu_fin_mois, 2),
            "alerte_depassement": solde_prevu_fin_mois < 0,
            "categories": categories,
        }

    # =================================================================
    # RAPPELS
    # =================================================================

    def add_reminder(self, reminder: Dict) -> str:
        rem_id = secrets.token_hex(6)
        reminder["id"] = rem_id
        reminder["created_at"] = datetime.utcnow().isoformat()
        reminder["done"] = "false"

        ts = _reminder_timestamp(
            reminder.get("due_date", ""),
            reminder.get("due_time", ""),
            reminder.get("title", "") + " " + reminder.get("description", ""),
        )

        rem_key = self._key("reminder", rem_id)
        self.client.hset(rem_key, mapping={k: str(v) if v is not None else "" for k, v in reminder.items()})
        self.client.expire(rem_key, TTL_REMINDER)
        self.client.zadd(self._key("reminders"), {rem_id: ts})
        return rem_id

    def get_upcoming_reminders(self, limit: int = 20) -> List[Dict]:
        now = datetime.utcnow().timestamp()
        rem_ids = self.client.zrangebyscore(self._key("reminders"), now, "+inf", start=0, num=limit) or []
        reminders = []
        for rem_id in rem_ids:
            data = self.client.hgetall(self._key("reminder", rem_id))
            if data and data.get("done", "false") != "true":
                reminders.append(data)
        return reminders

    def get_overdue_reminders(self) -> List[Dict]:
        now = datetime.utcnow().timestamp()
        rem_ids = self.client.zrangebyscore(self._key("reminders"), 0, now) or []
        overdue = []
        for rem_id in rem_ids:
            data = self.client.hgetall(self._key("reminder", rem_id))
            if data and data.get("done", "false") != "true":
                overdue.append(data)
        return overdue

    def mark_reminder_done(self, rem_id: str) -> bool:
        rem_key = self._key("reminder", rem_id)
        if not self.client.exists(rem_key):
            return False
        self.client.hset(rem_key, "done", "true")
        return True

    def get_all_reminders(self, limit: int = 50) -> List[Dict]:
        rem_ids = self.client.zrange(self._key("reminders"), 0, limit - 1) or []
        reminders = []
        for rem_id in rem_ids:
            data = self.client.hgetall(self._key("reminder", rem_id))
            if data:
                reminders.append(data)
        return reminders

    def delete_reminder(self, rem_id: str) -> bool:
        self.client.delete(self._key("reminder", rem_id))
        return bool(self.client.zrem(self._key("reminders"), rem_id))
