"""Regression tests for Guardian evidence action wiring."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from luna_supervisor.action_executor import ActionExecutor
from luna_supervisor.agent_caller import AgentDecision
from luna_supervisor.config import load_config


def test_collect_guardian_evidence_handler_is_registered():
    with tempfile.TemporaryDirectory() as tmp:
        config = load_config(project_path=tmp)
        config["PROJECT_PATH"] = tmp
        executor = ActionExecutor(config)
        assert "collect_guardian_evidence" in executor.execute.__code__.co_consts or hasattr(executor, "_action_collect_guardian_evidence")
        assert hasattr(executor, "_action_collect_guardian_evidence")
        print("TEST OK: action collect_guardian_evidence enregistrée côté exécuteur")


def test_collect_guardian_evidence_is_allowed_for_agents():
    assert "collect_guardian_evidence" in AgentDecision.VALID_ACTION_TYPES
    print("TEST OK: action collect_guardian_evidence autorisée côté agents")


def test_operator_prompt_mentions_guardian_evidence():
    prompt = (Path(__file__).resolve().parent / "prompts" / "operator.txt").read_text(encoding="utf-8")
    assert "collect_guardian_evidence" in prompt
    assert "preuves Guardian" in prompt
    print("TEST OK: prompt opérateur mentionne collect_guardian_evidence")


if __name__ == "__main__":
    test_collect_guardian_evidence_handler_is_registered()
    test_collect_guardian_evidence_is_allowed_for_agents()
    test_operator_prompt_mentions_guardian_evidence()
    print("Tous les tests guardian evidence action sont OK")
