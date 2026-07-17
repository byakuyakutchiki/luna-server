"""Tests unitaires du smoke test d'appels agents.

Ne consomme aucun appel IA (les callers sont mockés).
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from luna_supervisor.agent_call_smoke import _check_fallback, _check_routing_decide_agent, run_smoke


def test_check_fallback():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        config = {
            "PROJECT_PATH": str(tmp_path),
            "BUDGET_FILE": str(tmp_path / "budget.json"),
            "KIMI_CLI": "/bin/true",
            "DEEPSEEK_API_KEY": "real-key",
            "OPENAI_API_KEY": "real-key",
        }
        result = _check_fallback(config)
        assert result["auditor"]["fallback_agent"] == "kimi"
        assert result["coordinator"]["fallback_agent"] == "kimi"
        print("TEST OK: fallback sur Kimi quand clés absentes")


def test_routing_decide_agent():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        config = {
            "PROJECT_PATH": str(tmp_path),
            "BUDGET_FILE": str(tmp_path / "budget.json"),
            "KIMI_CLI": "/bin/true",
            "DEEPSEEK_API_KEY": "real-key",
            "OPENAI_API_KEY": "real-key",
        }
        result = _check_routing_decide_agent(config)
        assert "operator" in result
        assert "auditor" in result
        assert "coordinator" in result
        print("TEST OK: routing retourne une décision pour chaque rôle")


def test_run_smoke_with_mocked_callers():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        config = {
            "PROJECT_PATH": str(tmp_path),
            "BUDGET_FILE": str(tmp_path / "budget.json"),
            "RUNNER_ID": "test-runner",
            "KIMI_CLI": "/bin/true",
            "DEEPSEEK_API_KEY": "real-key",
            "OPENAI_API_KEY": "real-key",
        }

        mock_kimi = MagicMock()
        mock_kimi.name = "kimi"
        mock_decision = MagicMock()
        mock_decision.decision = "complete"
        mock_kimi.call.return_value = mock_decision

        mock_deepseek = MagicMock()
        mock_deepseek.name = "deepseek"
        mock_deepseek.call.return_value = mock_decision

        mock_openai = MagicMock()
        mock_openai.name = "codex"
        mock_openai.call.return_value = mock_decision

        def _fake_get_caller(role, cfg):
            if role in ("operator", "reviewer"):
                return mock_kimi
            if role == "auditor":
                return mock_deepseek
            if role == "coordinator":
                return mock_openai
            return mock_kimi

        with patch("luna_supervisor.agent_call_smoke.get_caller", side_effect=_fake_get_caller):
            with patch("luna_supervisor.budget.BudgetGovernor._provider_enabled", return_value=True):
                result = run_smoke(str(tmp_path))

        assert result["overall_status"] == "ok"
        attempted = [c for c in result["calls"] if c["attempted"]]
        assert len(attempted) == 3
        for call in attempted:
            assert call["success"] is True
        print("TEST OK: smoke test avec callers mockés OK")


if __name__ == "__main__":
    tests = [
        test_check_fallback,
        test_routing_decide_agent,
        test_run_smoke_with_mocked_callers,
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
    print("\nTous les tests de smoke test sont OK.")
