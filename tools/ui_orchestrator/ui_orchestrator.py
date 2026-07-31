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

from approval_detector import ApprovalDetector, ApprovalRequest
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


def run_approval_test(config: Dict[str, Any], args: argparse.Namespace) -> int:
    """Exécute une batterie de cas d'approbation simulés."""
    logger = logging.getLogger("ui_orchestrator")
    if not args.simulate:
        logger.error("Mode --simulate requis en V0. Aucune action réelle n'est autorisée.")
        return 1

    orchestrator_cfg = config.get("orchestrator", {})
    shared_dir = orchestrator_cfg.get("shared_dir", "/tmp/ui_orchestrator")
    mission_id = args.mission_id

    exchange = ExchangeManager(shared_dir)
    exchange.ensure_directories()

    policy = Policy.from_config(config)
    detector = ApprovalDetector(policy)

    test_cases = [
        ("kimi", "terminal", "cd /home/ludo/luna-server && git status --short"),
        ("kimi", "terminal", "pytest"),
        ("kimi", "terminal", 'rg "Guardian" static/guardian.html'),
        ("kimi", "terminal", "git diff --stat"),
        ("codex", "codex", "git push origin main"),
        ("codex", "codex", "gcloud run deploy luna-beta"),
        ("kimi", "terminal", "rm -rf /home/ludo/luna-server"),
        ("kimi", "terminal", "git reset --hard"),
        ("kimi", "terminal", "git clean -fd"),
        ("kimi", "terminal", "adb shell input tap 100 200"),
        ("kimi", "unknown", "git status --short"),
        ("kimi", "terminal", ""),
        ("kimi", "terminal", "export OPENAI_API_KEY=sk-12345678901234567890abcdef"),
    ]

    decisions = []
    for source, window_role, action in test_cases:
        request = ApprovalRequest(
            source=source,
            window_role=window_role,
            prompt_text="Run this command?",
            action_text=action,
            buttons=["Approve once", "Approve for session", "Reject"],
        )
        decision = detector.detect(request)
        decisions.append(decision)

        log_entry = {
            "event": "approval_decision",
            "source": source,
            "window_role": window_role,
            "action_text": action,
            "action_type": decision.action_type,
            "risk_level": decision.risk_level,
            "would_approve": decision.would_approve,
            "requires_human": decision.requires_human,
            "target_button": decision.target_button,
            "reason": decision.reason,
            "simulate": True,
            "real_click": False,
        }
        exchange.write_log(mission_id, log_entry)
        logger.info(
            "[%s] %s | risk=%s | approve=%s | human=%s | reason=%s",
            source,
            action or "<empty>",
            decision.risk_level,
            decision.would_approve,
            decision.requires_human,
            decision.reason,
        )

    # Cas spécifique : bouton "Approve for session" seul
    session_only_request = ApprovalRequest(
        source="kimi",
        window_role="terminal",
        prompt_text="Run this command?",
        action_text="git status --short",
        buttons=["Approve for session", "Reject"],
    )
    session_decision = detector.detect(session_only_request)
    decisions.append(session_decision)
    exchange.write_log(
        mission_id,
        {
            "event": "approval_decision",
            "source": "kimi",
            "window_role": "terminal",
            "action_text": "git status --short",
            "action_type": session_decision.action_type,
            "risk_level": session_decision.risk_level,
            "would_approve": session_decision.would_approve,
            "requires_human": session_decision.requires_human,
            "target_button": session_decision.target_button,
            "reason": session_decision.reason,
            "simulate": True,
            "real_click": False,
        },
    )

    report_path = exchange.write_simulation_report(
        mission_id,
        {
            "mission_id": mission_id,
            "test_type": "approval_detection",
            "simulate": True,
            "real_click": False,
            "real_approve": False,
            "decision_count": len(decisions),
            "would_approve_count": sum(1 for d in decisions if d.would_approve),
            "requires_human_count": sum(1 for d in decisions if d.requires_human),
            "decisions": [
                {
                    "approval_detected": d.approval_detected,
                    "action_text": d.action_text,
                    "action_type": d.action_type,
                    "risk_level": d.risk_level,
                    "would_approve": d.would_approve,
                    "requires_human": d.requires_human,
                    "target_button": d.target_button,
                    "reason": d.reason,
                }
                for d in decisions
            ],
        },
    )

    print(f"\n🛡️  Test d'approbation terminé : {mission_id}")
    print(f"   Décisions simulées : {len(decisions)}")
    print(f"   Would approve      : {sum(1 for d in decisions if d.would_approve)}")
    print(f"   Requires human     : {sum(1 for d in decisions if d.requires_human)}")
    print(f"   Rapport            : {report_path}")
    return 0


def main(argv: list = None) -> int:
    parser = argparse.ArgumentParser(
        description="luna-ui-orchestrator — V0 simulation sans clic réel.",
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Chemin vers la config YAML")
    parser.add_argument("--simulate", action="store_true", help="Mode simulation obligatoire en V0")
    parser.add_argument("--mission-id", default="SIMULATION-001", help="ID de mission simulée")
    parser.add_argument("--probe-windows", action="store_true", help="Détecter/classer les fenêtres Windows (simulation sur Linux)")
    parser.add_argument("--approval-test", action="store_true", help="Batterie de tests de détection d'approbation simulée")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    setup_logging(config.get("orchestrator", {}).get("log_level", "INFO"))

    if args.probe_windows:
        return run_probe_windows(config, args)

    if args.approval_test:
        return run_approval_test(config, args)

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
