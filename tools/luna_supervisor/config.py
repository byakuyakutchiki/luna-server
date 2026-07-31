"""Configuration du Luna Agent Supervisor.

La configuration est chargée depuis un fichier `.env.supervisor` local non versionné,
puis surchargée par les variables d'environnement.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Charge .env.supervisor s'il existe, sans écraser les variables déjà présentes.
try:
    from dotenv import load_dotenv
    env_supervisor = Path(__file__).resolve().parents[2] / ".env.supervisor"
    if env_supervisor.exists():
        load_dotenv(dotenv_path=env_supervisor, override=False, verbose=False)
except Exception:
    pass

DEFAULTS: Dict[str, Any] = {
    "PROJECT_PATH": "/home/ludo/luna-server",
    "RUNS_DIR": "runs",
    "RUNNER_ID": "luna-vm-01",
    "ANDROID_DEVICE_ID": "",
    "ANDROID_PACKAGE": "fr.yawatch.luna",
    "ANDROID_MAIN_ACTIVITY": "fr.yawatch.luna.MainActivity",
    "N8N_NEXT_JOB_URL": "",
    "N8N_REPORT_URL": "",
    "N8N_HEADER_NAME": "",
    "N8N_HEADER_VALUE": "",
    "POLL_INTERVAL_SECONDS": 1800,
    "MAX_ITERATIONS": 3,
    "LOG_LEVEL": "INFO",
    # Budget
    "BUDGET_FILE": "runs/supervisor-budget.json",
    "MAX_AI_CALLS_PER_DAY": 8,
    "MAX_KIMI_CALLS_PER_DAY": 5,
    "MAX_DEEPSEEK_CALLS_PER_DAY": 1,
    "MAX_CODEX_CALLS_PER_DAY": 2,
    "MAX_REVIEW_CALLS_PER_DAY": 2,
    "MAX_CALLS_PER_MISSION": 12,
    "MAX_SAME_ERROR_ATTEMPTS": 2,
    "MAX_CONTEXT_CHARACTERS": 60000,
    "MAX_LOG_LINES_FOR_AI": 250,
    "MAX_PARALLEL_JOBS": 1,
    # Agents
    "KIMI_CLI": "/home/ludo/.kimi-code/bin/kimi",
    "DEEPSEEK_API_KEY": "",
    "OPENAI_API_KEY": "",
    "OPENAI_MODEL": "gpt-4o-mini",
    "DEEPSEEK_MODEL": "deepseek-chat",
}


def _coerce(key: str, current: Any, value: str) -> Any:
    """Convertit une variable d'environnement vers le type de la valeur par défaut."""
    if isinstance(current, bool):
        return value.lower() in ("1", "true", "yes")
    if isinstance(current, int):
        try:
            return int(value)
        except ValueError:
            return current
    return value


def load_config(project_path: Optional[str] = None) -> Dict[str, Any]:
    """Charge la configuration depuis les valeurs par défaut, le fichier JSON
    runner si présent, puis les variables d'environnement."""
    config = dict(DEFAULTS)

    if project_path:
        config["PROJECT_PATH"] = project_path

    project = Path(config["PROJECT_PATH"]).resolve()

    # Fusionne la config du runner si elle existe (évite la duplication)
    runner_config_file = project / ".runner_config.json"
    if runner_config_file.exists():
        try:
            with open(runner_config_file, "r", encoding="utf-8") as f:
                runner_config = json.load(f)
            for key in ("N8N_NEXT_JOB_URL", "N8N_REPORT_URL", "N8N_HEADER_NAME",
                        "N8N_HEADER_VALUE", "RUNNER_ID", "ANDROID_DEVICE_ID",
                        "ANDROID_PACKAGE", "ANDROID_MAIN_ACTIVITY"):
                if key in runner_config:
                    config[key] = runner_config[key]
        except Exception:
            pass

    # Surcharge par les variables d'environnement
    for key in config:
        env_value = os.getenv(key)
        if env_value is not None:
            config[key] = _coerce(key, config[key], env_value)

    config["PROJECT_PATH"] = str(project)
    config["RUNS_DIR"] = str(project / config["RUNS_DIR"])
    config["BUDGET_FILE"] = str(project / config["BUDGET_FILE"])
    return config


def require(config: Dict[str, Any], key: str) -> Any:
    value = config.get(key)
    if value is None or value == "":
        raise RuntimeError(f"Configuration manquante: {key}")
    return value
