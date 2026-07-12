"""
Création de rappels depuis la conversation vocale Iris — déterministe côté serveur.

Même constat que pour l'urgence : gpt-realtime-mini n'appelle pas son outil
add_reminder de façon fiable (il part souvent sur « mets-le sur ton téléphone »).
On analyse donc directement le transcript : si l'utilisateur demande un rappel,
le SERVEUR extrait les créneaux (gpt-4o-mini) et crée le rappel lui-même, puis
Iris confirme naturellement. Iris ne renvoie JAMAIS vers une app du téléphone.

Flux : has_reminder_intent() (gate mots-clés, instantané) → extract_reminder() (LLM).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _strip_accents(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


# Mots-clés qui suggèrent une DEMANDE DE CRÉATION de rappel (gate cheap).
# La désambiguïsation fine (création vs simple évocation) est faite par le LLM.
_REMINDER_PATTERNS = [
    r"\brappelle?[ -]?(moi|le moi|moi de|moi d')\b",
    r"\brappelles[ -]?moi\b",
    r"\bun rappel\b", r"\bde rappel\b", r"\bcr[ée]e[r]? un rappel\b",
    r"\bajoute[r]? (un )?rappel\b", r"\bmets? (moi )?un rappel\b",
    r"\bn'?oublie[s]? pas\b", r"\bfais[ -]?moi penser\b", r"\bfaut que je pense\b",
    r"\bpense[r]? [àa]\b", r"\bpr[ée]viens[ -]?moi\b",
    r"\bnote (que|de)\b", r"\bprends note\b",
]
_REMINDER_RE = [re.compile(p) for p in _REMINDER_PATTERNS]


def has_reminder_intent(text: str) -> bool:
    """Gate rapide : le texte ressemble-t-il à une demande de rappel ?"""
    if not text:
        return False
    norm = _strip_accents(text)
    return any(rx.search(norm) for rx in _REMINDER_RE)


_EXTRACT_SYSTEM = (
    "Tu extrais un rappel à créer à partir d'une phrase dite à une assistante vocale. "
    "Tu réponds STRICTEMENT en JSON : "
    '{"is_reminder":true|false,"title":"...","due_date":"YYYY-MM-DD|","due_time":"HH:MM|"}\n'
    "- is_reminder=true UNIQUEMENT si l'utilisateur demande de CRÉER un rappel/une tâche à ne pas oublier. "
    "Si c'est une simple question, une demande de relecture, ou « rappelle-moi ce que tu as dit » "
    "(évocation, pas création), mets is_reminder=false.\n"
    "- title : l'objet du rappel, court, à l'infinitif si possible (ex : « Appeler le médecin »). "
    "Sans la formule « rappelle-moi de ».\n"
    "- due_date : date absolue au format YYYY-MM-DD, résolue à partir de la date du jour fournie "
    "(« demain », « lundi prochain », « le 15 »…). Vide si non précisée.\n"
    "- due_time : heure HH:MM (24h) si précisée (« à 9h », « ce soir »→20:00, « midi »→12:00). "
    "Vide si non précisée.\n"
    "N'invente jamais une date ou une heure non exprimée : laisse vide."
)


async def extract_reminder(
    text: str,
    today_iso: str,
    openai_client: Any,
    model: str = "gpt-4o-mini",
) -> Dict[str, Any]:
    """
    Extrait {is_reminder, title, due_date, due_time} via LLM (client SYNCHRONE → to_thread).
    En cas d'erreur, renvoie is_reminder=false (on ne crée rien à l'aveugle).
    """
    if not text or not openai_client:
        return {"is_reminder": False, "title": "", "due_date": "", "due_time": ""}
    try:
        resp = await asyncio.to_thread(
            openai_client.chat.completions.create,
            model=model,
            messages=[
                {"role": "system", "content": _EXTRACT_SYSTEM},
                {"role": "user", "content": f"Date du jour : {today_iso}\nPhrase : « {text} »"},
            ],
            max_tokens=160,
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content.strip())
        title = str(data.get("title", "")).strip()[:100]
        return {
            "is_reminder": bool(data.get("is_reminder")) and bool(title),
            "title": title,
            "due_date": str(data.get("due_date", "")).strip()[:10],
            "due_time": str(data.get("due_time", "")).strip()[:5],
        }
    except Exception as e:  # pragma: no cover
        logger.warning(f"voice_reminders.extract_reminder error: {e}")
        return {"is_reminder": False, "title": "", "due_date": "", "due_time": ""}
