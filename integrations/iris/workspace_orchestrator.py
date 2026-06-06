"""Iris Workspace Orchestrator.

Server-owned first pass for the Command Screen. The language model may add
personality, but the server decides when a user request is work, which mode it
belongs to, and which visual render must appear immediately.
"""
from __future__ import annotations

import re
import time
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from integrations.iris.modes import DEFAULT_MODE, detect_mode_from_text


@dataclass
class WorkspacePlan:
    should_render: bool
    mode: str
    render_type: str
    payload: Dict[str, Any]
    speech_instruction: str
    source: str = "workspace_orchestrator"


@dataclass
class MissionBrief:
    """Human/admin-defined frame for an Iris workspace session."""

    title: str = ""
    domain: str = ""
    objective: str = ""
    context: str = ""
    inputs: List[Dict[str, Any]] | None = None
    deliverables: List[str] | None = None
    constraints: List[str] | None = None
    external_research: bool = False

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "MissionBrief":
        if not isinstance(data, dict):
            return cls()
        return cls(
            title=str(data.get("title") or "")[:160],
            domain=str(data.get("domain") or data.get("topic") or "")[:120],
            objective=str(data.get("objective") or "")[:500],
            context=str(data.get("context") or "")[:1500],
            inputs=_list_of_dicts(data.get("inputs")),
            deliverables=_list_of_strings(data.get("deliverables")),
            constraints=_list_of_strings(data.get("constraints")),
            external_research=bool(data.get("external_research") or data.get("allow_web")),
        )

    def active(self) -> bool:
        return bool(self.title or self.domain or self.objective or self.context or self.inputs or self.deliverables)

    def context_text(self) -> str:
        parts = []
        if self.title:
            parts.append(f"Mission: {self.title}")
        if self.domain:
            parts.append(f"Domaine: {self.domain}")
        if self.objective:
            parts.append(f"Objectif: {self.objective}")
        if self.context:
            parts.append(f"Contexte: {self.context}")
        if self.deliverables:
            parts.append("Livrables attendus: " + ", ".join(self.deliverables))
        if self.constraints:
            parts.append("Contraintes: " + ", ".join(self.constraints))
        if self.inputs:
            labels = [str(i.get("label") or i.get("type") or "source") for i in self.inputs[:6]]
            parts.append("Sources fournies: " + ", ".join(labels))
        parts.append("Recherche externe: " + ("autorisee" if self.external_research else "non autorisee sans validation"))
        return "\n".join(parts)


def _list_of_strings(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(v)[:180] for v in value if str(v or "").strip()][:12]


def _list_of_dicts(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    result: List[Dict[str, Any]] = []
    for item in value[:12]:
        if isinstance(item, dict):
            result.append({
                "type": str(item.get("type") or "source")[:60],
                "label": str(item.get("label") or item.get("name") or item.get("url") or "source")[:180],
                "status": str(item.get("status") or "fourni")[:60],
            })
        else:
            result.append({"type": "source", "label": str(item)[:180], "status": "fourni"})
    return result


def _norm(text: str) -> str:
    raw = (text or "").lower()
    nfd = unicodedata.normalize("NFD", raw)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def _numbers(text: str) -> List[float]:
    vals: List[float] = []
    for match in re.findall(r"-?\d+(?:[,.]\d+)?", text or ""):
        try:
            vals.append(float(match.replace(",", ".")))
        except ValueError:
            pass
    return vals[:12]


def _chart_labels(text: str, count: int) -> List[str]:
    lowered = _norm(text)
    month_pairs = [
        ("janvier", "Jan"), ("fevrier", "Fev"), ("mars", "Mar"),
        ("avril", "Avr"), ("mai", "Mai"), ("juin", "Juin"),
        ("juillet", "Juil"), ("aout", "Aout"), ("septembre", "Sep"),
        ("octobre", "Oct"), ("novembre", "Nov"), ("decembre", "Dec"),
    ]
    labels = [label for word, label in month_pairs if word in lowered]
    if len(labels) >= count:
        return labels[:count]
    return [f"Point {i + 1}" for i in range(count)]


def _has_any(text: str, words: List[str]) -> bool:
    n = _norm(text)
    return any(w in n for w in words)


def _latest_document(session_documents: Optional[List[Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
    docs = session_documents or []
    if not docs:
        return None
    return max(docs, key=lambda d: d.get("ts", 0))


def _missing(title: str, fields: List[str], context: str) -> Dict[str, Any]:
    return {
        "title": title,
        "fields": fields,
        "context": context[:280],
        "suggestions": [
            "Donne-moi les donnees exactes a utiliser.",
            "Precise le format attendu du rendu.",
            "Ajoute un document ou des chiffres si necessaire.",
        ],
        "summary": "Iris attend les informations necessaires avant de produire un rendu final.",
    }


def _is_work_request(text: str) -> bool:
    return _has_any(text, [
        "tableau", "graphique", "courbe", "histogramme", "camembert",
        "document", "courrier", "lettre", "email", "redige", "ecris",
        "analyse", "resume", "synthese", "business plan", "budget",
        "kpi", "indicateur", "reunion", "compte-rendu", "kanban",
        "planning", "timeline", "roadmap", "compare", "cherche",
        "trouve", "web", "internet", "sms", "appelle", "envoie",
        "workspace", "panneau", "affiche", "montre",
    ])


def orchestrate_workspace_request(
    text: str,
    *,
    active_mode: str = DEFAULT_MODE,
    session_documents: Optional[List[Dict[str, Any]]] = None,
    mission_brief: Optional[Dict[str, Any] | MissionBrief] = None,
) -> WorkspacePlan:
    """Build a first deterministic Command Screen render for a user request."""
    ask = (text or "").strip()
    normalized = _norm(ask)
    brief = mission_brief if isinstance(mission_brief, MissionBrief) else MissionBrief.from_dict(mission_brief)
    if not ask or not _is_work_request(ask):
        return WorkspacePlan(
            should_render=False,
            mode=active_mode or DEFAULT_MODE,
            render_type="context_panel",
            payload={},
            speech_instruction="Reponds naturellement en une phrase courte.",
        )

    detected_mode = detect_mode_from_text(ask)
    mode = detected_mode if detected_mode != DEFAULT_MODE else (active_mode or DEFAULT_MODE)
    doc = _latest_document(session_documents)
    nums = _numbers(ask)
    mission_context = brief.context_text() if brief.active() else ""

    if _has_any(ask, ["contexte", "mission", "brief", "workspace", "sujet", "objectif"]) and brief.active():
        return WorkspacePlan(
            True,
            mode,
            "context_panel",
            {
                "title": brief.title or "Mission Iris",
                "sections": [
                    {"heading": "Domaine", "body": brief.domain or "A definir"},
                    {"heading": "Objectif", "body": brief.objective or ask},
                    {"heading": "Contexte", "body": brief.context or "A completer"},
                    {"heading": "Livrables", "body": ", ".join(brief.deliverables or ["A definir"])},
                ],
                "context": mission_context,
                "summary": "Brief de mission actif. Iris doit rester dans ce cadre.",
            },
            "Confirme en une phrase que le brief de mission est actif.",
        )

    if _has_any(ask, ["sms", "appelle", "appel", "email", "mail", "envoie", "envoyer"]):
        return WorkspacePlan(
            True,
            "actions",
            "action_board",
            {
                "title": "Validation requise",
                "requires_confirmation": True,
                "sections": [
                    {
                        "title": "Action demandee",
                        "items": [{"text": ask, "done": False, "priority": "high"}],
                    },
                    {
                        "title": "Garde-fous",
                        "items": [
                            {"text": "Aucune action externe n'est executee sans validation.", "done": True},
                            {"text": "Verifier destinataire, horaire, cout et consentement.", "done": False},
                        ],
                    },
                ],
                "context": mission_context or "Action sensible detectee par le serveur.",
            },
            "Le panneau de validation est affiche. Dis que l'action attend confirmation.",
        )

    if _has_any(ask, ["graphique", "courbe", "histogramme", "camembert", "evolution", "tendance"]):
        if nums:
            labels = _chart_labels(ask, len(nums))
            return WorkspacePlan(
                True,
                "tableau",
                "chart",
                {
                    "title": "Graphique de travail",
                    "type": "bar",
                    "labels": labels,
                    "datasets": [{"label": "Valeur", "data": nums}],
                    "summary": "Graphique construit a partir des donnees fournies.",
                    "context": mission_context or ask[:220],
                },
                "Confirme en une phrase que le graphique est affiche.",
            )
        return WorkspacePlan(
            True,
            "tableau",
            "missing_info",
            _missing(
                "Graphique a construire",
                ["Les donnees chiffrees", "Les libelles ou periodes", "Le type de graphique souhaite"],
                mission_context or ask,
            ),
            "Explique en une phrase quelles donnees manquent pour afficher le graphique.",
        )

    if _has_any(ask, ["tableau", "donnees", "liste", "grille"]):
        rows = [[f"Valeur {i + 1}", str(v), "recu"] for i, v in enumerate(nums)]
        if not rows:
            rows = [["Demande", ask[:80], "a structurer"]]
        return WorkspacePlan(
            True,
            "tableau",
            "data_board",
            {
                "title": "Tableau de travail",
                "columns": ["Element", "Valeur", "Statut"],
                "rows": rows,
                "summary": "Tableau cree par le serveur a partir de la demande.",
                "context": mission_context or ask[:220],
            },
            "Confirme en une phrase que le tableau est affiche.",
        )

    if _has_any(ask, ["courrier", "lettre", "redige", "rediger", "ecris", "ecrire", "email", "mail"]):
        return WorkspacePlan(
            True,
            "redaction",
            "document_draft",
            {
                "title": "Brouillon professionnel",
                "subject": "A preciser",
                "body": (
                    "Bonjour,\n\n"
                    f"Voici un premier brouillon base sur la demande : {ask}\n\n"
                    "[Iris complete ici les informations manquantes, le destinataire et les pieces utiles.]\n\n"
                    "Cordialement,\n"
                    "[Signature]"
                ),
                "placeholders": ["Destinataire", "Objet exact", "Informations cles", "Signature"],
                "summary": "Brouillon editable pret a completer.",
                "context": mission_context or ask[:220],
            },
            "Confirme en une phrase que le brouillon est ouvert dans le panneau.",
        )

    if doc and _has_any(ask, ["analyse", "resume", "synthese", "points cles", "document", "pdf"]):
        return WorkspacePlan(
            True,
            "analyse",
            "document_insight",
            {
                "title": doc.get("filename", "Document"),
                "boxes": [
                    {"title": "Analyse disponible", "body": doc.get("analysis", "Document charge.")},
                    {"title": "Demande", "body": ask[:300]},
                ],
                "tags": [{"label": "Document actif", "type": "ok"}],
                "actions": [
                    {"label": "Synthese"},
                    {"label": "Tableau"},
                    {"label": "Graphique"},
                    {"label": "Brouillon"},
                ],
                "context": mission_context or "Document charge dans la session.",
            },
            "Confirme en une phrase que l'analyse du document est affichee.",
        )

    if _has_any(ask, ["cherche", "trouve", "web", "internet", "source"]):
        if brief.active() and not brief.external_research:
            return WorkspacePlan(
                True,
                "recherche",
                "missing_info",
                _missing(
                    "Recherche externe a valider",
                    ["Autorisation recherche web", "Perimetre des sources", "Niveau de fiabilite attendu"],
                    mission_context or ask,
                ),
                "Explique en une phrase que la recherche externe doit etre autorisee dans le brief.",
            )
        return WorkspacePlan(
            True,
            "recherche",
            "research_board",
            {
                "query": ask,
                "summary": "Recherche externe demandee. Le connecteur web doit retourner les sources avant le rendu final.",
                "sources": [],
                "context": mission_context or "Le serveur a detecte une demande de recherche externe.",
                "missing": ["Brancher ou verifier le tool search_web pour recuperer les sources en temps reel."],
            },
            "Dis en une phrase que la recherche est cadrée et que les sources doivent etre recuperees.",
        )

    if _has_any(ask, ["reunion", "compte-rendu", "ordre du jour", "participant"]):
        return WorkspacePlan(
            True,
            "reunion",
            "meeting_board",
            {
                "title": "Reunion de travail",
                "date": time.strftime("%d/%m/%Y"),
                "time": time.strftime("%H:%M"),
                "participants": [{"name": "Ludovic", "initials": "LU", "role": "Owner"}],
                "agenda": [{"item": ask[:120], "done": False}],
                "decisions": [],
            "summary": "Espace de reunion initialise.",
                "context": mission_context,
            },
            "Confirme en une phrase que le panneau reunion est ouvert.",
        )

    return WorkspacePlan(
        True,
        mode,
        "context_panel",
        {
            "title": "Espace de travail Iris",
            "sections": [
                {"heading": "Demande", "body": ask},
                {"heading": "Action serveur", "body": "Iris ouvre un panneau de travail au lieu de rester en conversation seule."},
            ],
            "summary": "Demande de travail detectee.",
            "context": mission_context or ask[:220],
        },
        "Confirme en une phrase que le panneau de travail est ouvert.",
    )
