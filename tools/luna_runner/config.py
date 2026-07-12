"""Configuration du Luna Local Runner.

La configuration est chargée depuis un fichier JSON local non versionné
(.runner_config.json à la racine du projet) puis surchargée par les variables
d'environnement.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Charge .env.runner s'il existe, sans ecraser les variables deja presentes.
try:
    from dotenv import load_dotenv
    env_runner = Path(__file__).resolve().parents[2] / ".env.runner"
    if env_runner.exists():
        load_dotenv(dotenv_path=env_runner, override=False, verbose=False)
except Exception:
    pass

DEFAULTS: Dict[str, Any] = {
    "PROJECT_PATH": "/home/ludo/luna-server",
    "ANDROID_PACKAGE": "fr.yawatch.luna",
    "RUNS_DIR": "runs",
    "ADB_TIMEOUT": 60,
    "BUILD_TIMEOUT": 300,
    "MAX_ITERATIONS": 3,
    "DAILY_CALL_LIMIT": 100,
    "POLL_INTERVAL_SECONDS": 30,
    "N8N_NEXT_JOB_URL": "",
    "N8N_REPORT_URL": "",
    "RUNNER_ID": "luna-local-runner",
    "ANDROID_DEVICE_ID": "",
}

CONFIG_FILENAMES = [
    ".runner_config.json",
    ".runner_config.local.json",
]


def _find_config_file(project_path: Path) -> Optional[Path]:
    for name in CONFIG_FILENAMES:
        candidate = project_path / name
        if candidate.exists():
            return candidate
    return None


def load_config(project_path: Optional[str] = None) -> Dict[str, Any]:
    """Charge la configuration depuis fichier + env."""
    config = dict(DEFAULTS)

    if project_path:
        config["PROJECT_PATH"] = project_path

    project = Path(config["PROJECT_PATH"]).resolve()
    config_file = _find_config_file(project)
    if config_file:
        with open(config_file, "r", encoding="utf-8") as f:
            file_config = json.load(f)
        config.update(file_config)

    # Surcharge par les variables d'environnement
    for key in config:
        env_value = os.getenv(key)
        if env_value is not None:
            if isinstance(config[key], bool):
                config[key] = env_value.lower() in ("1", "true", "yes")
            elif isinstance(config[key], int):
                config[key] = int(env_value)
            else:
                config[key] = env_value

    config["PROJECT_PATH"] = str(Path(config["PROJECT_PATH"]).resolve())
    config["RUNS_DIR"] = str(Path(config["PROJECT_PATH"]) / config["RUNS_DIR"])
    return config


def require(config: Dict[str, Any], key: str) -> Any:
    value = config.get(key)
    if not value:
        raise RuntimeError(f"Configuration manquante: {key}")
    return value
