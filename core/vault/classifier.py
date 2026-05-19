"""Classification et extraction structurée de documents — Luna Vault.

Prompt unique (gpt-4o) : classification + métadonnées génériques + champs spécifiques par type.
Retourne un dict enrichi compatible avec VaultRedisOps.save_doc().
"""
import json
import logging
import re
from datetime import date, datetime, timedelta
from typing import Optional

logger = logging.getLogger("luna.vault")

# ── Types de documents ────────────────────────────────────────────────────────

DOC_TYPES = {
    "cni": {
        "label": "Carte d'identité", "emoji": "🪪",
        "expiry_years": 10, "reminder_days": [180, 30, 7],
        "fields": ["nom", "prenom", "nom_naissance", "date_naissance", "lieu_naissance",
                   "departement_naissance", "nationalite", "adresse", "code_postal",
                   "ville", "numero_ci", "date_delivrance", "date_expiration", "sexe"],
    },
    "passeport": {
        "label": "Passeport", "emoji": "📔",
        "expiry_years": 10, "reminder_days": [180, 30, 7],
        "fields": ["nom", "prenom", "date_naissance", "lieu_naissance", "nationalite",
                   "numero_passeport", "date_delivrance", "date_expiration", "autorite"],
    },
    "titre_sejour": {
        "label": "Titre de séjour", "emoji": "📄",
        "reminder_days": [180, 30, 7],
        "fields": ["nom", "prenom", "date_naissance", "nationalite", "type_titre",
                   "numero_titre", "date_delivrance", "date_expiration", "prefecture"],
    },
    "permis_conduire": {
        "label": "Permis de conduire", "emoji": "🚗",
        "reminder_days": [30, 7],
        "fields": ["nom", "prenom", "date_naissance", "lieu_naissance",
                   "numero_permis", "categories", "date_delivrance", "date_expiration"],
    },
    "carte_vitale": {
        "label": "Carte Vitale", "emoji": "💳",
        "reminder_days": [30], "sensitive": True,
        "fields": ["nom", "prenom", "date_naissance", "numero_secu",
                   "rang_naissance", "caisse", "date_validite"],
    },
    "ordonnance": {
        "label": "Ordonnance médicale", "emoji": "💊",
        "reminder_days": [7, 1], "sensitive": True,
        "fields": ["nom_patient", "prenom_patient", "date_naissance_patient",
                   "medecin", "numero_rpps", "date_ordonnance", "medicaments",
                   "duree_traitement", "renouvellement"],
    },
    "facture": {
        "label": "Facture", "emoji": "🧾",
        "reminder_days": [7, 1],
        "fields": ["nom", "adresse", "code_postal", "ville", "fournisseur",
                   "numero_client", "numero_facture", "date_emission", "date_echeance",
                   "montant_ht", "montant_ttc", "tva", "mode_paiement"],
    },
    "facture_energie": {
        "label": "Facture énergie", "emoji": "⚡",
        "reminder_days": [7, 1],
        "fields": ["nom", "adresse", "code_postal", "ville", "fournisseur",
                   "numero_client", "numero_facture", "date_debut_periode", "date_fin_periode",
                   "date_emission", "date_echeance", "montant_ttc", "consommation_kwh", "mode_paiement"],
    },
    "releve_bancaire": {
        "label": "Relevé bancaire", "emoji": "🏦",
        "reminder_days": [], "sensitive": True,
        "fields": ["nom", "prenom", "banque", "numero_compte", "iban", "bic",
                   "date_debut", "date_fin", "solde"],
    },
    "avis_imposition": {
        "label": "Avis d'imposition", "emoji": "📊",
        "reminder_days": [30], "sensitive": True,
        "fields": ["nom", "prenom", "adresse", "code_postal", "ville",
                   "numero_fiscal", "reference_avis", "annee_revenus", "revenu_fiscal",
                   "revenu_reference", "nb_parts", "taux_imposition", "date_emission"],
    },
    "contrat": {
        "label": "Contrat / Bail", "emoji": "📝",
        "reminder_days": [30],
        "fields": ["type_contrat", "nom", "prenom", "adresse", "code_postal", "ville",
                   "parties", "objet", "date_signature", "date_debut", "date_fin",
                   "montant", "periodicite"],
    },
    "assurance": {
        "label": "Attestation assurance", "emoji": "🛡️",
        "reminder_days": [30, 7],
        "fields": ["nom", "prenom", "adresse", "assureur", "numero_contrat",
                   "type_couverture", "date_debut", "date_fin", "montant_prime", "franchise"],
    },
    "courrier_admin": {
        "label": "Courrier administratif", "emoji": "✉️",
        "reminder_days": [7],
        "fields": ["expediteur", "objet", "reference", "date_courrier",
                   "action_requise", "date_reponse", "pieces_jointes_requises"],
    },
    "diplome": {
        "label": "Diplôme / Certificat", "emoji": "🎓",
        "reminder_days": [],
        "fields": ["nom", "prenom", "diplome", "etablissement", "specialite",
                   "niveau", "date_obtention", "numero_diplome", "mention"],
    },
    "autre": {
        "label": "Autre document", "emoji": "📎",
        "reminder_days": [], "fields": [],
    },
}

# ── Prompts spécifiques par type ──────────────────────────────────────────────

_FIELD_PROMPTS = {
    "cni": "nom(MAJUSCULES) prenom nom_naissance date_naissance(YYYY-MM-DD) lieu_naissance departement_naissance nationalite adresse code_postal ville numero_ci date_delivrance(YYYY-MM-DD) date_expiration(YYYY-MM-DD) sexe(M/F)",
    "passeport": "nom prenom date_naissance(YYYY-MM-DD) lieu_naissance nationalite numero_passeport date_delivrance(YYYY-MM-DD) date_expiration(YYYY-MM-DD) autorite",
    "titre_sejour": "nom prenom date_naissance(YYYY-MM-DD) nationalite type_titre numero_titre date_delivrance(YYYY-MM-DD) date_expiration(YYYY-MM-DD) prefecture",
    "permis_conduire": "nom prenom date_naissance(YYYY-MM-DD) lieu_naissance numero_permis categories(liste) date_delivrance(YYYY-MM-DD) date_expiration(YYYY-MM-DD)",
    "carte_vitale": "nom prenom date_naissance(YYYY-MM-DD) numero_secu(15 chiffres) rang_naissance caisse date_validite(YYYY-MM-DD)",
    "ordonnance": "nom_patient prenom_patient date_naissance_patient(YYYY-MM-DD) medecin numero_rpps date_ordonnance(YYYY-MM-DD) medicaments(liste) duree_traitement renouvellement",
    "facture": "nom adresse code_postal ville fournisseur numero_client numero_facture date_emission(YYYY-MM-DD) date_echeance(YYYY-MM-DD) montant_ht montant_ttc tva mode_paiement",
    "facture_energie": "nom adresse code_postal ville fournisseur numero_client numero_facture date_debut_periode(YYYY-MM-DD) date_fin_periode(YYYY-MM-DD) date_emission(YYYY-MM-DD) date_echeance(YYYY-MM-DD) montant_ttc consommation_kwh mode_paiement",
    "releve_bancaire": "nom prenom banque numero_compte iban bic date_debut(YYYY-MM-DD) date_fin(YYYY-MM-DD) solde",
    "avis_imposition": "nom prenom adresse code_postal ville numero_fiscal reference_avis annee_revenus revenu_fiscal revenu_reference nb_parts taux_imposition date_emission(YYYY-MM-DD)",
    "contrat": "type_contrat nom prenom adresse code_postal ville parties(liste) objet date_signature(YYYY-MM-DD) date_debut(YYYY-MM-DD) date_fin(YYYY-MM-DD) montant periodicite",
    "assurance": "nom prenom adresse assureur numero_contrat type_couverture date_debut(YYYY-MM-DD) date_fin(YYYY-MM-DD) montant_prime franchise",
    "courrier_admin": "expediteur objet reference date_courrier(YYYY-MM-DD) action_requise date_reponse(YYYY-MM-DD) pieces_jointes_requises(liste)",
    "diplome": "nom prenom diplome etablissement specialite niveau date_obtention(YYYY-MM-DD) numero_diplome mention",
}

_FIELDS_SECTION = "\n".join(f"- {k}: {v}" for k, v in _FIELD_PROMPTS.items())

_CLASSIFY_PROMPT = f"""Tu es un expert OCR de documents administratifs français.
Analyse cette image et retourne UNIQUEMENT un JSON valide (sans markdown).

Structure exacte attendue :
{{
  "doc_type": "cni|passeport|titre_sejour|permis_conduire|carte_vitale|ordonnance|facture|facture_energie|releve_bancaire|avis_imposition|contrat|assurance|courrier_admin|diplome|autre",
  "titre": "titre court (max 60 chars)",
  "emetteur": "organisme émetteur ou null",
  "date_document": "YYYY-MM-DD ou null",
  "date_expiration": "YYYY-MM-DD ou null",
  "montant": "montant principal ou null",
  "reference": "numéro de référence principal ou null",
  "notes": "observations importantes ou null",
  "confidence": 0.85,
  "extracted_fields": {{
    "champ1": "valeur ou null",
    "champ2": "valeur ou null"
  }}
}}

Champs spécifiques à extraire selon le type détecté :
{_FIELDS_SECTION}

RÈGLES CRITIQUES :
- Ne jamais inventer une valeur. Si incertain à plus de 10%, mets null.
- extracted_fields : extrais UNIQUEMENT les champs correspondant au doc_type détecté.
- confidence : score 0.0–1.0 basé sur la lisibilité et la complétude.
- Dates toujours en YYYY-MM-DD ou null.
- Réponds UNIQUEMENT en JSON valide."""

# ── Champs critiques par type (pour calcul confiance) ────────────────────────

_CRITICAL_FIELDS = {
    "cni":            ["nom", "prenom", "date_naissance", "numero_ci"],
    "passeport":      ["nom", "prenom", "numero_passeport"],
    "carte_vitale":   ["nom", "prenom", "numero_secu"],
    "avis_imposition":["nom", "numero_fiscal", "reference_avis"],
    "facture":        ["fournisseur", "montant_ttc", "date_emission"],
    "facture_energie":["fournisseur", "montant_ttc", "date_emission"],
    "assurance":      ["assureur", "numero_contrat", "type_couverture"],
}

# ── Utilitaires ───────────────────────────────────────────────────────────────

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
                "priority": "high" if days_before <= 7 else "medium" if days_before <= 30 else "low",
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


def _validate_extracted_fields(doc_type: str, fields: dict) -> dict:
    """Nettoie et valide les champs extraits selon le type."""
    expected = DOC_TYPES.get(doc_type, {}).get("fields", [])
    validated = {}
    for field in expected:
        value = fields.get(field)
        if isinstance(value, str):
            value = value.strip()
            if not value or value.lower() in ("null", "none", "n/a", "-", ""):
                value = None
        elif isinstance(value, list) and len(value) == 0:
            value = None
        validated[field] = value
    # Conserver les champs inattendus mais présents
    for k, v in fields.items():
        if k not in validated:
            validated[k] = v
    return validated


def _compute_confidence(doc_type: str, fields: dict, llm_confidence: float) -> float:
    """Recalcule la confiance — prend le min entre LLM et score champs critiques."""
    expected = DOC_TYPES.get(doc_type, {}).get("fields", [])
    if not expected:
        return round(min(llm_confidence, 0.5), 2)

    filled = sum(1 for f in expected if fields.get(f) is not None)
    base = filled / len(expected)

    crits = _CRITICAL_FIELDS.get(doc_type, [])
    if crits:
        crit_filled = sum(1 for c in crits if fields.get(c) is not None)
        crit_ratio = crit_filled / len(crits)
        computed = round(0.6 * crit_ratio + 0.4 * base, 2)
    else:
        computed = round(base, 2)

    return round(min(llm_confidence, computed), 2)


# ── Fonction principale ───────────────────────────────────────────────────────

async def classify_document(
    image_b64: str,
    media_type: str,
    llm_client,
    vision_model: str = "gpt-4o",
) -> dict:
    """Classifie le document et extrait les champs structurés.

    Retourne un dict compatible avec VaultRedisOps.save_doc().
    Nouveaux champs vs ancienne version : extracted_fields, confidence,
    profile_update_available, profile_fields.
    """
    try:
        data_uri = f"data:{media_type};base64,{image_b64}"
        resp = llm_client.chat.completions.create(
            model=vision_model,
            messages=[
                {
                    "role": "system",
                    "content": "Tu analyses des documents administratifs français. Tu réponds uniquement en JSON valide.",
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _CLASSIFY_PROMPT},
                        {"type": "image_url", "image_url": {"url": data_uri, "detail": "high"}},
                    ],
                },
            ],
            max_tokens=1500,
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or "{}"

        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r"\{[\s\S]*\}", raw)
            result = json.loads(m.group(0)) if m else {}

        # Normalise doc_type
        doc_type = str(result.get("doc_type", "autre")).lower().strip()
        if doc_type not in DOC_TYPES:
            doc_type = "autre"
        result["doc_type"] = doc_type

        # Extrait et valide les champs structurés
        raw_fields = result.get("extracted_fields", {})
        if not isinstance(raw_fields, dict):
            raw_fields = {}
        extracted_fields = _validate_extracted_fields(doc_type, raw_fields)

        # Confiance
        llm_conf = float(result.get("confidence", 0.5))
        if not (0.0 <= llm_conf <= 1.0):
            llm_conf = 0.5
        confidence = _compute_confidence(doc_type, extracted_fields, llm_conf)

        # Fallback confiance trop basse
        if confidence < 0.25 and doc_type != "autre":
            logger.warning(f"Vault classify: confiance {confidence} trop basse pour {doc_type}, fallback=autre")
            doc_type = "autre"
            extracted_fields = {}
            result["doc_type"] = "autre"

        # Dates
        expiry = _parse_date(result.get("date_expiration"))
        result["date_expiration"] = expiry.isoformat() if expiry else None
        result["reminders"] = compute_reminders(doc_type, expiry)

        # Labels
        result["is_sensitive"] = DOC_TYPES.get(doc_type, {}).get("sensitive", False)
        result["doc_label"] = DOC_TYPES.get(doc_type, {}).get("label", "Document")
        result["doc_emoji"] = DOC_TYPES.get(doc_type, {}).get("emoji", "📎")

        # Expiry status
        if expiry:
            delta = (expiry - date.today()).days
            result["expires_in_days"] = delta
            result["expiry_status"] = (
                "expired" if delta < 0 else
                "urgent"  if delta <= 7 else
                "warning" if delta <= 30 else "ok"
            )
        else:
            result["expires_in_days"] = None
            result["expiry_status"] = "none"

        # Champs structurés + confiance
        result["extracted_fields"] = extracted_fields
        result["confidence"] = confidence

        # Pont vers profil identité
        _IDENTITY_DOC_TYPES = {"cni", "passeport", "titre_sejour", "permis_conduire"}
        _IDENTITY_KEYS = {
            "nom", "prenom", "nom_naissance", "date_naissance", "lieu_naissance",
            "departement_naissance", "nationalite", "adresse", "code_postal",
            "ville", "numero_ci", "numero_passeport", "numero_permis",
        }
        if doc_type in _IDENTITY_DOC_TYPES:
            profile_fields = {
                k: v for k, v in extracted_fields.items()
                if k in _IDENTITY_KEYS and v is not None
            }
            result["profile_update_available"] = bool(profile_fields)
            result["profile_fields"] = profile_fields
        else:
            result["profile_update_available"] = False
            result["profile_fields"] = {}

        # Titre par défaut
        if not result.get("titre"):
            result["titre"] = result["doc_label"]

        logger.info(
            f"Vault classify: type={doc_type} confidence={confidence} "
            f"fields={len(extracted_fields)} profile_update={result['profile_update_available']}"
        )
        return result

    except Exception as e:
        logger.error(f"Vault classify error: {e}")
        return {
            "doc_type": "autre", "doc_label": "Document", "doc_emoji": "📎",
            "titre": "Document non reconnu", "emetteur": None,
            "date_document": None, "date_expiration": None,
            "montant": None, "reference": None, "notes": str(e),
            "reminders": [], "is_sensitive": False,
            "expires_in_days": None, "expiry_status": "none",
            "extracted_fields": {}, "confidence": 0.0,
            "profile_update_available": False, "profile_fields": {},
        }
