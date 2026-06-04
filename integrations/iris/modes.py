"""Iris Modes de Mission — Objectif 024

Cadrage des 10 modes de travail d'Iris.
Chaque mode définit : contexte, outils autorisés, render type attendu, garde-fous.
"""
from typing import Dict, Any, List


MODE_DISCUSSION = {
    "id": "discussion",
    "label": "Discussion",
    "icon": "💬",
    "prompt_appendix": (
        "Mode discussion courte. Réponses en 2-3 phrases maximum. "
        "Pas de rendu visuel sauf demande explicite. "
        "Si la demande devient complexe (tableau, graphique, document, analyse), "
        "propose de passer en mode adapté."
    ),
    "allowed_tools": ["chat"],
    "default_render": "context_panel",
    "forbidden_actions": ["send_sms", "call_contact", "send_email", "alert_contacts",
                          "invite_visio", "invite_to_session", "add_expense"],
    "auto_render": False,
}

MODE_ANALYSE = {
    "id": "analyse",
    "label": "Analyse documents",
    "icon": "📄",
    "prompt_appendix": (
        "Mode Analyse de documents. Tu examines des documents uploadés et produis "
        "des synthèses structurées : résumé, points clés, risques, opportunités, actions. "
        "Structure TOUJOURS ta réponse en sections. Utilise document_insight. "
        "Les formats acceptés : PDF, DOCX, TXT, CSV, XLSX, images, ZIP. "
        "Pour un ZIP : liste les fichiers, puis analyse chaque document pertinent."
    ),
    "allowed_tools": ["get_documents_summary", "search_documents", "list_folders",
                      "iris_render", "chat"],
    "default_render": "document_insight",
    "forbidden_actions": ["send_sms", "call_contact", "send_email"],
    "auto_render": True,
}

MODE_REUNION = {
    "id": "reunion",
    "label": "Réunion",
    "icon": "👥",
    "prompt_appendix": (
        "Mode Réunion. Tu écoutes tous les participants, prends des notes structurées, "
        "assigne les actions avec responsables, et produis un compte-rendu. "
        "Utilise meeting_board pour le CR. Utilize organize_kanban pour les actions. "
        "À la fin de la réunion, résume les décisions et les actions à venir."
    ),
    "allowed_tools": ["start_meeting", "organize_kanban", "iris_render", "chat",
                      "get_contacts", "add_reminder"],
    "default_render": "meeting_board",
    "forbidden_actions": ["send_sms", "call_contact", "send_email", "alert_contacts",
                          "invite_visio"],
    "auto_render": True,
}

MODE_TABLEAU = {
    "id": "tableau",
    "label": "Tableau / Graphique",
    "icon": "📊",
    "prompt_appendix": (
        "Mode Tableau / Graphique. Tu structures TOUTES les données visuellement. "
        "Utilise data_board pour des tableaux, chart pour des graphiques/courbes/barres, "
        "kpi_cards pour des indicateurs clés, timeline pour des chronologies. "
        "Ne réponds JAMAIS en texte seul quand des données sont présentes. "
        "Si les données sont insuffisantes pour un graphique, affiche un tableau."
    ),
    "allowed_tools": ["iris_render", "chat"],
    "default_render": "data_board",
    "forbidden_actions": ["send_sms", "call_contact", "send_email"],
    "auto_render": True,
}

MODE_REDACTION = {
    "id": "redaction",
    "label": "Rédaction",
    "icon": "✏️",
    "prompt_appendix": (
        "Mode Rédaction. Tu produis des documents complets et professionnels : "
        "courriers, emails, contrats, notes, rapports. "
        "Utilise document_draft. Inclue les placeholders pour les informations manquantes. "
        "Le document est exportable en PDF/TXT. Pas d'envoi sans confirmation."
    ),
    "allowed_tools": ["iris_render", "generate_document", "chat"],
    "default_render": "document_draft",
    "forbidden_actions": ["send_sms", "call_contact", "send_email", "alert_contacts"],
    "auto_render": True,
}

MODE_RECHERCHE = {
    "id": "recherche",
    "label": "Recherche web",
    "icon": "🔍",
    "prompt_appendix": (
        "Mode Recherche web. Tu cherches des informations factuelles et les présentes "
        "de manière structurée avec sources. Cite TOUJOURS tes sources. "
        "Utilise context_panel pour la synthèse. "
        "Pas d'information médicale/juridique sans disclaimer."
    ),
    "allowed_tools": ["search_web", "get_page_info", "get_news", "iris_render", "chat"],
    "default_render": "context_panel",
    "forbidden_actions": ["send_sms", "call_contact", "send_email"],
    "auto_render": True,
}

MODE_ACTIONS = {
    "id": "actions",
    "label": "Actions",
    "icon": "⚡",
    "prompt_appendix": (
        "Mode Actions. Tu exécutes des actions concrètes : SMS, email, appel, rappel. "
        "TOUJOURS demander confirmation avant envoi/réalisation. "
        "Utilise action_board pour présenter les actions à valider. "
        "Blacklist horaires 22h-7h. Pas d'appel aux numéros d'urgence."
    ),
    "allowed_tools": ["send_sms", "send_email", "call_contact", "add_reminder",
                      "alert_contacts", "iris_render", "chat"],
    "default_render": "action_board",
    "forbidden_actions": ["invite_visio", "invite_to_session"],
    "auto_render": True,
    "requires_confirmation": True,
}

MODE_EQUIPE = {
    "id": "equipe",
    "label": "Équipe",
    "icon": "🧑‍🤝‍🧑",
    "prompt_appendix": (
        "Mode Équipe. Tu gères les participants de la session : lister, inviter, rôles. "
        "Seul le souscripteur (owner) peut inviter ou exclure. "
        "Utilise status_rail pour l'état de l'équipe. "
        "Utilize invite_to_session pour les invitations."
    ),
    "allowed_tools": ["invite_to_session", "get_contacts", "iris_render", "chat"],
    "default_render": "status_rail",
    "forbidden_actions": ["send_sms", "call_contact", "send_email", "alert_contacts"],
    "auto_render": True,
    "subscriber_only": ["invite_to_session"],
}

MODE_CARTE = {
    "id": "carte",
    "label": "Carte",
    "icon": "🗺️",
    "prompt_appendix": (
        "Mode Carte. Tu localises des adresses et affiches des informations géographiques. "
        "Demande TOUJOURS le consentement pour la géolocalisation. "
        "Utilise search_places pour chercher un lieu. Utilise map_board pour l'affichage."
    ),
    "allowed_tools": ["search_places", "iris_render", "chat"],
    "default_render": "map_board",
    "forbidden_actions": ["send_sms", "call_contact", "send_email", "alert_contacts"],
    "auto_render": True,
    "requires_consent": ["geolocation"],
}

MODE_CONFORMITE = {
    "id": "conformite",
    "label": "Conformité",
    "icon": "🛡️",
    "prompt_appendix": (
        "Mode Conformité. Tu vérifies les documents, contrats et obligations. "
        "Tu ne donnes PAS de conseil juridique. "
        "Ajoute TOUJOURS : 'Je ne suis pas un conseil juridique. Vérifiez avec un professionnel.' "
        "Utilise document_insight pour l'analyse. Utilise action_board pour les points à vérifier."
    ),
    "allowed_tools": ["get_documents_summary", "search_documents", "iris_render", "chat"],
    "default_render": "document_insight",
    "forbidden_actions": ["send_sms", "call_contact", "send_email", "alert_contacts"],
    "auto_render": True,
    "mandatory_disclaimer": "Je ne suis pas un conseil juridique.",
}

IRIS_MODES: Dict[str, Dict[str, Any]] = {
    "discussion": MODE_DISCUSSION,
    "analyse": MODE_ANALYSE,
    "reunion": MODE_REUNION,
    "tableau": MODE_TABLEAU,
    "redaction": MODE_REDACTION,
    "recherche": MODE_RECHERCHE,
    "actions": MODE_ACTIONS,
    "equipe": MODE_EQUIPE,
    "carte": MODE_CARTE,
    "conformite": MODE_CONFORMITE,
}

DEFAULT_MODE = "discussion"

# Mots déclencheurs pour auto-détection du mode depuis la demande utilisateur
MODE_TRIGGER_WORDS: Dict[str, List[str]] = {
    "analyse": ["analyse", "document", "pdf", "fichier", "synthèse", "rapport", "lire", "zip"],
    "reunion": ["réunion", "compte-rendu", "cr", "note", "décision", "participant"],
    "tableau": ["tableau", "graphique", "courbe", "histogramme", "chiffres", "données", "kpi"],
    "redaction": ["rédige", "écris", "courrier", "lettre", "email", "contrat", "document"],
    "recherche": ["cherche", "trouve", "web", "internet", "source", "information"],
    "actions": ["envoie", "appelle", "sms", "email", "rappelle", "action"],
    "equipe": ["équipe", "membre", "inviter", "participant", "rôle"],
    "carte": ["carte", "localise", "adresse", "itinéraire", "où est", "géolocalisation"],
    "conformite": ["conformité", "rgpd", "juridique", "légal", "contrat", "vérifier"],
}


def detect_mode_from_text(text: str) -> str:
    """Détecte le mode le plus probable depuis le texte utilisateur."""
    lower = text.lower()
    scores: Dict[str, int] = {}
    for mode_id, words in MODE_TRIGGER_WORDS.items():
        score = sum(1 for w in words if w in lower)
        if score:
            scores[mode_id] = score
    if not scores:
        return DEFAULT_MODE
    return max(scores, key=scores.get)


def get_mode_tools(mode_id: str) -> List[str]:
    """Retourne la liste des outils autorisés pour un mode."""
    mode = IRIS_MODES.get(mode_id)
    if not mode:
        return []
    return mode.get("allowed_tools", [])


def build_mode_context(mode_id: str) -> str:
    """Construit le contexte système à injecter pour un mode donné."""
    mode = IRIS_MODES.get(mode_id)
    if not mode:
        return ""
    lines = [
        f"=== MODE COURANT : {mode['label'].upper()} ===",
        mode["prompt_appendix"],
        f"Outils autorisés : {', '.join(mode.get('allowed_tools', []))}",
        f"Render type attendu : {mode.get('default_render', 'context_panel')}",
    ]
    if mode.get("requires_confirmation"):
        lines.append("CONFIRMATION OBLIGATOIRE pour toute action externe.")
    if mode.get("mandatory_disclaimer"):
        lines.append(f"Disclaimer obligatoire : {mode['mandatory_disclaimer']}")
    return "\n".join(lines)
