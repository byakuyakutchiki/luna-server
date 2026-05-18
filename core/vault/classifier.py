"""Classification et extraction de métadonnées de documents."""
import json
import logging
import re
from datetime import date, datetime, timedelta
from typing import Optional

logger = logging.getLogger("luna.vault")

# Types de documents reconnus
DOC_TYPES = {
    "cni": {"label": "Carte d'identité", "emoji": "🪪", "expiry_years": 10, "reminder_days": [180, 30, 7]},
    "passeport": {"label": "Passeport", "emoji": "📔", "expiry_years": 10, "reminder_days": [180, 30, 7]},
    "titre_sejour": {"label": "Titre de séjour", "emoji": "📄", "reminder_days": [180, 30, 7]},
    "permis_conduire": {"label": "Permis de conduire", "emoji": "🚗", "reminder_days": [30, 7]},
    "carte_vitale": {"label": "Carte Vitale", "emoji": "💳", "reminder_days": [30]},
    "ordonnance": {"label": "Ordonnance médicale", "emoji": "💊", "sensitive": True, "reminder_days": [7, 1]},
    "facture": {"label": "Facture", "emoji": "🧾", "reminder_days": [7, 1]},
    "facture_energie": {"label": "Facture énergie", "emoji": "⚡", "reminder_days": [7, 1]},
    "releve_bancaire": {"label": "Relevé bancaire", "emoji": "🏦", "sensitive": True, "reminder_days": []},
    "avis_imposition": {"label": "Avis d'imposition", "emoji": "📊", "reminder_days": [30]},
    "contrat": {"label": "Contrat / Bail", "emoji": "📝", "reminder_days": [30]},
    "assurance": {"label": "Attestation assurance", "emoji": "🛡️", "reminder_days": [30, 7]},
    "courrier_admin": {"label": "Courrier administratif", "emoji": "✉️", "reminder_days": [7]},
    "diplome": {"label": "Diplôme / Certificat", "emoji": "🎓", "reminder_days": []},
    "autre": {"label": "Autre document", "emoji": "📎", "reminder_days": []},
}

_CLASSIFY_PROMPT = """Tu es un assistant qui analyse des documents administratifs français.

Analyse cette image et retourne un JSON avec ces clés exactes :

{
  "doc_type": "cni|passeport|titre_sejour|permis_conduire|carte_vitale|ordonnance|facture|facture_energie|releve_bancaire|avis_imposition|contrat|assurance|courrier_admin|diplome|autre",
  "titre": "titre court du document (ex: CNI Jean DUPONT, Facture EDF mars 2026)",
  "emetteur": "qui a émis ce document (ex: République Française, EDF, CPAM...)",
  "date_document": "YYYY-MM-DD ou null — date du document",
  "date_expiration": "YYYY-MM-DD ou null — date d'expiration ou d'échéance",
  "montant": "string ou null — montant si applicable (ex: 87.50€)",
  "reference": "string ou null — numéro de référence/facture",
  "notes": "string ou null — informations importantes à retenir"
}

RÈGLES :
- doc_type doit être EXACTEMENT une des valeurs listées
- Pour les factures : date_expiration = date limite de paiement
- Pour les ordonnances : date_expiration = date de validité (30 jours après date si non précisée)
- Pour CNI/passeport : calcule date_expiration depuis date de délivrance + durée validité
- Réponds UNIQUEMENT en JSON valide, pas de markdown"""


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def compute_reminders(doc_type: str, expiry_date: Optional[date]) -> list[dict]:
    """Calcule les dates de rappel à partir de la date d'expiration."""
    if not expiry_date:
        return []
    cfg = DOC_TYPES.get(doc_type, {})
    reminders = []
    for days_before in cfg.get("reminder_days", []):
        reminder_date = expiry_date - timedelta(days=days_before)
        if reminder_date >= date.today():
            reminders.append({
                "date": reminder_date.isoformat(),
                "days_before": days_before,
                "message": _reminder_message(doc_type, days_before, expiry_date),
            })
    return reminders


def _reminder_message(doc_type: str, days_before: int, expiry: date) -> str:
    label = DOC_TYPES.get(doc_type, {}).get("label", "Document")
    emoji = DOC_TYPES.get(doc_type, {}).get("emoji", "📄")
    if days_before == 1:
        return f"{emoji} {label} — échéance DEMAIN ({expiry.strftime('%d/%m/%Y')})"
    elif days_before <= 7:
        return f"{emoji} {label} — échéance dans {days_before} jours ({expiry.strftime('%d/%m/%Y')})"
    elif days_before <= 30:
        return f"{emoji} {label} expire dans {days_before} jours — pensez à le renouveler"
    else:
        m = days_before // 30
        return f"{emoji} {label} expire dans environ {m} mois ({expiry.strftime('%d/%m/%Y')})"


async def classify_document(image_b64: str, media_type: str, llm_client, vision_model: str = "gpt-4o") -> dict:
    """Envoie l'image au LLM pour classification et extraction."""
    try:
        data_uri = f"data:{media_type};base64,{image_b64}"
        resp = llm_client.chat.completions.create(
            model=vision_model,
            messages=[
                {"role": "system", "content": "Tu analyses des documents administratifs français. Tu réponds uniquement en JSON valide."},
                {"role": "user", "content": [
                    {"type": "text", "text": _CLASSIFY_PROMPT},
                    {"type": "image_url", "image_url": {"url": data_uri, "detail": "high"}},
                ]},
            ],
            max_tokens=600,
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or "{}"
        result = json.loads(raw)

        # Normalise le type
        doc_type = result.get("doc_type", "autre")
        if doc_type not in DOC_TYPES:
            doc_type = "autre"
        result["doc_type"] = doc_type

        # Parse les dates
        expiry = _parse_date(result.get("date_expiration"))
        result["date_expiration"] = expiry.isoformat() if expiry else None
        result["reminders"] = compute_reminders(doc_type, expiry)
        result["is_sensitive"] = DOC_TYPES.get(doc_type, {}).get("sensitive", False)
        result["doc_label"] = DOC_TYPES.get(doc_type, {}).get("label", "Document")
        result["doc_emoji"] = DOC_TYPES.get(doc_type, {}).get("emoji", "📎")

        # Expiration status
        if expiry:
            delta = (expiry - date.today()).days
            result["expires_in_days"] = delta
            result["expiry_status"] = "expired" if delta < 0 else "urgent" if delta <= 7 else "warning" if delta <= 30 else "ok"
        else:
            result["expires_in_days"] = None
            result["expiry_status"] = "none"

        return result

    except Exception as e:
        logger.error(f"Vault classify error: {e}")
        return {
            "doc_type": "autre",
            "doc_label": "Document",
            "doc_emoji": "📎",
            "titre": "Document non reconnu",
            "emetteur": None,
            "date_document": None,
            "date_expiration": None,
            "montant": None,
            "reference": None,
            "notes": str(e),
            "reminders": [],
            "is_sensitive": False,
            "expires_in_days": None,
            "expiry_status": "none",
        }
