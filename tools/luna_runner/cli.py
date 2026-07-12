"""Interface en ligne de commande du Luna Local Runner."""

import argparse
import json
import sys
from pathlib import Path

from .config import load_config
from .runner import Runner


def cmd_health(args: argparse.Namespace) -> int:
    runner = Runner()
    result = runner.health()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("adb_available") and result.get("device_connected") else 1


def cmd_poll_once(args: argparse.Namespace) -> int:
    runner = Runner()
    response = runner.poll_once()
    print(json.dumps(response, indent=2, ensure_ascii=False))
    if response.get("status") == "idle":
        print("Aucune mission disponible.")
        return 0
    print("Mission recue.")
    return 0


def cmd_execute_diagnostic(args: argparse.Namespace) -> int:
    runner = Runner()
    mission_id = args.mission_id
    task_id = args.task_id or mission_id
    result = runner.execute_diagnostic(mission_id, task_id)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\nPreuves disponibles dans: {result['evidence_directory']}")
    return 0 if result["status"] in ("success", "success_with_errors") else 1


def cmd_report(args: argparse.Namespace) -> int:
    runner = Runner()
    result_path = Path(args.result_file)
    if not result_path.exists():
        print(f"Fichier introuvable: {result_path}", file=sys.stderr)
        return 1
    result = json.loads(result_path.read_text(encoding="utf-8"))
    response = runner.send_report(result)
    print(json.dumps(response, indent=2, ensure_ascii=False))
    return 0


def main(argv: list = None) -> int:
    parser = argparse.ArgumentParser(
        prog="luna_runner",
        description="Luna Local Runner - execute des missions Android locales pour n8n.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("health", help="Verifie l'etat du runner et du telephone")

    sub.add_parser("poll-once", help="Interroge n8n une fois pour une mission")

    diag = sub.add_parser(
        "execute-diagnostic",
        help="Execute un diagnostic ADB en lecture seule",
    )
    diag.add_argument("--mission-id", required=True, help="Identifiant de mission")
    diag.add_argument("--task-id", default=None, help="Identifiant de tache (defaut: mission-id)")

    rep = sub.add_parser("report", help="Envoie un result.json a n8n")
    rep.add_argument("result_file", help="Chemin vers result.json")

    args = parser.parse_args(argv)

    commands = {
        "health": cmd_health,
        "poll-once": cmd_poll_once,
        "execute-diagnostic": cmd_execute_diagnostic,
        "report": cmd_report,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
