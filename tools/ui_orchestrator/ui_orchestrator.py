#!/usr/bin/env python3
"""luna-ui-orchestrator — V0 simulation.

Aucun clic réel, aucun envoi réel, aucune approbation réelle.
L'orchestrateur simule le transfert Kimi ↔ Codex via dossier partagé.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

import yaml

from exchange import ExchangeManager
from policy import Policy
from state_machine import StateMachine, Transition
from window_detector import WindowDetector


DEFAULT_CONFIG = Path(__file__).with_suffix("").parent / "config" / "orchestrator_config.yaml"


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def load_config(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def run_probe_windows(config: Dict[str, Any], args: argparse.Namespace) -> int:
    """Exécute une détection de fenêtres (simulation si non-Windows)."""
    logger = logging.getLogger("ui_orchestrator")
    if not args.simulate:
        logger.error("Mode --simulate requis en V0. Aucune action réelle n'est autorisée.")
        return 1

    orchestrator_cfg = config.get("orchestrator", {})
    shared_dir = orchestrator_cfg.get("shared_dir", "/tmp/ui_orchestrator")

    detector = WindowDetector(config, shared_dir)
    windows = detector.probe_windows(simulate=True)
    matched = detector.classify(windows)

    report_path = detector.write_probe_report(args.mission_id, windows, matched)

    print(f"\n🔍 Probe Windows terminé : {args.mission_id}")
    print(f"   Fenêtres détectées : {len(windows)}")
    for role, wins in matched.items():
        if wins:
            print(f"   - {role}: {len(wins)}")
    print(f"   Rapport : {report_path}")
    return 0


def main(argv: list = None) -> int:
    parser = argparse.ArgumentParser(
        description="luna-ui-orchestrator — V0 simulation sans clic réel.",
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Chemin vers la config YAML")
    parser.add_argument("--simulate", action="store_true", help="Mode simulation obligatoire en V0")
    parser.add_argument("--mission-id", default="SIMULATION-001", help="ID de mission simulée")
    parser.add_argument("--probe-windows", action="store_true", help="Détecter/classer les fenêtres Windows (simulation sur Linux)")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    setup_logging(config.get("orchestrator", {}).get("log_level", "INFO"))

    if args.probe_windows:
        return run_probe_windows(config, args)

    config = load_config(args.config)
    setup_logging(config.get("orchestrator", {}).get("log_level", "INFO"))
    logger = logging.getLogger("ui_orchestrator")

    if not args.simulate:
        logger.error("Mode --simulate requis en V0. Aucune action réelle n'est autorisée.")
        return 1

    orchestrator_cfg = config.get("orchestrator", {})
    shared_dir = orchestrator_cfg.get("shared_dir", "/tmp/ui_orchestrator")
    mission_id = args.mission_id

    exchange = ExchangeManager(shared_dir)
    exchange.ensure_directories()

    log_entries: list = []

    def log_transition(transition: Transition) -> None:
        entry = {
            "state_from": transition.state_from,
            "state_to": transition.state_to,
            "event": transition.event,
            "safe_mode": True,
            "simulate": True,
        }
        log_entries.append(entry)
        exchange.write_log(mission_id, entry)
        logger.info("%s -> %s (%s)", transition.state_from, transition.state_to, transition.event)

    sm = StateMachine(
        initial_state=config.get("state_machine", {}).get("initial_state", "WAITING_FOR_KIMI"),
        terminal_states=config.get("state_machine", {}).get("terminal_states"),
        on_transition=log_transition,
    )

    policy = Policy.from_config(config)

    # Arrêt d'urgence
    if exchange.stop_file_exists():
        logger.warning("Fichier STOP détecté. Passage en PAUSED.")
        sm.transition("stop_file_detected", "PAUSED", {"stop_file": str(exchange.shared_dir / "STOP")})
        exchange.write_state(
            {
                "mission_id": mission_id,
                "state": sm.state,
                "simulate": True,
                "stopped": True,
            }
        )
        exchange.write_simulation_report(
            mission_id,
            {
                "mission_id": mission_id,
                "status": sm.state,
                "simulate": True,
                "reason": "Fichier STOP détecté avant simulation",
                "transitions": [(t.state_from, t.state_to, t.event) for t in sm.history()],
            },
        )
        return 0

    # Simulation Kimi -> Codex
    sm.transition("kimi_response_ready", "KIMI_RESPONSE_READY", {"agent": "kimi"})
    sm.transition("copy_response", "COPYING_KIMI_RESPONSE")
    sm.transition("switch_window", "SWITCHING_TO_CODEX")
    sm.transition("send_to_codex", "SENDING_TO_CODEX")

    # Vérification politique avant écriture (même en simulation)
    sample_kimi_action = "git status"
    decision = policy.evaluate(sample_kimi_action)
    logger.info("Policy '%s': allowed=%s human=%s (%s)", sample_kimi_action, decision.allowed, decision.requires_human, decision.reason)

    outbox_path = exchange.write_message(
        "outbox",
        from_agent="kimi",
        to_agent="codex",
        mission_id=mission_id,
        payload={
            "type": "kimi_report",
            "summary": "Rapport Kimi simulé pour validation Codex.",
            "safe_to_continue": decision.allowed and not decision.requires_human,
            "sample_action_checked": sample_kimi_action,
            "sample_action_decision": {
                "allowed": decision.allowed,
                "requires_human": decision.requires_human,
                "reason": decision.reason,
            },
        },
    )
    logger.info("Message Kimi -> Codex simulé : %s", outbox_path)

    # Simulation Codex -> Kimi
    sm.transition("codex_response_ready", "CODEX_RESPONSE_READY", {"agent": "codex"})
    sm.transition("copy_response", "COPYING_CODEX_RESPONSE")
    sm.transition("switch_window", "SWITCHING_TO_KIMI")
    sm.transition("send_to_kimi", "SENDING_TO_KIMI")

    sample_codex_action = "git reset --hard"
    decision = policy.evaluate(sample_codex_action)
    logger.info("Policy '%s': allowed=%s human=%s (%s)", sample_codex_action, decision.allowed, decision.requires_human, decision.reason)

    inbox_path = exchange.write_message(
        "inbox",
        from_agent="codex",
        to_agent="kimi",
        mission_id=mission_id,
        payload={
            "type": "codex_decision",
            "decision": "HUMAN_REVIEW_REQUIRED",
            "reason": "Action interdite détectée dans le rapport Kimi",
            "forbidden_action": sample_codex_action,
            "safe_to_continue_automatically": False,
            "sample_action_decision": {
                "allowed": decision.allowed,
                "requires_human": decision.requires_human,
                "reason": decision.reason,
            },
        },
    )
    logger.info("Message Codex -> Kimi simulé : %s", inbox_path)

    # Fin simulation
    if decision.allowed:
        sm.transition("mission_validated", "MISSION_VALIDATED")
    else:
        sm.transition("human_review_required", "HUMAN_REVIEW_REQUIRED")

    state_path = exchange.write_state(
        {
            "mission_id": mission_id,
            "state": sm.state,
            "simulate": True,
            "shared_dir": shared_dir,
        }
    )
    logger.info("État écrit : %s", state_path)

    report_path = exchange.write_simulation_report(
        mission_id,
        {
            "mission_id": mission_id,
            "status": sm.state,
            "simulate": True,
            "real_click": False,
            "real_send": False,
            "transitions": [
                {
                    "state_from": t.state_from,
                    "state_to": t.state_to,
                    "event": t.event,
                    "timestamp": t.timestamp,
                }
                for t in sm.history()
            ],
            "messages": {
                "kimi_to_codex": str(outbox_path),
                "codex_to_kimi": str(inbox_path),
            },
            "policy_checks": [
                {"action": "git status", "allowed": True},
                {"action": "git reset --hard", "allowed": False, "reason": "Pattern interdit"},
            ],
        },
    )
    logger.info("Rapport de simulation écrit : %s", report_path)

    print(f"\n✅ Simulation terminée : {mission_id}")
    print(f"   État final      : {sm.state}")
    print(f"   Dossier partagé : {shared_dir}")
    print(f"   Rapport         : {report_path}")
    print(f"   Logs            : {exchange.logs_dir}/orchestrator_YYYYMMDD.jsonl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
