"""Validation de sécurité côté client pour les prompts et fichiers mission.

Cette couche de protection est indépendante du workflow n8n. Elle refuse
avant envoi tout prompt ou fichier contenant des demandes explicitement
dangereuses ou destructrices.
"""

import re
import unicodedata
from pathlib import Path
from typing import Tuple

# Mots et expressions interdites dans un prompt ou un fichier mission.
# La comparaison est case-insensitive et tolère des séparateurs courants.
FORBIDDEN_PATTERNS = [
    # Git / merge / reset
    "push",
    "merge",
    "reset",
    "reset_hard",
    "reset --hard",
    # Deploy / production
    "deploy",
    "deploie",
    "production_deploy",
    "mise en production",
    # APK / build install
    "installer apk",
    "installer l apk",
    "installer l'apk",
    "install apk",
    "install l apk",
    "install l'apk",
    "install_debug",
    "install debug",
    "build debug apk",
    "build_debug_apk",
    "compile debug apk",
    "assemble debug apk",
    # Communications réelles
    "real_sms",
    "real_call",
    "sms reel",
    "appel reel",
    "appeler",
    "appelle",
    "envoyer sms",
    "envoyer un sms",
    "envoie sms",
    "envoie un sms",
    "sos reel",
    # Secrets / credentials
    ".env",
    "secret",
    "cle api",
    "clé api",
    "api key",
    "api_key",
    "token",
    "password",
    "credential",
    # Données / cloud
    "supprimer donnees",
    "supprimer données",
    "user_data_deletion",
    "cloud_modification",
    "modifier cloud",
    # Actions destructrices explicites
    "stash",
    "supprime",
    "supprimer",
    "suppression",
]

# Marqueurs de négation / interdiction / inhibition. Si un de ces mots
# apparaît à proximité d'un motif interdit, le motif est considéré comme
# utilisé dans un contexte de blocage (et non de demande dangereuse).
NEGATION_MARKERS = {
    "ne",
    "pas",
    "non",
    "sans",
    "aucun",
    "aucune",
    "jamais",
    "interdit",
    "interdite",
    "interdits",
    "interdites",
    "bloque",
    "bloquer",
    "bloqué",
    "bloquée",
    "bloqués",
    "bloquées",
    "refuse",
    "refuser",
    "refusé",
    "refusée",
    "désactive",
    "désactiver",
    "désactivé",
    "désactivée",
    "empeche",
    "empêche",
    "interdiction",
    "prohibition",
}

# Extensions autorisées pour --prompt-file
ALLOWED_PROMPT_EXTENSIONS = {".md", ".txt"}

# Taille maximale d'un fichier prompt (en octets)
MAX_PROMPT_FILE_SIZE = 100 * 1024


def _normalize(text: str) -> str:
    """Normalise le texte pour la détection d'expressions interdites."""
    text = (
        text.lower()
        .replace("_", " ")
        .replace("-", " ")
        .replace("\n", " ")
        .replace("\t", " ")
    )
    # Supprime les accents pour uniformiser "déploie"/"deploie",
    # "réel"/"reel", "clé"/"cle", etc.
    return "".join(
        c
        for c in unicodedata.normalize("NFKD", text)
        if unicodedata.category(c) != "Mn"
    )


def _pattern_allowed(normalized_text: str, pattern: str) -> bool:
    """Dit si toutes les occurrences d'un motif interdit sont autorisées.

    Le texte est découpé en clauses (phrase, segment). Une occurrence est
    autorisée si la clause contient un marqueur de négation/interdiction.
    """
    pattern_norm = _normalize(pattern)
    if pattern_norm not in normalized_text:
        return True

    # Découpe en clauses pour ne pas mélanger les contextes.
    # La ponctuation doit être suivie d'un espace ou de la fin du texte
    # pour éviter de couper des tokens comme ".env".
    clauses = re.split(r"[.!?;\n]+(?:\s+|$)", normalized_text)
    for clause in clauses:
        if pattern_norm not in clause:
            continue
        clause_words = set(re.findall(r"[a-z0-9]+", clause))
        if clause_words & NEGATION_MARKERS:
            # La clause contient une négation/interdiction : on considère
            # l'occurrence comme une formulation de blocage.
            continue
        return False

    return True


def validate_prompt(prompt: str) -> Tuple[bool, str]:
    """Vérifie qu'un prompt texte ne contient pas de demande dangereuse.

    Retourne (True, "") si le prompt est acceptable, (False, reason) sinon.
    Les formulations d'interdiction ("ne pas push", "aucun deploy", etc.)
    sont autorisées.
    """
    if not prompt or not prompt.strip():
        return False, "prompt vide"

    normalized = _normalize(prompt)
    for pattern in FORBIDDEN_PATTERNS:
        if not _pattern_allowed(normalized, pattern):
            return False, f"mot/expression interdit detecte: '{pattern}'"

    return True, ""


def validate_prompt_file(path: Path) -> Tuple[bool, str]:
    """Vérifie qu'un fichier prompt est lisible, sûr et non dangereux.

    Retourne (True, prompt_content) si le fichier est acceptable,
    (False, reason) sinon.
    """
    if not path.exists():
        return False, f"fichier introuvable: {path}"

    if not path.is_file():
        return False, f"chemin non valide: {path}"

    if path.suffix.lower() not in ALLOWED_PROMPT_EXTENSIONS:
        return False, f"extension non autorisee: {path.suffix} (autorise: {', '.join(sorted(ALLOWED_PROMPT_EXTENSIONS))})"

    try:
        size = path.stat().st_size
    except OSError as e:
        return False, f"impossible de lire le fichier: {e}"

    if size > MAX_PROMPT_FILE_SIZE:
        return False, f"fichier trop volumineux: {size} octets (max {MAX_PROMPT_FILE_SIZE})"

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False, "le fichier n'est pas un texte UTF-8 lisible"
    except OSError as e:
        return False, f"erreur lecture fichier: {e}"

    ok, reason = validate_prompt(content)
    if not ok:
        return False, f"contenu du fichier interdit - {reason}"

    return True, content
