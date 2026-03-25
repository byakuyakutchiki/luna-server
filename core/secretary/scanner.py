"""Scanner de documents — OCR + classification via GPT-4o-mini vision."""

import json
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

SCAN_SYSTEM_PROMPT = """Tu es l'assistant administratif de Luna, une secretaire personnelle IA.

On te donne la photo d'un document (facture, courrier, relance, contrat, fiche de paie, etc.).

Analyse-le et retourne un JSON STRICT avec ces champs :

{
  "type_doc": "facture|relance|courrier|contrat|fiche_de_paie|impot|assurance|abonnement|devis|recu|autre",
  "emetteur": "nom de l'organisme ou entreprise",
  "destinataire": "nom du destinataire si visible",
  "montant": 123.45,
  "devise": "EUR",
  "echeance": "2026-04-15",
  "date_document": "2026-03-10",
  "reference": "numero de facture ou reference",
  "objet": "resume en 1 ligne de quoi il s'agit",
  "urgence": "haute|moyenne|basse",
  "action_requise": "payer avant le 15 avril|aucune|a archiver|a contester",
  "montant_deja_paye": null,
  "mensualites": null,
  "notes": "toute info utile supplementaire"
}

Regles :
- Si un champ n'est pas visible, mets null
- montant = le montant TOTAL a payer (pas le detail ligne par ligne)
- echeance = la date limite de paiement ou de reponse
- urgence = haute si echeance < 7 jours ou relance, moyenne si < 30 jours, basse sinon
- Retourne UNIQUEMENT le JSON, rien d'autre
"""

CATEGORIES_BUDGET = {
    "facture": "charges",
    "relance": "charges",
    "impot": "impots",
    "assurance": "assurance",
    "abonnement": "abonnements",
    "loyer": "logement",
    "fiche_de_paie": "revenus",
    "recu": "achats",
    "devis": "projets",
    "autre": "divers",
}


async def scan_document(openai_client, image_b64: str) -> Tuple[bool, Dict]:
    """
    Analyse une image de document via GPT-4o-mini vision.

    Args:
        openai_client: instance OpenAI
        image_b64: image en base64 (JPEG ou PNG)

    Returns:
        (success, data) avec data = metadonnees extraites
    """
    if not openai_client:
        return False, {"error": "OpenAI non configure"}

    # Detect mime type from base64 header or default to jpeg
    if image_b64.startswith("data:"):
        # Already has data URI prefix
        image_url = image_b64
    else:
        image_url = f"data:image/jpeg;base64,{image_b64}"

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SCAN_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyse ce document :"},
                        {"type": "image_url", "image_url": {"url": image_url, "detail": "high"}},
                    ],
                },
            ],
            max_tokens=800,
            temperature=0.1,
        )

        raw = response.choices[0].message.content.strip()
        # Extract JSON from response (might be wrapped in ```json```)
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        data = json.loads(raw)

        # Validate required fields
        if not data.get("type_doc"):
            data["type_doc"] = "autre"
        if not data.get("objet"):
            data["objet"] = "Document scanne"

        # Map to budget category
        data["budget_categorie"] = CATEGORIES_BUDGET.get(data["type_doc"], "divers")

        logger.info(f"Document scanne: {data.get('type_doc')} / {data.get('emetteur')} / {data.get('montant')}€")
        return True, data

    except json.JSONDecodeError as e:
        logger.error(f"Scan document JSON parse error: {e}, raw: {raw[:200]}")
        return False, {"error": "Impossible de lire le document. Reessaie avec une meilleure photo."}
    except Exception as e:
        logger.error(f"Scan document error: {e}")
        return False, {"error": f"Erreur d'analyse: {type(e).__name__}"}


def generate_budget_suggestions(analysis: Dict) -> list:
    """
    Genere des suggestions d'economies basees sur l'analyse budget.
    Appele cote serveur, pas par LLM (instantane, gratuit).
    """
    suggestions = []
    reste = analysis.get("reste_a_vivre", 0)
    prevu = analysis.get("solde_prevu_fin_mois", 0)
    categories = analysis.get("categories", {})
    depense_moy = analysis.get("depense_moyenne_jour", 0)

    if prevu < 0:
        deficit = abs(prevu)
        suggestions.append({
            "type": "alerte",
            "priority": "haute",
            "message": f"Attention, tu risques un decouvert de {deficit:.0f}€ en fin de mois.",
            "action": f"Il faudrait reduire tes depenses de {deficit / max(1, analysis.get('jours_restants', 1)):.0f}€/jour.",
        })
    elif prevu < 100:
        suggestions.append({
            "type": "vigilance",
            "priority": "moyenne",
            "message": f"Fin de mois serree : il te restera environ {prevu:.0f}€.",
            "action": "Limite les depenses non essentielles cette semaine.",
        })

    # Detect high spending categories
    total_dep = analysis.get("total_depenses", 0)
    if total_dep > 0:
        for cat, amount in sorted(categories.items(), key=lambda x: -x[1]):
            pct = (amount / total_dep) * 100
            if pct > 40 and amount > 200:
                suggestions.append({
                    "type": "categorie",
                    "priority": "moyenne",
                    "message": f"La categorie '{cat}' represente {pct:.0f}% de tes depenses ({amount:.0f}€).",
                    "action": f"Verifie s'il y a des postes a optimiser dans '{cat}'.",
                })

    # Subscription alert
    abo = categories.get("abonnements", 0)
    if abo > 50:
        suggestions.append({
            "type": "abonnements",
            "priority": "basse",
            "message": f"Tu depenses {abo:.0f}€/mois en abonnements.",
            "action": "Fais le tri : quels abonnements utilises-tu vraiment ?",
        })

    # Daily budget tip
    if analysis.get("jours_restants", 0) > 0 and reste > 0:
        budget_jour = reste / analysis["jours_restants"]
        suggestions.append({
            "type": "conseil",
            "priority": "basse",
            "message": f"Budget quotidien disponible : {budget_jour:.0f}€/jour pour les {analysis['jours_restants']} jours restants.",
            "action": "",
        })

    return suggestions
