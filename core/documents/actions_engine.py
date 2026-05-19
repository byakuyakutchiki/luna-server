"""
Luna Documents v2 — Actions Engine
Analyse les documents du vault et génère des actions intelligentes prioritisées.
"""
import json
import logging
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
import uuid

logger = logging.getLogger("luna.documents.actions")

# ── Priorités ─────────────────────────────────────────────────────────────────

PRIORITY_HIGH   = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW    = "low"

# ── Templates d'actions par type de document ─────────────────────────────────

_ACTION_TEMPLATES: Dict[str, List[Dict]] = {
    "facture": [
        {"type": "pay",     "label": "Payer avant échéance",    "icon": "◈", "auto": True},
        {"type": "contest", "label": "Contester la facture",     "icon": "◇", "auto": True},
        {"type": "explain", "label": "Expliquer ce document",    "icon": "◐", "auto": True},
    ],
    "facture_energie": [
        {"type": "pay",    "label": "Payer avant échéance",      "icon": "◈", "auto": True},
        {"type": "switch", "label": "Comparer les offres",        "icon": "◇", "auto": False},
        {"type": "explain","label": "Expliquer ma consommation", "icon": "◐", "auto": True},
    ],
    "courrier_admin": [
        {"type": "email",   "label": "Rédiger une réponse",      "icon": "◫", "auto": True},
        {"type": "remind",  "label": "Créer un rappel",           "icon": "◈", "auto": True},
        {"type": "explain", "label": "Expliquer ce courrier",     "icon": "◐", "auto": True},
    ],
    "cni": [
        {"type": "renew",   "label": "Préparer le renouvellement","icon": "◈", "auto": True},
        {"type": "form",    "label": "Pré-remplir un formulaire", "icon": "◫", "auto": True},
    ],
    "passeport": [
        {"type": "renew",   "label": "Préparer le renouvellement","icon": "◈", "auto": True},
        {"type": "form",    "label": "Pré-remplir un formulaire", "icon": "◫", "auto": True},
    ],
    "titre_sejour": [
        {"type": "renew",   "label": "Préparer le renouvellement","icon": "◈", "auto": True},
        {"type": "email",   "label": "Contacter la préfecture",   "icon": "◫", "auto": True},
    ],
    "permis_conduire": [
        {"type": "renew",   "label": "Préparer le renouvellement","icon": "◈", "auto": True},
    ],
    "ordonnance": [
        {"type": "remind",  "label": "Rappel de prise de médicament","icon": "◈", "auto": True},
        {"type": "renew",   "label": "Renouveler l'ordonnance",   "icon": "◇", "auto": False},
        {"type": "call",    "label": "Appeler la pharmacie",       "icon": "◐", "auto": False},
    ],
    "avis_imposition": [
        {"type": "explain", "label": "Expliquer mon avis",         "icon": "◐", "auto": True},
        {"type": "email",   "label": "Contacter les impôts",       "icon": "◫", "auto": True},
    ],
    "assurance": [
        {"type": "renew",   "label": "Renouveler l'assurance",     "icon": "◈", "auto": False},
        {"type": "email",   "label": "Contacter l'assureur",       "icon": "◫", "auto": True},
        {"type": "claim",   "label": "Déclarer un sinistre",       "icon": "◇", "auto": False},
    ],
    "contrat": [
        {"type": "explain", "label": "Résumer le contrat",         "icon": "◐", "auto": True},
        {"type": "remind",  "label": "Rappel fin de contrat",      "icon": "◈", "auto": True},
        {"type": "cancel",  "label": "Préparer une résiliation",   "icon": "◇", "auto": True},
    ],
    "releve_bancaire": [
        {"type": "explain", "label": "Analyser mes dépenses",      "icon": "◐", "auto": True},
    ],
    "carte_vitale": [
        {"type": "explain", "label": "Infos sur ma couverture",    "icon": "◐", "auto": True},
    ],
    "diplome": [
        {"type": "explain", "label": "Résumer ce diplôme",         "icon": "◐", "auto": True},
    ],
    "autre": [
        {"type": "explain", "label": "Expliquer ce document",      "icon": "◐", "auto": True},
        {"type": "remind",  "label": "Créer un rappel",            "icon": "◈", "auto": True},
    ],
}

# ── Calcul de priorité ────────────────────────────────────────────────────────

def _days_until(date_str: Optional[str]) -> Optional[int]:
    if not date_str:
        return None
    try:
        d = date.fromisoformat(str(date_str)[:10])
        return (d - date.today()).days
    except (ValueError, TypeError):
        return None


def _compute_priority(doc: dict) -> str:
    doc_type = doc.get("doc_type", "autre")
    ef = doc.get("extracted_fields") or {}
    if isinstance(ef, str):
        try:
            ef = json.loads(ef)
        except Exception:
            ef = {}

    # Échéance de paiement imminente (factures)
    if doc_type in ("facture", "facture_energie"):
        days = _days_until(ef.get("date_echeance") or doc.get("date_expiration"))
        if days is not None:
            if days < 0:   return PRIORITY_HIGH   # en retard
            if days <= 7:  return PRIORITY_HIGH
            if days <= 30: return PRIORITY_MEDIUM
        return PRIORITY_LOW

    # Documents qui expirent
    exp = doc.get("date_expiration") or ef.get("date_expiration") or ef.get("date_fin")
    if exp:
        days = _days_until(exp)
        if days is not None:
            if days < 0:    return PRIORITY_HIGH
            if days <= 30:  return PRIORITY_HIGH
            if days <= 180: return PRIORITY_MEDIUM
        return PRIORITY_LOW

    # Courrier avec date de réponse
    if doc_type == "courrier_admin":
        days = _days_until(ef.get("date_reponse"))
        if days is not None:
            if days <= 7:  return PRIORITY_HIGH
            if days <= 30: return PRIORITY_MEDIUM
        return PRIORITY_MEDIUM  # tout courrier admin = au moins medium

    # Ordonnance: toujours priorité medium+
    if doc_type == "ordonnance":
        return PRIORITY_MEDIUM

    return PRIORITY_LOW


def _urgency_label(doc: dict) -> Optional[str]:
    doc_type = doc.get("doc_type", "autre")
    ef = doc.get("extracted_fields") or {}
    if isinstance(ef, str):
        try: ef = json.loads(ef)
        except: ef = {}

    if doc_type in ("facture", "facture_energie"):
        d = ef.get("date_echeance") or doc.get("date_expiration")
        days = _days_until(d)
        if days is not None:
            if days < 0:  return f"{abs(days)}j de retard"
            if days == 0: return "Aujourd'hui"
            return f"dans {days}j"
        montant = ef.get("montant_ttc") or doc.get("montant")
        if montant: return f"{montant}€"

    exp = doc.get("date_expiration") or ef.get("date_expiration") or ef.get("date_fin")
    if exp:
        days = _days_until(exp)
        if days is not None:
            if days < 0:  return f"Expiré il y a {abs(days)}j"
            if days <= 30: return f"Expire dans {days}j"
            if days <= 180: return f"Expire dans {days//30}mois"
    return None


# ── Génération d'actions ─────────────────────────────────────────────────────

def generate_actions(doc: dict) -> List[Dict]:
    """
    Retourne la liste des actions suggérées pour un document.
    Chaque action : {id, type, label, icon, priority, urgency_label, auto, doc_id}
    """
    doc_type = doc.get("doc_type", "autre")
    doc_id = doc.get("id") or doc.get("doc_id", "")
    priority = _compute_priority(doc)
    urgency = _urgency_label(doc)
    templates = _ACTION_TEMPLATES.get(doc_type, _ACTION_TEMPLATES["autre"])

    actions = []
    for tpl in templates:
        actions.append({
            "id": f"act_{uuid.uuid4().hex[:10]}",
            "type": tpl["type"],
            "label": tpl["label"],
            "icon": tpl["icon"],
            "priority": priority,
            "urgency_label": urgency,
            "auto": tpl["auto"],
            "doc_id": doc_id,
            "doc_type": doc_type,
            "doc_title": doc.get("titre", "Document"),
            "doc_emetteur": doc.get("emetteur"),
        })
    return actions


# ── Dashboard ─────────────────────────────────────────────────────────────────

def build_dashboard(docs: List[dict]) -> Dict:
    """
    Agrège tous les documents → retourne le dashboard complet.
    """
    all_actions = []
    for doc in docs:
        all_actions.extend(generate_actions(doc))

    # Tri: high first, puis medium, puis low
    _order = {PRIORITY_HIGH: 0, PRIORITY_MEDIUM: 1, PRIORITY_LOW: 2}
    all_actions.sort(key=lambda a: _order.get(a["priority"], 2))

    urgent  = [a for a in all_actions if a["priority"] == PRIORITY_HIGH]
    medium  = [a for a in all_actions if a["priority"] == PRIORITY_MEDIUM]
    low     = [a for a in all_actions if a["priority"] == PRIORITY_LOW]

    # Catégories avec compteurs
    from core.vault.classifier import DOC_TYPES
    cats: Dict[str, Dict] = {}
    for doc in docs:
        t = doc.get("doc_type", "autre")
        if t not in cats:
            cats[t] = {
                "id": t,
                "label": DOC_TYPES.get(t, {}).get("label", t.replace("_", " ").title()),
                "count": 0,
                "urgent": 0,
            }
        cats[t]["count"] += 1
        if _compute_priority(doc) == PRIORITY_HIGH:
            cats[t]["urgent"] += 1

    # Résumé IA (sans LLM — généré localement)
    summary = _local_summary(urgent, medium, len(docs))

    return {
        "urgent_count":  len(urgent),
        "pending_count": len(medium),
        "total_docs":    len(docs),
        "total_actions": len(all_actions),
        "actions":       all_actions[:20],  # top 20
        "urgent_actions": urgent[:6],
        "categories":    list(cats.values()),
        "summary":       summary,
        "generated_at":  datetime.utcnow().isoformat(),
    }


def _local_summary(urgent: List, medium: List, total: int) -> str:
    if not urgent and not medium:
        if total == 0:
            return "Aucun document dans votre coffre-fort. Commencez par scanner un document."
        return f"{total} document(s) analysé(s). Tout est en ordre."

    parts = []
    if urgent:
        labels = list({a["doc_title"] for a in urgent[:3]})
        parts.append(f"{len(urgent)} action(s) urgente(s) : {', '.join(labels)}")
    if medium:
        parts.append(f"{len(medium)} à traiter prochainement")

    return ". ".join(parts) + "."


# ── Exécution d'action ────────────────────────────────────────────────────────

def execute_action(action_type: str, doc: dict, openai_client=None) -> Dict:
    """
    Exécute une action et retourne le résultat.
    """
    ef = doc.get("extracted_fields") or {}
    if isinstance(ef, str):
        try: ef = json.loads(ef)
        except: ef = {}

    doc_type = doc.get("doc_type", "autre")
    titre = doc.get("titre", "Ce document")
    emetteur = doc.get("emetteur", "")

    if action_type == "explain":
        return _action_explain(doc, ef, openai_client)

    if action_type == "email":
        return _action_email(doc, ef, openai_client)

    if action_type == "remind":
        return _action_remind(doc, ef)

    if action_type == "pay":
        return _action_pay(doc, ef)

    if action_type == "renew":
        return _action_renew(doc, ef)

    if action_type == "form":
        return {"type": "form", "message": "Redirection vers le pré-remplissage de formulaire",
                "redirect": "/formulaires"}

    if action_type == "call":
        target = emetteur or "l'organisme concerné"
        return {"type": "call", "message": f"Appel suggéré à : {target}",
                "phone_hint": emetteur}

    if action_type in ("contest", "cancel", "switch", "claim"):
        return _action_draft(action_type, doc, ef, openai_client)

    return {"type": action_type, "message": "Action prise en compte."}


def _action_explain(doc: dict, ef: dict, llm=None) -> Dict:
    if llm:
        try:
            prompt = (
                f"Explique ce document en langage simple (3-4 phrases max) :\n"
                f"Type: {doc.get('doc_type')}\n"
                f"Titre: {doc.get('titre')}\n"
                f"Émetteur: {doc.get('emetteur')}\n"
                f"Champs: {json.dumps({k:v for k,v in ef.items() if v}, ensure_ascii=False)[:400]}\n"
                f"Réponds en français, de façon bienveillante et claire."
            )
            resp = llm.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200, temperature=0.4,
            )
            return {"type": "explain", "explanation": resp.choices[0].message.content.strip()}
        except Exception as e:
            logger.warning(f"LLM explain failed: {e}")

    # Fallback local
    notes = [f"Document : {doc.get('titre', 'Sans titre')}"]
    if doc.get("emetteur"): notes.append(f"Émis par {doc['emetteur']}")
    if doc.get("date_document"): notes.append(f"Date : {doc['date_document']}")
    if doc.get("date_expiration"): notes.append(f"Expire : {doc['date_expiration']}")
    if doc.get("montant"): notes.append(f"Montant : {doc['montant']} €")
    return {"type": "explain", "explanation": " · ".join(notes)}


def _action_email(doc: dict, ef: dict, llm=None) -> Dict:
    objet = ef.get("objet") or f"Re: {doc.get('titre', 'votre courrier')}"
    emetteur = doc.get("emetteur") or "l'organisme"
    nom = ef.get("nom") or ef.get("nom_patient") or ""
    if llm:
        try:
            prompt = (
                f"Rédige un email de réponse court et professionnel en français.\n"
                f"Document: {doc.get('titre')}\nÉmetteur: {emetteur}\nObjet: {objet}\n"
                f"Action requise: {ef.get('action_requise', 'répondre')}\n"
                f"Nom: {nom}\nÉcris uniquement l'email (objet + corps), sans explication."
            )
            resp = llm.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300, temperature=0.3,
            )
            body = resp.choices[0].message.content.strip()
            return {"type": "email", "subject": f"Réponse — {objet}", "body": body,
                    "to_hint": emetteur}
        except Exception as e:
            logger.warning(f"LLM email failed: {e}")

    body = (
        f"Madame, Monsieur,\n\n"
        f"Suite à votre courrier concernant « {objet} », "
        f"je vous contacte afin de donner suite à votre demande.\n\n"
        f"[Complétez votre réponse ici]\n\n"
        f"Cordialement,\n{nom}"
    )
    return {"type": "email", "subject": f"Réponse — {objet}", "body": body, "to_hint": emetteur}


def _action_remind(doc: dict, ef: dict) -> Dict:
    exp = doc.get("date_expiration") or ef.get("date_echeance") or ef.get("date_reponse")
    if exp:
        days = _days_until(exp)
        msg = f"Rappel pour « {doc.get('titre', 'document')} » le {exp}"
        if days and days > 0:
            msg += f" (dans {days} jour(s))"
        return {"type": "remind", "message": msg, "date": exp, "created": True}
    return {"type": "remind", "message": "Rappel créé pour ce document.", "created": True}


def _action_pay(doc: dict, ef: dict) -> Dict:
    montant = ef.get("montant_ttc") or doc.get("montant")
    echeance = ef.get("date_echeance") or doc.get("date_expiration")
    mode = ef.get("mode_paiement", "virement/prélèvement")
    return {
        "type": "pay",
        "amount": montant,
        "due_date": echeance,
        "payment_method": mode,
        "message": f"Paiement de {montant or '?'}€ à effectuer avant le {echeance or '?'} par {mode}.",
    }


def _action_renew(doc: dict, ef: dict) -> Dict:
    exp = doc.get("date_expiration") or ef.get("date_expiration") or ef.get("date_fin")
    days = _days_until(exp)
    msg = f"Renouvellement de « {doc.get('titre', 'document')} »"
    if exp: msg += f" avant le {exp}"
    if days and days < 0: msg += " — EXPIRÉ"
    return {"type": "renew", "message": msg, "expiry": exp, "days_remaining": days}


def _action_draft(action_type: str, doc: dict, ef: dict, llm=None) -> Dict:
    labels = {"contest": "contester", "cancel": "résilier", "switch": "changer d'offre", "claim": "déclarer un sinistre"}
    verb = labels.get(action_type, action_type)
    if llm:
        try:
            prompt = (
                f"Rédige un courrier court pour {verb} en lien avec ce document :\n"
                f"Type: {doc.get('doc_type')}, Titre: {doc.get('titre')}, Émetteur: {doc.get('emetteur')}\n"
                f"Champs: {json.dumps({k:v for k,v in ef.items() if v}, ensure_ascii=False)[:300]}\n"
                f"Courrier en français, professionnel, 3-4 paragraphes max."
            )
            resp = llm.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=350, temperature=0.3,
            )
            return {"type": action_type, "draft": resp.choices[0].message.content.strip()}
        except Exception as e:
            logger.warning(f"LLM draft {action_type} failed: {e}")
    return {"type": action_type,
            "draft": f"[Modèle de courrier pour {verb} — {doc.get('titre', 'ce document')}]\n\nMadame, Monsieur,\n\n[Complétez ici]\n\nCordialement,"}
