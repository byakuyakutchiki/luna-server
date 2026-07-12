"""Liste blanche des actions et commandes autorisées.

Le runner n'exécute jamais de commande shell arbitraire. Chaque action est
prédéfinie, validée et construite de manière contrôlée.
"""

import re
import shlex
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class AllowedCommand:
    """Définit une commande autorisée.

    - family: nom interne de l'action (ex: adb_devices)
    - base: liste des tokens de base, sans arguments variables
    - allowed_args: arguments positionnels ou options autorisés
    - arg_patterns: regex autorisés pour les arguments variables
    - modifies_state: True si la commande modifie l'état du téléphone ou du dépôt
    - requires_lock: True si un verrou opérateur est requis
    """

    family: str
    base: Tuple[str, ...]
    allowed_args: Tuple[str, ...] = ()
    arg_patterns: Tuple[str, ...] = ()
    modifies_state: bool = False
    requires_lock: bool = False


# Commandes Git autorisées (lecture seule ou commit local)
GIT_STATUS = AllowedCommand("git_status", ("git", "status"), modifies_state=False)
GIT_DIFF = AllowedCommand("git_diff", ("git", "diff"), modifies_state=False)
GIT_LOG = AllowedCommand("git_log", ("git", "log"), modifies_state=False)
GIT_BRANCH = AllowedCommand("git_branch", ("git", "branch"), modifies_state=False)
GIT_SWITCH = AllowedCommand(
    "git_switch",
    ("git", "switch"),
    allowed_args=("-c",),
    arg_patterns=(r"^automation/[a-zA-Z0-9_-]+$",),
    modifies_state=True,
)
GIT_ADD = AllowedCommand(
    "git_add",
    ("git", "add"),
    arg_patterns=(r"^[a-zA-Z0-9_./\-]+$",),
    modifies_state=True,
)
GIT_COMMIT = AllowedCommand(
    "git_commit",
    ("git", "commit"),
    allowed_args=("-m",),
    modifies_state=True,
)

# Commandes Gradle/Android autorisées
GRADLE_TEST = AllowedCommand(
    "gradle_test", ("./gradlew", "test"), modifies_state=False
)
GRADLE_CONNECTED_TEST = AllowedCommand(
    "gradle_connected_test",
    ("./gradlew", "connectedAndroidTest"),
    modifies_state=True,
    requires_lock=True,
)
GRADLE_ASSEMBLE_DEBUG = AllowedCommand(
    "gradle_assemble_debug",
    ("./gradlew", "assembleDebug"),
    modifies_state=False,
)

# Commandes ADB autorisées
ADB_DEVICES = AllowedCommand("adb_devices", ("adb", "devices"), modifies_state=False)
ADB_GET_STATE = AllowedCommand(
    "adb_get_state", ("adb", "get-state"), modifies_state=False
)
ADB_LOGCAT = AllowedCommand("adb_logcat", ("adb", "logcat"), modifies_state=False)
ADB_DUMPSYS = AllowedCommand(
    "adb_shell_dumpsys", ("adb", "shell", "dumpsys"), modifies_state=False
)
ADB_UI_DUMP = AllowedCommand(
    "adb_shell_uiautomator_dump",
    ("adb", "shell", "uiautomator", "dump"),
    modifies_state=False,
)
ADB_SCREENCAP = AllowedCommand(
    "adb_exec_out_screencap",
    ("adb", "exec-out", "screencap"),
    modifies_state=False,
)
ADB_INSTALL = AllowedCommand(
    "adb_install",
    ("adb", "install", "-r"),
    arg_patterns=(r"^.*luna.*\.apk$",),
    modifies_state=True,
    requires_lock=True,
)
ADB_START_APP = AllowedCommand(
    "adb_start_app",
    ("adb", "shell", "am", "start"),
    allowed_args=("-n",),
    arg_patterns=(r"^fr\.yawatch\.luna/\.MainActivity$",),
    modifies_state=True,
    requires_lock=True,
)
ADB_FORCE_STOP = AllowedCommand(
    "adb_force_stop",
    ("adb", "shell", "am", "force-stop"),
    arg_patterns=(r"^fr\.yawatch\.luna$",),
    modifies_state=True,
    requires_lock=True,
)

ALLOWED_COMMANDS: List[AllowedCommand] = [
    GIT_STATUS,
    GIT_DIFF,
    GIT_LOG,
    GIT_BRANCH,
    GIT_SWITCH,
    GIT_ADD,
    GIT_COMMIT,
    GRADLE_TEST,
    GRADLE_CONNECTED_TEST,
    GRADLE_ASSEMBLE_DEBUG,
    ADB_DEVICES,
    ADB_GET_STATE,
    ADB_LOGCAT,
    ADB_DUMPSYS,
    ADB_UI_DUMP,
    ADB_SCREENCAP,
    ADB_INSTALL,
    ADB_START_APP,
    ADB_FORCE_STOP,
]


def _normalize(tokens: List[str]) -> List[str]:
    """Normalise une liste de tokens (enlève -s <device> s'il est présent)."""
    result = []
    skip_next = False
    for i, token in enumerate(tokens):
        if skip_next:
            skip_next = False
            continue
        if token == "-s" and i + 1 < len(tokens):
            skip_next = True
            continue
        result.append(token)
    return result


def classify_command(command: List[str]) -> Optional[AllowedCommand]:
    """Vérifie si une commande tokenisée correspond à une commande autorisée."""
    normalized = _normalize(command)
    for allowed in ALLOWED_COMMANDS:
        if not normalized[: len(allowed.base)] == list(allowed.base):
            continue

        remaining = normalized[len(allowed.base) :]
        valid = True
        for token in remaining:
            if token in allowed.allowed_args:
                continue
            if any(re.fullmatch(pattern, token) for pattern in allowed.arg_patterns):
                continue
            valid = False
            break

        if valid:
            return allowed
    return None


def validate_shell_command(cmd_string: str) -> Tuple[bool, str]:
    """Valide une chaîne de commande shell brute.

    Retourne (ok, raison). Ne permet jamais les métacaractères dangereux.
    """
    forbidden = [";", "&&", "||", "|", "`", "$", "<", ">", "\n", "\r"]
    for char in forbidden:
        if char in cmd_string:
            return False, f"Caractère interdit dans la commande: {char!r}"

    try:
        tokens = shlex.split(cmd_string)
    except ValueError as e:
        return False, f"Impossible de parser la commande: {e}"

    if not tokens:
        return False, "Commande vide"

    allowed = classify_command(tokens)
    if allowed is None:
        return False, "Commande non autorisée"

    return True, allowed.family
