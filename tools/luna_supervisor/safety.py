"""Validation de sécurité côté client pour les prompts et fichiers mission.

Cette couche de protection est indépendante du workflow n8n. Elle refuse
avant envoi tout prompt ou fichier contenant des demandes explicitement
dangereuses ou destructrices.
"""

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
    "envoyer sms",
    "envoyer un sms",
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
]

# Extensions autorisées pour --prompt-file
ALLOWED_PROMPT_EXTENSIONS = {".md", ".txt"}

# Taille maximale d'un fichier prompt (en octets)
MAX_PROMPT_FILE_SIZE = 100 * 1024


def _normalize(text: str) -> str:
    """Normalise le texte pour la détection d'expressions interdites."""
    return (
        text.lower()
        .replace("_", " ")
        .replace("-", " ")
        .replace("\n", " ")
        .replace("\t", " ")
    )


def validate_prompt(prompt: str) -> Tuple[bool, str]:
    """Vérifie qu'un prompt texte ne contient pas de demande dangereuse.

    Retourne (True, "") si le prompt est acceptable, (False, reason) sinon.
    """
    if not prompt or not prompt.strip():
        return False, "prompt vide"

    normalized = _normalize(prompt)
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.lower() in normalized:
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
