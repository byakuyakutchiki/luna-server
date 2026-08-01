"""Helper d'injection de mission dans n8n.

Lit un fichier mission JSON local et l'envoie au webhook n8n
Luna Mission Create. Ne fait jamais apparaitre de secret en clair.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

DEFAULT_MISSION_DIR = "runs/missions"
DEFAULT_WEBHOOK_PATH = "/webhook/luna-mission-create"


def load_env_supervisor(project_path: Path) -> Dict[str, str]:
    """Charge .env.supervisor sans exposer les valeurs."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        load_dotenv = None

    env_path = project_path / ".env.supervisor"
    if load_dotenv and env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False, verbose=False)

    return {
        "header_name": os.getenv("N8N_HEADER_NAME", "X-Luna-Runner-Key"),
        "header_value": os.getenv("N8N_HEADER_VALUE", ""),
        "base_url": _base_url_from_next_job(),
    }


def _base_url_from_next_job() -> str:
    url = os.getenv("N8N_NEXT_JOB_URL", "")
    if url:
        # Extrait la base avant /webhook/
        parts = url.split("/webhook/")
        if parts:
            return parts[0].rstrip("/")
    return ""


def _budget_limits_from_policy() -> Dict[str, int]:
    """Expose les limites IA reelles dans le contexte de mission envoye a n8n."""
    fallback = {
        "kimi_per_day": 4,
        "deepseek_per_day": 1,
        "review_per_day": 1,
        "codex_per_day": 0,
        "total_per_day": 6,
    }
    policy_path = Path(__file__).resolve().parents[2] / "config" / "agent_budget_policy.yaml"
    if yaml is None or not policy_path.exists():
        return fallback
    try:
        policy = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
        providers = policy.get("providers", {})

        def daily(provider: str, default: int) -> int:
            return int(providers.get(provider, {}).get("max_calls_per_day", default))

        return {
            "kimi_per_day": daily("kimi", fallback["kimi_per_day"]),
            "deepseek_per_day": daily("deepseek", fallback["deepseek_per_day"]),
            "review_per_day": daily("review", fallback["review_per_day"]),
            "codex_per_day": daily("codex", fallback["codex_per_day"]),
            "total_per_day": int(policy.get("max_total_ai_calls_per_day", fallback["total_per_day"])),
        }
    except Exception:
        return fallback


def build_mission_payload(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Construit le payload attendu par le workflow Luna Mission Create."""
    mission_id = raw.get("mission_id", "")
    objective = raw.get("objective", "") or raw.get("description", "")
    role = raw.get("role", "operator")
    max_iterations = int(raw.get("max_iterations", 3))

    if not mission_id:
        raise ValueError("mission_id obligatoire")
    if not objective:
        raise ValueError("objective obligatoire")
    if role not in ("operator", "auditor", "coordinator", "reviewer"):
        raise ValueError(f"role invalide: {role}")
    if not 1 <= max_iterations <= 8:
        raise ValueError(f"max_iterations hors limites: {max_iterations}")

    mission_context = {
        "objective": objective,
        "priority": raw.get("priority", "normal"),
        "role": role,
        "source": "luna-mission-create",
        "created_by": "Ludovic",
        "guardian_anti_regression": True,
        "charte_produit": "config/luna_mission_charter.yaml",
        "auto_next": bool(raw.get("auto_next", False)),
        "budget_limits": _budget_limits_from_policy(),
        "forbidden_actions": raw.get(
            "forbidden_actions",
            [
                "push",
                "merge",
                "reset_hard",
                "real_sms",
                "real_call",
                "production_deploy",
                "secret_modification",
                "cloud_modification",
                "user_data_deletion",
            ],
        ),
    }

    payload = {
        "mission_id": mission_id,
        "task_id": raw.get("task_id", mission_id),
        "role": role,
        "priority": raw.get("priority", "normal"),
        "objective": objective,
        "max_iterations": max_iterations,
        "status": "queued",
        "budget_allowed": True,
        "approval_required": False,
        "current_role": role,
        "next_role": raw.get("next_role", role),
        "iteration": int(raw.get("iteration", 0)),
        "mission_context_json": json.dumps(mission_context, ensure_ascii=False),
    }

    if "expected_final_status" in raw:
        payload["expected_final_status"] = raw["expected_final_status"]
        mission_context["expected_final_status"] = raw["expected_final_status"]
        payload["mission_context_json"] = json.dumps(mission_context, ensure_ascii=False)

    if "allows_guardian_modification" in raw:
        payload["allows_guardian_modification"] = bool(raw["allows_guardian_modification"])
        mission_context["allows_guardian_modification"] = bool(raw["allows_guardian_modification"])
        payload["mission_context_json"] = json.dumps(mission_context, ensure_ascii=False)

    return payload


def submit_mission(
    payload: Dict[str, Any],
    base_url: str,
    header_name: str,
    header_value: str,
) -> Dict[str, Any]:
    """Envoie la mission au webhook n8n."""
    if not base_url:
        raise RuntimeError("URL de base n8n non configuree")
    if not header_value:
        raise RuntimeError("Valeur du header d'authentification manquante")

    url = f"{base_url}{DEFAULT_WEBHOOK_PATH}"
    headers = {
        "Content-Type": "application/json",
        header_name: header_value,
    }
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    try:
        body = response.json()
    except Exception:
        body = {"_raw": response.text}
    # Le workflow n8n peut retourner une liste d'items ; on normalise en dict.
    if isinstance(body, list) and body:
        body = body[0]
    if not isinstance(body, dict):
        body = {"_raw": str(body)}
    body["_http_status"] = response.status_code
    return body


def _cmd_submit(args: argparse.Namespace) -> int:
    project_path = Path(args.project_path).resolve()
    mission_file = Path(args.mission_file)
    if not mission_file.is_absolute():
        mission_file = project_path / mission_file

    if not mission_file.exists():
        print(f"Fichier mission introuvable: {mission_file}", file=sys.stderr)
        return 1

    raw = json.loads(mission_file.read_text(encoding="utf-8"))
    return _submit_raw(raw, project_path)


def _cmd_create_from_prompt(args: argparse.Namespace) -> int:
    project_path = Path(args.project_path).resolve()
    prefix = args.prefix or "PROMPT"
    mission_id = f"{prefix}-{int(time.time())}"

    raw: Dict[str, Any] = {
        "mission_id": mission_id,
        "objective": args.prompt,
        "role": args.role,
        "max_iterations": args.max_iterations,
        "priority": args.priority,
    }
    if args.expected_final_status:
        raw["expected_final_status"] = args.expected_final_status

    mission_file = project_path / DEFAULT_MISSION_DIR / f"{mission_id}.json"
    mission_file.parent.mkdir(parents=True, exist_ok=True)
    mission_file.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Fichier créé: {mission_file}")

    return _submit_raw(raw, project_path)


def _submit_raw(raw: Dict[str, Any], project_path: Path) -> int:
    try:
        payload = build_mission_payload(raw)
    except ValueError as e:
        print(f"Validation mission echouee: {e}", file=sys.stderr)
        return 1

    env = load_env_supervisor(project_path)
    try:
        result = submit_mission(
            payload,
            env["base_url"],
            env["header_name"],
            env["header_value"],
        )
    except Exception as e:
        print(f"Erreur envoi mission: {e}", file=sys.stderr)
        return 1

    status = result.get("status", result.get("_http_status"))
    mission_id = result.get("mission_id", payload["mission_id"])
    print(f"mission_id={mission_id}")
    print(f"status={status}")
    return 0 if str(status).lower() == "queued" else 1


def _add_project_path(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--project-path",
        default=".",
        help="Chemin racine du projet Luna",
    )


def main(argv: list = None) -> int:
    parser = argparse.ArgumentParser(
        description="Injecte une mission Luna dans n8n via Luna Mission Create"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    submit_parser = sub.add_parser("submit", help="Soumet un fichier mission JSON")
    _add_project_path(submit_parser)
    submit_parser.add_argument(
        "mission_file",
        help="Chemin vers le fichier JSON de la mission (ex: runs/missions/GUARDIAN-AUTONOMOUS-001.json)",
    )

    create_parser = sub.add_parser("create-from-prompt", help="Crée et soumet une mission à partir d'un prompt")
    _add_project_path(create_parser)
    create_parser.add_argument("--prompt", required=True, help="Objectif de la mission")
    create_parser.add_argument("--role", default="operator", choices=("operator", "auditor", "coordinator", "reviewer"))
    create_parser.add_argument("--max-iterations", type=int, default=1)
    create_parser.add_argument("--expected-final-status", default=None)
    create_parser.add_argument("--priority", default="normal", choices=("low", "normal", "high", "critical"))
    create_parser.add_argument("--prefix", default="PROMPT", help="Préfixe de l'ID de mission généré")

    args = parser.parse_args(argv)

    if args.command == "submit":
        return _cmd_submit(args)
    if args.command == "create-from-prompt":
        return _cmd_create_from_prompt(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
