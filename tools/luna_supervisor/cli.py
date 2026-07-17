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
from . import mission_queue
from . import safety
from .agent_connectivity import run_audit, write_report
from .next_mission_planner import NextMissionPlanner
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


def cmd_plan_next(args: argparse.Namespace) -> int:
    """Propose ou crée automatiquement la prochaine mission sûre."""
    config = load_config(args.config)
    planner = NextMissionPlanner(config)
    plan = planner.plan(auto_next=args.auto_next)
    path = planner.write_report(plan)
    print(json.dumps(plan, indent=2, ensure_ascii=False))
    print(f"Rapport planificateur: {path}")
    return 0


def cmd_agent_connectivity(args: argparse.Namespace) -> int:
    """Audit de connectivité des agents sans appel IA ni exposition de secrets."""
    result = run_audit(args.config)
    path = write_report(result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\nRapport d'audit: {path}")
    return 0 if result.get("overall_status") in ("ok", "limited") else 1


def cmd_create(args: argparse.Namespace) -> int:
    """Crée et soumet une mission Luna depuis un prompt texte ou un fichier."""
    project_path = Path(args.project_path).resolve()

    # Détermine le prompt source
    if args.prompt_file:
        ok, payload_or_reason = safety.validate_prompt_file(Path(args.prompt_file))
        if not ok:
            print(f"ERREUR: fichier prompt interdit - {payload_or_reason}", file=sys.stderr)
            return 1
        prompt_text = payload_or_reason
    else:
        prompt_text = args.prompt

    if not prompt_text:
        print("ERREUR: prompt vide", file=sys.stderr)
        return 1

    # Validation de sécurité côté client
    ok, reason = safety.validate_prompt(prompt_text)
    if not ok:
        print(f"ERREUR: prompt interdit - {reason}", file=sys.stderr)
        return 1

    raw: Dict[str, Any] = {
        "mission_id": args.mission_id or f"PROMPT-{int(time.time())}",
        "objective": prompt_text,
        "role": args.role,
        "max_iterations": args.max_iterations,
        "priority": args.priority,
        "auto_next": args.auto_next,
    }
    if args.expected_final_status:
        raw["expected_final_status"] = args.expected_final_status
    if args.prefix:
        raw["mission_id"] = f"{args.prefix}-{int(time.time())}"

    try:
        payload = mission_queue.build_mission_payload(raw)
    except ValueError as e:
        print(f"Validation mission échouée: {e}", file=sys.stderr)
        return 1

    env = mission_queue.load_env_supervisor(project_path)
    try:
        result = mission_queue.submit_mission(
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

    create_parser = sub.add_parser("create", help="Crée et soumet une mission autonome")
    prompt_group = create_parser.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("prompt", nargs="?", default=None, help="Objectif de la mission")
    prompt_group.add_argument("--prompt-file", default=None, help="Chemin vers un fichier Markdown ou TXT contenant l'objectif")

    plan_next = sub.add_parser("plan-next", help="Propose ou crée la prochaine mission sûre depuis la roadmap")
    plan_next.add_argument("--auto-next", action="store_true", help="Crée automatiquement la mission dans mission_store")

    sub.add_parser("agent-connectivity", help="Audit la connectivité des agents sans appel IA")

    create_parser.add_argument("--project-path", default=".", help="Chemin racine du projet Luna")
    create_parser.add_argument("--role", default="operator", choices=("operator", "auditor", "coordinator", "reviewer"))
    create_parser.add_argument("--max-iterations", type=int, default=1)
    create_parser.add_argument("--expected-final-status", default=None)
    create_parser.add_argument("--priority", default="normal", choices=("low", "normal", "high", "critical"))
    create_parser.add_argument("--prefix", default=None, help="Préfixe de l'ID de mission généré")
    create_parser.add_argument("--mission-id", default=None, help="ID de mission explicite (écrase le préfixe)")
    create_parser.add_argument("--auto-next", action="store_true", help="Autorise le superviseur à planifier la mission suivante après celle-ci")

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
        "plan-next": cmd_plan_next,
        "agent-connectivity": cmd_agent_connectivity,
        "create": cmd_create,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
