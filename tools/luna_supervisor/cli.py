"""Interface en ligne de commande du Luna Agent Supervisor."""

import argparse
import json
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .config import load_config
from .supervisor import LunaAgentSupervisor

logger = logging.getLogger(__name__)


def _setup_logging(log_level: str = "INFO") -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def _load_supervisor(config_path: Optional[str] = None) -> LunaAgentSupervisor:
    config = load_config(config_path)
    _setup_logging(config.get("LOG_LEVEL", "INFO"))
    return LunaAgentSupervisor(config)


def cmd_health(args: argparse.Namespace) -> int:
    sup = _load_supervisor(args.config)
    result = sup.health()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("adb_available") else 1


def cmd_poll_once(args: argparse.Namespace) -> int:
    sup = _load_supervisor(args.config)
    response = sup.poll_once()
    print(json.dumps(response, indent=2, ensure_ascii=False))
    if response and response.get("status") == "idle":
        print("Aucune mission disponible.")
        return 0
    print("Mission reçue.")
    return 0


def cmd_run_once(args: argparse.Namespace) -> int:
    sup = _load_supervisor(args.config)
    mission = None
    if args.mission_file:
        mission = json.loads(Path(args.mission_file).read_text(encoding="utf-8"))
    result = sup.run_once(mission_override=mission)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("status") in ("success", "complete", "idle", "waiting_human_approval") else 1


def cmd_dry_run(args: argparse.Namespace) -> int:
    """Exécute un cycle de test avec une mission simulée en lecture seule."""
    sup = _load_supervisor(args.config)
    mission = {
        "mission_id": "DRY-RUN-001",
        "task_id": "DRY-RUN-001",
        "role": "operator",
        "objective": "Mission de test sec. Lire le README.md et retourner une décision complete sans rien modifier.",
        "iteration": 0,
        "max_iterations": 1,
    }
    result = sup.run_once(mission_override=mission)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Vérifie qu'aucune modification n'a été faite
    diff = result.get("git_diff", "")
    if diff.strip():
        print("\n⚠️ ATTENTION: des modifications ont été détectées après le dry-run.")
        print(diff[:500])
        return 1

    print("\n✅ Dry-run terminé sans modification.")
    return 0 if result.get("status") in ("success", "complete") else 1


def cmd_daemon(args: argparse.Namespace) -> int:
    """Boucle permanente de récupération et traitement des missions."""
    sup = _load_supervisor(args.config)
    config = sup.config
    poll_interval = int(config.get("POLL_INTERVAL_SECONDS", 1800))
    max_consecutive_errors = 3
    consecutive_errors = 0

    def _handle_signal(signum, frame):
        logger.info("Signal %s reçu, arrêt du daemon", signum)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    logger.info("Daemon Luna Agent Supervisor démarré (poll_interval=%ss)", poll_interval)

    while True:
        sleep_seconds = poll_interval
        try:
            result = sup.run_once()
            status = result.get("status")
            if status == "idle":
                logger.info("Aucune mission. Pause de %ss", poll_interval)
            elif status == "in_progress":
                logger.info("Mission en cours, reprise rapide...")
                sleep_seconds = 10
                consecutive_errors = 0
            elif status in ("success", "complete", "needs_audit"):
                logger.info("Mission traitée avec succès: %s", result.get("mission_id"))
                consecutive_errors = 0
            elif status == "waiting_human_approval":
                logger.info("Mission en attente de validation humaine: %s", result.get("mission_id"))
                consecutive_errors = 0
            else:
                logger.error("Échec mission: %s", result.get("error_summary"))
                consecutive_errors += 1
        except Exception as e:
            logger.exception("Erreur inattendue dans le daemon")
            consecutive_errors += 1

        if consecutive_errors >= max_consecutive_errors:
            logger.error("%d erreurs consécutives. Arrêt du daemon.", consecutive_errors)
            return 1

        time.sleep(sleep_seconds)


def cmd_status(args: argparse.Namespace) -> int:
    sup = _load_supervisor(args.config)
    health = sup.health()
    lock_active = sup.lock_file.exists()
    print(json.dumps({"health": health, "locked": lock_active}, indent=2, ensure_ascii=False))
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    sup = _load_supervisor(args.config)
    sup.release_lock()
    print("Verrou supprimé.")
    return 0


def cmd_morning_report(args: argparse.Namespace) -> int:
    sup = _load_supervisor(args.config)
    path = sup.generate_morning_report()
    print(f"Rapport du matin généré: {path}")
    return 0


def main(argv: list = None) -> int:
    parser = argparse.ArgumentParser(
        prog="luna_supervisor",
        description="Luna Agent Supervisor - cellule autonome multi-agents.",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Chemin vers un fichier de configuration (par défaut: .env.supervisor + .runner_config.json)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("health", help="Vérifie l'état du superviseur, d'ADB et du budget")
    sub.add_parser("poll-once", help="Interroge n8n une fois pour une mission")

    run_once = sub.add_parser("run-once", help="Exécute un cycle complet (optionnellement avec un fichier mission)")
    run_once.add_argument("--mission-file", default=None, help="Fichier JSON contenant la mission simulée")

    sub.add_parser("dry-run", help="Exécute un cycle de test en lecture seule")
    sub.add_parser("daemon", help="Démarre la boucle permanente")
    sub.add_parser("status", help="Affiche l'état et le verrou")
    sub.add_parser("stop", help="Supprime le verrou du superviseur")
    sub.add_parser("morning-report", help="Génère le rapport du matin sans appel IA")

    args = parser.parse_args(argv)

    commands = {
        "health": cmd_health,
        "poll-once": cmd_poll_once,
        "run-once": cmd_run_once,
        "dry-run": cmd_dry_run,
        "daemon": cmd_daemon,
        "status": cmd_status,
        "stop": cmd_stop,
        "morning-report": cmd_morning_report,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
