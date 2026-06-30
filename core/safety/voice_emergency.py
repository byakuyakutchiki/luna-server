"""
Détection d'urgence pendant une conversation vocale avec Iris.

Architecture délibérément DÉTERMINISTE côté serveur : on n'attend PAS que le
modèle vocal (gpt-realtime-mini) appelle un outil — il en est incapable de
façon fiable. On analyse directement la transcription de l'utilisateur.

Deux niveaux (cf. politique validée par Ludo) :
  - immediate : danger explicite/clair → alerte IMMÉDIATE, aucune confirmation.
  - ambiguous : détresse possible mais incertaine → Iris demande UNE fois.

Détection hybride :
  - match_immediate_sos() : regex sur formulations explicites (instantané, 0 coût).
  - classify_emergency() : compréhension d'intention via gpt-4o-mini (nuancé).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import unicodedata
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


def _strip_accents(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


# ---------------------------------------------------------------------------
# Niveau 1 — SOS EXPLICITE (instantané, déterministe)
# ---------------------------------------------------------------------------
# Formulations qui, à elles seules, justifient un déclenchement immédiat.
# Comparées sur une version SANS accents et en minuscules.
# NOTE (30/06) : "aide-moi", "aidez-moi" et "a l'aide" ont été RETIRÉS de cette liste —
# ce sont des formulations banales adressées à un assistant ("aide-moi à écrire un mail",
# "à l'aide de…") qui provoquaient des alertes intempestives (SMS+appels aux proches sans
# confirmation). La détresse réelle exprimée ainsi reste captée par le classifieur LLM, qui
# passe désormais TOUJOURS par une confirmation vocale avant d'alerter.
_IMMEDIATE_PATTERNS = [
    r"\bau secours\b",
    r"\bje suis en danger\b",
    r"\bje suis en train de mourir\b",
    r"\bje vais mourir\b",
    r"\bje me sens mourir\b",
    r"\bappelle (mes |les )?(contacts|proches|secours|ma famille|mes enfants)\b",
    r"\bpreviens (mes |les )?(contacts|proches|ma famille)\b",
    r"\balerte (mes |les )?(contacts|proches)\b",
    r"\bj'?ai besoin d'?aide (maintenant|tout de suite|vite|urgent)\b",
    r"\bc'?est une urgence\b",
    r"\burgence (medicale|vitale)\b",
    r"\bje peux plus (respirer|bouger|me lever)\b",
    r"\bje n'?arrive plus a respirer\b",
    r"\bj'?etouffe\b",
    r"\bje suis tombe[e]?\b.*\b(peux plus|peux pas|arrive plus|mal)\b",
    r"\bil m'?agresse\b",
    r"\bon m'?agresse\b",
    r"\bil veut me (tuer|frapper|faire du mal)\b",
    r"\bhelp me\b",
    r"\bcall (my |the )?(contacts|family|help)\b",
]
_IMMEDIATE_RE = [re.compile(p) for p in _IMMEDIATE_PATTERNS]


def match_immediate_sos(text: str) -> bool:
    """True si le texte contient une formulation de détresse EXPLICITE → alerte immédiate."""
    if not text:
        return False
    norm = _strip_accents(text)
    return any(rx.search(norm) for rx in _IMMEDIATE_RE)


# ---------------------------------------------------------------------------
# Confirmation (pour le niveau ambigu : « tu veux que je prévienne tes proches ? »)
# ---------------------------------------------------------------------------
_AFFIRMATIVE = [
    r"\boui\b", r"\bouais\b", r"\bok\b", r"\bd'?accord\b", r"\bvas[ -]?y\b",
    r"\bfais[ -]?le\b", r"\bappelle[ -]?les\b", r"\bpreviens[ -]?les\b",
    r"\bs'?il te plait\b", r"\bje t'?en prie\b", r"\bbien sur\b", r"\byes\b",
    r"\bmaintenant\b", r"\btout de suite\b", r"\bvite\b",
]
_AFFIRMATIVE_RE = [re.compile(p) for p in _AFFIRMATIVE]

_NEGATIVE = [
    r"\bnon\b", r"\bnan\b", r"\bpas (la peine|besoin|maintenant)\b",
    r"\blaisse tomber\b", r"\bc'?est bon\b", r"\bca va\b", r"\bca ira\b",
    r"\bn'?appelle pas\b", r"\bsurtout pas\b", r"\bno\b",
]
_NEGATIVE_RE = [re.compile(p) for p in _NEGATIVE]


def is_affirmative(text: str) -> bool:
    """True si l'utilisateur confirme (répond oui à la proposition d'alerter)."""
    if not text:
        return False
    norm = _strip_accents(text)
    if any(rx.search(norm) for rx in _NEGATIVE_RE):
        return False
    return any(rx.search(norm) for rx in _AFFIRMATIVE_RE)


def is_negative(text: str) -> bool:
    """True si l'utilisateur refuse explicitement l'alerte."""
    if not text:
        return False
    norm = _strip_accents(text)
    return any(rx.search(norm) for rx in _NEGATIVE_RE)


# ---------------------------------------------------------------------------
# Niveau 2 — INTENTION (gpt-4o-mini) : capte la détresse que les mots-clés ratent
# ---------------------------------------------------------------------------
_CLASSIFY_SYSTEM = (
    "Tu es un module de sécurité qui analyse les propos d'un utilisateur pendant "
    "une conversation vocale avec son assistante. Tu détermines s'il y a une "
    "URGENCE ou une demande d'aide immédiate (danger physique, malaise, agression, "
    "chute, détresse vitale, idées suicidaires, peur d'une menace présente).\n"
    "Tu réponds STRICTEMENT en JSON : "
    '{\"level\":\"immediate|ambiguous|none\",\"summary\":\"...\",\"reason\":\"...\"}\n'
    "- immediate : danger réel ou demande d'aide claire → il faut alerter les proches MAINTENANT "
    "(chute avec blessure, malaise, douleur thoracique, difficulté à respirer, agression/intrusion, "
    "menace immédiate, idées suicidaires explicites).\n"
    "- ambiguous : VRAIS signaux de détresse ou de danger possible, mais incertains → il faut DEMANDER "
    "avant d'alerter (symptôme physique potentiellement sérieux, peur d'une menace présente, désespoir profond, "
    "isolement avec détresse marquée).\n"
    "- none : conversation normale, y compris émotions négatives ORDINAIRES de la vie courante "
    "(fatigue, stress du travail, agacement, déception, ennui, légère tristesse, inquiétude banale, "
    "peur d'un examen, film qui fait peur). Ces cas ne justifient PAS d'alerter ni de demander à alerter.\n"
    "summary : résumé court (1 phrase) de la situation comprise, en français, utile pour prévenir un proche. "
    "Ne classe 'immediate' ou 'ambiguous' QUE s'il y a un vrai enjeu de sécurité ou de santé. "
    "Une simple émotion négative du quotidien = none. En cas de doute entre une VRAIE détresse et none, "
    "choisis ambiguous ; mais n'utilise jamais ambiguous pour un simple coup de fatigue ou de ras-le-bol."
)


async def classify_emergency(
    text: str,
    recent_user_texts: Optional[List[str]],
    openai_client: Any,
    model: str = "gpt-4o-mini",
) -> Dict[str, Any]:
    """
    Classifie l'intention d'urgence via LLM. Retourne
    {"level": "immediate"|"ambiguous"|"none", "summary": str, "reason": str}.

    En cas d'erreur LLM, retombe sur {"level":"none"} (le filet keyword reste actif
    en amont pour les SOS explicites — on ne perd jamais le cas le plus grave).
    """
    if not text or not openai_client:
        return {"level": "none", "summary": "", "reason": "no_input"}

    context = ""
    if recent_user_texts:
        joined = " | ".join(t for t in recent_user_texts[-4:] if t)
        if joined:
            context = f"Échanges récents de l'utilisateur : {joined}\n"
    user_msg = f"{context}Dernière phrase de l'utilisateur : « {text} »"

    try:
        # openai_client est SYNCHRONE dans cette app → on l'exécute hors boucle event.
        resp = await asyncio.to_thread(
            openai_client.chat.completions.create,
            model=model,
            messages=[
                {"role": "system", "content": _CLASSIFY_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=160,
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content.strip()
        data = json.loads(raw)
        level = str(data.get("level", "none")).lower()
        if level not in ("immediate", "ambiguous", "none"):
            level = "none"
        return {
            "level": level,
            "summary": str(data.get("summary", ""))[:300],
            "reason": str(data.get("reason", ""))[:300],
        }
    except Exception as e:  # pragma: no cover - dépend du réseau
        logger.warning(f"voice_emergency.classify_emergency error: {e}")
        return {"level": "none", "summary": "", "reason": f"llm_error:{e}"}
