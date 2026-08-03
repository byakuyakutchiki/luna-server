"""Tests unitaires du mapping strict decision=audit -> status.

Ne consomme aucun appel IA.
Injecte des decisions factices dans le superviseur pour verifier :
- audit + action non destructive -> needs_audit
- audit + action destructive + validation -> waiting_human_approval
- audit + action interdite -> waiting_human_approval/blocked
"""

import json
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from luna_supervisor.agent_caller import AgentDecision
from luna_supervisor.config import load_config
from luna_supervisor.supervisor import LunaAgentSupervisor


def _make_supervisor(tmp_path: Path):
    """Cree un superviseur isole dans un repertoire temporaire."""
    config = load_config(project_path=str(tmp_path))
    config["BUDGET_FILE"] = str(tmp_path / "runs" / "supervisor-budget.json")
    config["LOG_LEVEL"] = "ERROR"
    return LunaAgentSupervisor(config)


def _make_decision(
    decision: str = "audit",
    action_type: str = "none",
    requires_human_validation: bool = False,
):
    """Fabrique une decision d'agent conforme."""
    raw = {
        "summary": f"Test decision={decision} action={action_type} validation={requires_human_validation}",
        "decision": decision,
        "requested_action": {"type": action_type},
        "files_relevant": [],
        "expected_result": "test",
        "requires_human_validation": requires_human_validation,
    }
    return AgentDecision(raw, agent_name="kimi")


def _run_mission_with_decision(supervisor, mission, decision):
    """Execute _process_mission en remplacant l'appel agent par la decision fournie."""
    mock_caller = MagicMock()
    mock_caller.name = "kimi"
    mock_caller.is_available.return_value = True
    mock_caller.call.return_value = decision

    with patch("luna_supervisor.supervisor.get_caller", return_value=mock_caller):
        return supervisor._process_mission(mission)


def test_audit_none_without_expected_to_needs_audit():
    """audit + action none + pas d'expected_final_status -> needs_audit.

    Corrige apres SUPERVISOR-STATUS-AUDIT-004 : une decision "audit" ne doit
    jamais se resoudre silencieusement en "success", meme quand aucune action
    concrete n'est demandee (ex: un reviewer qui juge un travail incomplet
    sans redemander de lecture/edition).
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        supervisor = _make_supervisor(tmp_path)
        mission = {
            "mission_id": "TEST-AUDIT-NONE-001",
            "task_id": "TEST-AUDIT-NONE-001",
            "role": "operator",
            "objective": "Verifier comportement audit avec action none",
            "iteration": 0,
            "max_iterations": 1,
            "forbidden_actions": ["real_sms", "real_calls"],
        }
        decision = _make_decision("audit", "none", False)
        result = _run_mission_with_decision(supervisor, mission, decision)
        assert result["status"] == "needs_audit", f"attendu needs_audit, recu {result['status']}"
        assert result.get("requires_human_validation") is False
        print("TEST OK: audit + none sans expected_final_status -> needs_audit")


def test_audit_none_with_expected_to_needs_audit():
    """audit + action none + expected_final_status=needs_audit -> needs_audit."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        supervisor = _make_supervisor(tmp_path)
        mission = {
            "mission_id": "TEST-AUDIT-DECISION-STRICT-001",
            "task_id": "TEST-AUDIT-DECISION-STRICT-001",
            "role": "operator",
            "objective": "Verifier mapping audit non destructif",
            "iteration": 0,
            "max_iterations": 1,
            "expected_final_status": "needs_audit",
            "forbidden_actions": ["real_sms", "real_calls"],
        }
        decision = _make_decision("audit", "none", False)
        result = _run_mission_with_decision(supervisor, mission, decision)
        assert result["status"] == "needs_audit", f"attendu needs_audit, recu {result['status']}"
        assert result.get("requires_human_validation") is False
        print("TEST OK: audit + none + expected_final_status=needs_audit -> needs_audit")


def test_audit_read_files_non_destructive_to_needs_audit():
    """audit + read_files + pas de validation -> needs_audit."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        supervisor = _make_supervisor(tmp_path)
        mission = {
            "mission_id": "TEST-AUDIT-READ-FILES-001",
            "task_id": "TEST-AUDIT-READ-FILES-001",
            "role": "operator",
            "objective": "Verifier mapping audit avec lecture",
            "iteration": 0,
            "max_iterations": 1,
            "forbidden_actions": ["real_sms", "real_calls"],
        }
        decision = _make_decision("audit", "read_files", False)
        result = _run_mission_with_decision(supervisor, mission, decision)
        assert result["status"] == "needs_audit", f"attendu needs_audit, recu {result['status']}"
        assert result.get("requires_human_validation") is False
        print("TEST OK: audit + read_files -> needs_audit")


def test_audit_destructive_with_validation_to_waiting():
    """audit + action destructive + requires_human_validation=true -> waiting_human_approval."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        supervisor = _make_supervisor(tmp_path)
        mission = {
            "mission_id": "TEST-AUDIT-DESTRUCTIVE-001",
            "task_id": "TEST-AUDIT-DESTRUCTIVE-001",
            "role": "operator",
            "objective": "Verifier blocage audit destructif",
            "iteration": 0,
            "max_iterations": 1,
            "forbidden_actions": ["real_sms", "real_calls"],
        }
        decision = _make_decision("audit", "edit_files", True)
        result = _run_mission_with_decision(supervisor, mission, decision)
        assert result["status"] == "waiting_human_approval", f"attendu waiting_human_approval, recu {result['status']}"
        assert result.get("requires_human_validation") is True
        print("TEST OK: audit + edit_files + validation -> waiting_human_approval")


def test_audit_forbidden_action_to_waiting():
    """audit + action explicitement interdite par la mission -> waiting_human_approval/blocked."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        supervisor = _make_supervisor(tmp_path)
        mission = {
            "mission_id": "TEST-AUDIT-FORBIDDEN-001",
            "task_id": "TEST-AUDIT-FORBIDDEN-001",
            "role": "operator",
            "objective": "Verifier blocage audit action interdite",
            "iteration": 0,
            "max_iterations": 1,
            "forbidden_actions": ["real_sms", "real_calls", "commit_local"],
        }
        # On utilise une action valide du superviseur mais interdite par la mission.
        decision = _make_decision("audit", "commit_local", False)
        result = _run_mission_with_decision(supervisor, mission, decision)
        assert result["status"] == "waiting_human_approval", f"attendu waiting_human_approval, recu {result['status']}"
        assert result.get("requires_human_validation") is True
        print("TEST OK: audit + commit_local interdit -> waiting_human_approval")


def test_audit_requires_human_validation_true_non_destructive_to_needs_audit():
    """decision=audit + action non destructif + requires_human_validation=true -> needs_audit."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        supervisor = _make_supervisor(tmp_path)
        mission = {
            "mission_id": "TEST-AUDIT-VALIDATION-FLAG-001",
            "task_id": "TEST-AUDIT-VALIDATION-FLAG-001",
            "role": "operator",
            "objective": "Verifier que requires_human_validation=true sur action non destructive produit needs_audit",
            "iteration": 0,
            "max_iterations": 1,
            "forbidden_actions": ["real_sms", "real_calls"],
        }
        decision = _make_decision("audit", "read_files", True)
        result = _run_mission_with_decision(supervisor, mission, decision)
        assert result["status"] == "needs_audit", f"attendu needs_audit, recu {result['status']}"
        assert result.get("requires_human_validation") is False
        print("TEST OK: audit + read_files + requires_human_validation=true -> needs_audit")


def test_execute_requires_human_validation_true_non_destructive_to_needs_audit():
    """decision=execute + action non destructif + requires_human_validation=true -> needs_audit."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        supervisor = _make_supervisor(tmp_path)
        mission = {
            "mission_id": "TEST-EXECUTE-VALIDATION-FLAG-001",
            "task_id": "TEST-EXECUTE-VALIDATION-FLAG-001",
            "role": "operator",
            "objective": "Verifier que execute + read_files + validation reste non bloquant",
            "iteration": 0,
            "max_iterations": 1,
            "forbidden_actions": ["real_sms", "real_calls"],
        }
        decision = _make_decision("execute", "read_files", True)
        result = _run_mission_with_decision(supervisor, mission, decision)
        assert result["status"] == "needs_audit", f"attendu needs_audit, recu {result['status']}"
        assert result.get("requires_human_validation") is False
        print("TEST OK: execute + read_files + requires_human_validation=true -> needs_audit")


def test_audit_complete_decision_not_overridden():
    """Une decision complete reste complete meme si expected_final_status est needs_audit."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        supervisor = _make_supervisor(tmp_path)
        mission = {
            "mission_id": "TEST-AUDIT-COMPLETE-001",
            "task_id": "TEST-AUDIT-COMPLETE-001",
            "role": "operator",
            "objective": "Verifier que complete reste complete",
            "iteration": 0,
            "max_iterations": 1,
            "expected_final_status": "needs_audit",
        }
        decision = _make_decision("complete", "none", False)
        result = _run_mission_with_decision(supervisor, mission, decision)
        assert result["status"] == "complete", f"attendu complete, recu {result['status']}"
        print("TEST OK: decision=complete -> complete")


if __name__ == "__main__":
    tests = [
        test_audit_none_without_expected_to_needs_audit,
        test_audit_none_with_expected_to_needs_audit,
        test_audit_read_files_non_destructive_to_needs_audit,
        test_audit_destructive_with_validation_to_waiting,
        test_audit_forbidden_action_to_waiting,
        test_audit_requires_human_validation_true_non_destructive_to_needs_audit,
        test_execute_requires_human_validation_true_non_destructive_to_needs_audit,
        test_audit_complete_decision_not_overridden,
    ]
    failed = []
    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"TEST {t.__name__} FAILED: {e}")
            failed.append(t.__name__)
    if failed:
        print(f"\n{len(failed)} test(s) echoue(s): {failed}")
        sys.exit(1)
    print("\nTous les tests de mapping audit sont OK.")
