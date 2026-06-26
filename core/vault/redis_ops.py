"""Opérations Redis pour le coffre-fort documentaire."""
import json
import time
import uuid
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any


class VaultRedisOps:
    """Toutes les opérations Redis du vault pour un tenant donné."""

    _DOCS_KEY     = "vault:docs"                    # sorted set: doc_id → timestamp création
    _DOC_KEY      = "vault:doc:{doc_id}"            # hash: métadonnées
    _TYPE_KEY     = "vault:docs_by_type:{doc_type}" # sorted set: doc_id → timestamp (par type)
    _REM_KEY      = "vault:reminders"               # sorted set: json → timestamp rappel
    _CONSENT_KEY  = "vault:consent"                 # string: timestamp consentement
    _FOLDERS_KEY  = "vault:folders"                 # set: dossiers custom créés par l'utilisateur
    _RULES_KEY    = "vault:folder_rules"            # hash: emetteur normalisé → folder_path appris
    TTL_DOC = 86400 * 365             # 1 an max

    # Arborescence par défaut : doc_type → "Dossier" ou "Dossier/Sous-dossier".
    # Best-effort modifiable par l'utilisateur (l'IA suggère, elle ne décide pas).
    DEFAULT_FOLDER_MAP = {
        "cni":             "Identité",
        "passeport":       "Identité",
        "titre_sejour":    "Identité",
        "permis_conduire": "Identité",
        "carte_vitale":    "Santé",
        "ordonnance":      "Santé/Ordonnances",
        "facture":         "Factures",
        "facture_energie": "Logement/Énergie",
        "releve_bancaire": "Banque/Relevés",
        "avis_imposition": "Impôts",
        "contrat":         "Logement/Contrats",
        "assurance":       "Assurance",
        "courrier_admin":  "Administratif",
        "diplome":         "Travail/Diplômes",
        "autre":           "Personnel",
    }
    # Dossiers racine toujours présents dans l'arbre (même vides), ordre d'affichage.
    ROOT_FOLDERS = [
        "Identité", "Banque", "Assurance", "Logement", "Santé",
        "Travail", "Impôts", "Administratif", "Factures", "Personnel",
    ]

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
        # Index par type (pour get_profile_data)
        doc_type = metadata.get("doc_type", "autre")
        self.rc.client.zadd(self._k(self._TYPE_KEY, doc_type=doc_type), {doc_id: now})
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
        self.rc.client.delete(self._k(self._FOLDERS_KEY))
        self.rc.client.delete(self._k(self._RULES_KEY))
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

    # ── Arborescence / classement (issue #22, Lot A) ──────────────────
    #
    # 100 % additif : le dossier d'un document est résolu sans rien stocker
    # de plus tant que l'utilisateur ne déplace rien. Priorité de résolution :
    #   1. champ explicite `folder_path` sur le doc (déplacement utilisateur) ;
    #   2. règle apprise pour cet émetteur (l'IA apprend des choix passés) ;
    #   3. mapping par défaut selon le type de document.

    FOLDER_ICONS = {
        "Identité": "🪪", "Banque": "🏦", "Assurance": "🛡", "Logement": "🏠",
        "Santé": "❤️", "Travail": "💼", "Impôts": "🧾", "Administratif": "📬",
        "Factures": "🧾", "Personnel": "📂",
    }

    @staticmethod
    def _norm_key(s: str) -> str:
        """Normalise un émetteur pour servir de clé de règle (minuscule, sans accents/espaces multiples)."""
        if not s:
            return ""
        import unicodedata
        nfd = unicodedata.normalize("NFD", str(s))
        out = "".join(c for c in nfd if unicodedata.category(c) != "Mn").lower()
        return " ".join(out.split())

    @staticmethod
    def _clean_folder_path(path: str) -> str:
        """Nettoie un folder_path : trim, max 2 niveaux, pas de slash en trop."""
        if not path:
            return ""
        parts = [p.strip() for p in str(path).split("/") if p.strip()]
        return "/".join(parts[:2])

    def _rules(self) -> dict:
        return self.rc.client.hgetall(self._k(self._RULES_KEY)) or {}

    def learn_rule(self, emetteur: str, folder_path: str) -> None:
        """Mémorise qu'un émetteur va dans tel dossier (apprentissage des choix utilisateur)."""
        key = self._norm_key(emetteur)
        fp = self._clean_folder_path(folder_path)
        if key and fp:
            self.rc.client.hset(self._k(self._RULES_KEY), key, fp)
            self.rc.client.expire(self._k(self._RULES_KEY), self.TTL_DOC)

    def folder_for(self, doc: dict, rules: dict | None = None) -> str:
        """Résout le dossier d'un document (explicite > règle apprise > défaut par type).

        `rules` peut être pré-chargé pour éviter un appel Redis par document.
        """
        explicit = self._clean_folder_path(doc.get("folder_path") or "")
        if explicit:
            return explicit
        if rules is None:
            rules = self._rules()
        rule = rules.get(self._norm_key(doc.get("emetteur") or ""))
        if rule:
            return self._clean_folder_path(rule)
        return self.DEFAULT_FOLDER_MAP.get(doc.get("doc_type", "autre"), "Personnel")

    def resolve_folders(self, docs: list[dict]) -> list[dict]:
        """Attache à chaque document son dossier résolu (champ `folder`). Charge les règles une fois."""
        rules = self._rules()
        for d in docs:
            d["folder"] = self.folder_for(d, rules)
        return docs

    def _custom_folders(self) -> set:
        return set(self.rc.client.smembers(self._k(self._FOLDERS_KEY)) or [])

    def add_folder(self, path: str) -> str:
        fp = self._clean_folder_path(path)
        if not fp:
            return ""
        self.rc.client.sadd(self._k(self._FOLDERS_KEY), fp)
        self.rc.client.expire(self._k(self._FOLDERS_KEY), self.TTL_DOC)
        return fp

    def delete_folder(self, path: str) -> dict:
        """Supprime un dossier vide. Refuse si des documents y sont rangés."""
        fp = self._clean_folder_path(path)
        if not fp:
            return {"ok": False, "error": "Chemin invalide"}
        if fp in self.ROOT_FOLDERS:
            return {"ok": False, "error": "Dossier racine non supprimable"}
        n = self._count_docs_under(fp)
        if n > 0:
            return {"ok": False, "error": f"Dossier non vide ({n} document(s))"}
        self.rc.client.srem(self._k(self._FOLDERS_KEY), fp)
        return {"ok": True}

    def rename_folder(self, old: str, new: str) -> dict:
        """Renomme un dossier : déplace tous ses documents et met à jour le set custom."""
        old_fp = self._clean_folder_path(old)
        new_fp = self._clean_folder_path(new)
        if not old_fp or not new_fp:
            return {"ok": False, "error": "Chemin invalide"}
        moved = self._move_docs_prefix(old_fp, new_fp)
        cf = self._custom_folders()
        if old_fp in cf:
            self.rc.client.srem(self._k(self._FOLDERS_KEY), old_fp)
        self.add_folder(new_fp)
        return {"ok": True, "moved": moved}

    def merge_folders(self, src: str, dst: str) -> dict:
        """Fusionne src dans dst : tous les documents de src passent dans dst."""
        src_fp = self._clean_folder_path(src)
        dst_fp = self._clean_folder_path(dst)
        if not src_fp or not dst_fp or src_fp == dst_fp:
            return {"ok": False, "error": "Chemins invalides"}
        moved = self._move_docs_prefix(src_fp, dst_fp)
        if src_fp not in self.ROOT_FOLDERS:
            self.rc.client.srem(self._k(self._FOLDERS_KEY), src_fp)
        self.add_folder(dst_fp)
        return {"ok": True, "moved": moved}

    def move_doc(self, doc_id: str, folder_path: str, learn: bool = True) -> dict:
        """Déplace un document dans un dossier (champ explicite folder_path)."""
        doc = self._load_doc(doc_id)
        if not doc:
            return {"ok": False, "error": "Document non trouvé"}
        fp = self._clean_folder_path(folder_path)
        if not fp:
            return {"ok": False, "error": "Dossier invalide"}
        self.rc.client.hset(self._k(self._DOC_KEY, doc_id=doc_id), "folder_path", fp)
        if learn and doc.get("emetteur"):
            self.learn_rule(doc["emetteur"], fp)
        return {"ok": True, "folder_path": fp}

    def rename_doc(self, doc_id: str, titre: str) -> dict:
        """Renomme un document (titre lisible, éditable par l'utilisateur)."""
        doc = self._load_doc(doc_id)
        if not doc:
            return {"ok": False, "error": "Document non trouvé"}
        t = (titre or "").strip()
        if not t:
            return {"ok": False, "error": "Titre vide"}
        self.rc.client.hset(self._k(self._DOC_KEY, doc_id=doc_id), "titre", t[:200])
        return {"ok": True, "titre": t[:200]}

    def _move_docs_prefix(self, old_fp: str, new_fp: str) -> int:
        """Déplace tous les docs dont le dossier résolu == old_fp vers new_fp."""
        moved = 0
        for doc in self.list_docs(limit=1000):
            if self.folder_for(doc) == old_fp:
                self.rc.client.hset(
                    self._k(self._DOC_KEY, doc_id=doc["id"]), "folder_path", new_fp)
                moved += 1
        return moved

    def _count_docs_under(self, fp: str) -> int:
        return sum(1 for doc in self.list_docs(limit=1000)
                   if self.folder_for(doc).startswith(fp))

    @staticmethod
    def _is_urgent(doc: dict) -> bool:
        if doc.get("expiry_status") in ("expired", "urgent"):
            return True
        return doc.get("priority") == "high"

    def build_tree(self, limit: int = 1000) -> dict:
        """Construit l'arborescence : dossiers (avec sous-dossiers), compteurs,
        urgences, dernière modif. Inclut les dossiers racine et custom même vides."""
        docs = self.list_docs(limit=limit)
        rules = self._rules()
        # node = {count, urgent, last, children:{}}
        roots: dict = {}

        def ensure(path: str):
            parts = path.split("/")
            root = parts[0]
            node = roots.setdefault(root, {"count": 0, "urgent": 0, "last": "", "children": {}})
            if len(parts) > 1:
                node["children"].setdefault(parts[1], {"count": 0, "urgent": 0, "last": ""})
            return node

        # Dossiers toujours visibles
        for r in self.ROOT_FOLDERS:
            ensure(r)
        for cf in self._custom_folders():
            ensure(cf)

        for doc in docs:
            fp = self.folder_for(doc, rules)
            parts = fp.split("/")
            node = ensure(fp)
            created = doc.get("created_at", "") or ""
            urgent = 1 if self._is_urgent(doc) else 0
            node["count"] += 1
            node["urgent"] += urgent
            if created > node["last"]:
                node["last"] = created
            if len(parts) > 1:
                sub = node["children"][parts[1]]
                sub["count"] += 1
                sub["urgent"] += urgent
                if created > sub["last"]:
                    sub["last"] = created

        # Sérialisation ordonnée : racines connues d'abord, puis le reste alpha
        ordered = [r for r in self.ROOT_FOLDERS if r in roots]
        ordered += sorted(k for k in roots if k not in self.ROOT_FOLDERS)
        tree = []
        for name in ordered:
            n = roots[name]
            children = [
                {"name": cn, "path": f"{name}/{cn}", "count": c["count"],
                 "urgent": c["urgent"], "last_modified": c["last"]}
                for cn, c in sorted(n["children"].items())
            ]
            tree.append({
                "name": name, "path": name, "icon": self.FOLDER_ICONS.get(name, "📁"),
                "count": n["count"], "urgent": n["urgent"],
                "last_modified": n["last"], "children": children,
            })
        return {"tree": tree, "total": len(docs)}

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

    # ── Index par type (helpers internes) ─────────────────────────────

    def _get_latest_by_type(self, doc_type: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retourne les N documents les plus récents d'un type donné."""
        type_key = self._k(self._TYPE_KEY, doc_type=doc_type)
        doc_ids = self.rc.client.zrevrange(type_key, 0, limit - 1)
        docs = []
        for did in doc_ids:
            d = self._load_doc(did)
            if d:
                # Désérialise extracted_fields si string JSON
                if isinstance(d.get("extracted_fields"), str):
                    try:
                        d["extracted_fields"] = json.loads(d["extracted_fields"])
                    except Exception:
                        d["extracted_fields"] = {}
                docs.append(d)
        return docs

    @staticmethod
    def _select_best_doc(docs: List[Dict[str, Any]], priority_fields: List[str]) -> Optional[Dict[str, Any]]:
        """Sélectionne le doc le plus récent avec le plus de champs prioritaires remplis."""
        if not docs:
            return None
        scored = []
        for doc in docs:
            fields = doc.get("extracted_fields") or {}
            prio_score = sum(1 for f in priority_fields if fields.get(f))
            confidence = float(doc.get("confidence") or 0)
            date_score = 0.0
            raw_date = doc.get("date_document") or doc.get("created_at") or ""
            if raw_date:
                try:
                    d = datetime.fromisoformat(raw_date[:10])
                    days_old = (datetime.utcnow() - d).days
                    date_score = max(0, 365 - days_old) / 365
                except Exception:
                    pass
            scored.append((prio_score * 3 + confidence * 2 + date_score, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    @staticmethod
    def _completeness(profile: Dict[str, Any]) -> Dict[str, Any]:
        cats = {
            "identity": ["nom", "prenom", "date_naissance", "lieu_naissance", "nationalite", "numero_ci"],
            "address":  ["adresse", "code_postal", "ville"],
            "secu":     ["numero_secu"],
            "fiscal":   ["numero_fiscal", "reference_avis", "annee_revenus"],
            "assurance":["assureur", "numero_contrat", "type_couverture"],
            "banking":  ["iban", "banque"],
        }
        result = {}
        for cat, fields in cats.items():
            data = profile.get(cat) or {}
            filled = sum(1 for f in fields if data.get(f))
            result[cat] = {"filled": filled, "total": len(fields),
                           "percentage": round(filled / len(fields) * 100, 1) if fields else 0}
        total_f = sum(v["total"] for v in result.values())
        total_ok = sum(v["filled"] for v in result.values())
        result["global"] = {"filled": total_ok, "total": total_f,
                            "percentage": round(total_ok / total_f * 100, 1) if total_f else 0}
        return result

    # ── Profil unifié (pont vault → formulaires) ───────────────────────

    def get_profile_data(self) -> Dict[str, Any]:
        """Consolide les champs extraits de tous les documents en un profil structuré.

        Stratégie de priorité : doc le plus récent + meilleure confiance + champs critiques remplis.
        Sources tracées pour chaque catégorie (RGPD).
        """
        profile: Dict[str, Any] = {
            "identity": {}, "address": {}, "secu": {}, "fiscal": {},
            "assurance": {}, "banking": {}, "sources": {},
        }

        # 1. Identité — CNI / passeport / titre_séjour / permis
        identity_docs: List[Dict] = []
        for dt in ("cni", "passeport", "titre_sejour", "permis_conduire"):
            identity_docs.extend(self._get_latest_by_type(dt))
        best = self._select_best_doc(identity_docs, ["nom", "prenom", "date_naissance"])
        if best:
            f = best.get("extracted_fields") or {}
            profile["identity"] = {
                "nom": f.get("nom"), "prenom": f.get("prenom"),
                "nom_naissance": f.get("nom_naissance"),
                "date_naissance": f.get("date_naissance"),
                "lieu_naissance": f.get("lieu_naissance"),
                "departement_naissance": f.get("departement_naissance"),
                "nationalite": f.get("nationalite"), "sexe": f.get("sexe"),
                "numero_ci": (f.get("numero_ci") or f.get("numero_passeport")
                              or f.get("numero_titre") or f.get("numero_permis")),
            }
            profile["sources"]["identity"] = {
                "doc_id": best.get("id"), "doc_type": best.get("doc_type"),
                "titre": best.get("titre"), "confidence": best.get("confidence"),
            }

        # 2. Adresse — facture / facture_energie / avis_imposition / contrat / assurance
        address_docs: List[Dict] = []
        for dt in ("facture", "facture_energie", "avis_imposition", "contrat", "assurance"):
            address_docs.extend(self._get_latest_by_type(dt))
        best = self._select_best_doc(address_docs, ["adresse", "code_postal", "ville"])
        if best:
            f = best.get("extracted_fields") or {}
            profile["address"] = {
                "adresse": f.get("adresse"), "code_postal": f.get("code_postal"),
                "ville": f.get("ville"),
            }
            profile["sources"]["address"] = {
                "doc_id": best.get("id"), "doc_type": best.get("doc_type"),
                "titre": best.get("titre"),
            }

        # 3. Sécurité sociale — carte_vitale
        vitale = self._get_latest_by_type("carte_vitale", limit=1)
        if vitale:
            f = vitale[0].get("extracted_fields") or {}
            profile["secu"] = {
                "numero_secu": f.get("numero_secu"),
                "caisse": f.get("caisse"),
                "rang_naissance": f.get("rang_naissance"),
            }
            profile["sources"]["secu"] = {"doc_id": vitale[0].get("id"), "doc_type": "carte_vitale"}

        # 4. Fiscal — avis_imposition
        fiscal = self._get_latest_by_type("avis_imposition", limit=1)
        if fiscal:
            f = fiscal[0].get("extracted_fields") or {}
            profile["fiscal"] = {
                "numero_fiscal": f.get("numero_fiscal"),
                "reference_avis": f.get("reference_avis"),
                "annee_revenus": f.get("annee_revenus"),
                "revenu_fiscal": f.get("revenu_fiscal"),
                "revenu_reference": f.get("revenu_reference"),
                "nb_parts": f.get("nb_parts"),
                "taux_imposition": f.get("taux_imposition"),
            }
            profile["sources"]["fiscal"] = {"doc_id": fiscal[0].get("id"), "doc_type": "avis_imposition"}

        # 5. Assurance
        assur = self._get_latest_by_type("assurance", limit=1)
        if assur:
            f = assur[0].get("extracted_fields") or {}
            profile["assurance"] = {
                "assureur": f.get("assureur"),
                "numero_contrat": f.get("numero_contrat"),
                "type_couverture": f.get("type_couverture"),
                "date_debut": f.get("date_debut"),
                "date_fin": f.get("date_fin"),
                "montant_prime": f.get("montant_prime"),
                "franchise": f.get("franchise"),
            }
            profile["sources"]["assurance"] = {"doc_id": assur[0].get("id"), "doc_type": "assurance"}

        # 6. Bancaire — relevé
        bank = self._get_latest_by_type("releve_bancaire", limit=1)
        if bank:
            f = bank[0].get("extracted_fields") or {}
            profile["banking"] = {
                "banque": f.get("banque"), "iban": f.get("iban"),
                "bic": f.get("bic"), "numero_compte": f.get("numero_compte"),
            }
            profile["sources"]["banking"] = {"doc_id": bank[0].get("id"), "doc_type": "releve_bancaire"}

        profile["completeness"] = self._completeness(profile)
        profile["last_updated"] = datetime.utcnow().isoformat()
        return profile

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
