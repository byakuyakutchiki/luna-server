"""Tests unitaires du workflow multi-itérations du superviseur.

Ne consomme aucun appel IA ni aucune requête réseau (requests.post vers mission_store est mocké).
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

import requests

from luna_supervisor.agent_caller import AgentCallError, AgentDecision
from luna_supervisor.config import load_config
from luna_supervisor.routing import RoutingDecision
from luna_supervisor.supervisor import LunaAgentSupervisor
from luna_supervisor import mission_queue


def _make_supervisor(tmp_path: Path):
    config = load_config(project_path=str(tmp_path))
    config["AGENT_SHARED"] = str(tmp_path / "AGENT_SHARED")
    # Évite d'appeler le vrai N8NClient
    config["N8N_NEXT_JOB_URL"] = "http://localhost:9999/webhook/test-next"
    config["N8N_REPORT_URL"] = "http://localhost:9999/webhook/test-report"
    config["N8N_HEADER_NAME"] = "X-Test"
    config["N8N_HEADER_VALUE"] = "test"
    return LunaAgentSupervisor(config)


def test_build_mission_payload_accepts_iteration():
    """Vérifie que build_mission_payload propage l'itération > 0."""
    payload = mission_queue.build_mission_payload({
        "mission_id": "TEST-ITER",
        "objective": "test iteration",
        "role": "operator",
        "max_iterations": 3,
        "iteration": 2,
    })
    assert payload["iteration"] == 2, f"attendu 2, recu {payload['iteration']}"
    print("TEST OK: build_mission_payload accepte iteration=2")


def test_maybe_submit_next_iteration_ignores_terminal_status():
    """Si le statut n'est pas in_progress, aucune itération suivante ne doit être soumise."""
    with tempfile.TemporaryDirectory() as tmp:
        sup = _make_supervisor(Path(tmp))
        mission = {
            "mission_id": "TEST-001",
            "objective": "test",
            "role": "operator",
            "max_iterations": 3,
        }
        result = {"status": "needs_audit", "iteration": 1, "max_iterations": 3}
        assert sup._maybe_submit_next_iteration(mission, result) is None
        print("TEST OK: pas de soumission si statut terminal")


def test_maybe_submit_next_iteration_submits_when_in_progress():
    """Si le statut est in_progress, l'itération suivante doit être soumise au mission_store."""
    with tempfile.TemporaryDirectory() as tmp:
        sup = _make_supervisor(Path(tmp))
        mission = {
            "mission_id": "TEST-002",
            "task_id": "TEST-002",
            "objective": "test objective",
            "role": "operator",
            "max_iterations": 3,
            "priority": "normal",
            "auto_next": True,
        }
        result = {
            "status": "in_progress",
            "iteration": 1,
            "max_iterations": 3,
            "next_role": "reviewer",
        }
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"status": "queued", "mission_id": "TEST-002"}
        with patch.object(
            requests,
            "post",
            return_value=mock_response,
        ) as mock_post:
            response = sup._maybe_submit_next_iteration(mission, result)
            assert response is not None
            assert response["status"] == "queued"
            mock_post.assert_called_once()
            url = mock_post.call_args[0][0]
            payload = mock_post.call_args[1]["json"]
            assert url == "http://127.0.0.1:9876/create"
            assert payload["mission_id"] == "TEST-002"
            assert payload["current_role"] == "reviewer"
            assert payload["next_role"] == "reviewer"
            assert payload["iteration"] == 1
            assert payload["status"] == "queued"
            assert payload["objective"] == "test objective"
            ctx = json.loads(payload["mission_context_json"])
            assert ctx["role"] == "reviewer"
            assert ctx["source"] == "luna-supervisor-next-iteration"
            print("TEST OK: soumission itération suivante directe au mission_store avec role=reviewer iteration=1")


def test_maybe_submit_next_iteration_respects_max_iterations():
    """Si max_iterations est atteint, aucune nouvelle itération ne doit être soumise."""
    with tempfile.TemporaryDirectory() as tmp:
        sup = _make_supervisor(Path(tmp))
        mission = {
            "mission_id": "TEST-003",
            "objective": "test",
            "role": "operator",
            "max_iterations": 2,
        }
        result = {"status": "in_progress", "iteration": 2, "max_iterations": 2}
        assert sup._maybe_submit_next_iteration(mission, result) is None
        print("TEST OK: pas de soumission au-delà de max_iterations")


def _valid_decision():
    """Retourne une décision structurée valide pour les tests (audit non destructif)."""
    return AgentDecision({
        "summary": "décision de test",
        "decision": "audit",
        "requested_action": {"type": "read_files", "parameters": {"files": []}},
        "files_relevant": [],
        "expected_result": "needs_audit fallback",
        "requires_human_validation": False,
    }, agent_name="test")


def test_call_agent_with_fallback_coordinator_to_kimi():
    """Si coordinator échoue, le superviseur doit fallback sur operator/Kimi."""
    with tempfile.TemporaryDirectory() as tmp:
        sup = _make_supervisor(Path(tmp))
        routing = RoutingDecision(
            should_call=True,
            role="coordinator",
            reason="test",
            agent_name="codex",
            next_role="coordinator",
        )
        mission = {"mission_id": "TEST-FALLBACK-001", "objective": "test"}
        context = {}

        def _mock_caller(role, config):
            mock = MagicMock()
            mock.name = role
            mock.is_available.return_value = True
            if role == "coordinator":
                mock.call.side_effect = AgentCallError("JSON invalide de Codex")
            else:
                mock.call.return_value = _valid_decision()
            return mock

        with patch("luna_supervisor.supervisor.get_caller", side_effect=_mock_caller):
            decision, agent_name = sup._call_agent_with_fallback(mission, context, routing)

        assert agent_name == "operator"
        assert decision.decision == "audit"
        print("TEST OK: fallback coordinator -> operator/Kimi sur JSON invalide")


def test_process_mission_coordinator_invalid_fallback_produces_needs_audit():
    """Une mission dont le coordinator échoue doit finir en needs_audit avec rapport."""
    with tempfile.TemporaryDirectory() as tmp:
        sup = _make_supervisor(Path(tmp))
        mission = {
            "mission_id": "TEST-FALLBACK-002",
            "task_id": "TEST-FALLBACK-002",
            "objective": "test coordinator fallback",
            "role": "operator",
            "iteration": 2,
            "max_iterations": 3,
        }

        def _mock_caller(role, config):
            mock = MagicMock()
            mock.name = role
            mock.is_available.return_value = True
            if role == "coordinator":
                mock.call.side_effect = AgentCallError("JSON invalide de Codex")
            else:
                mock.call.return_value = _valid_decision()
            return mock

        routing = RoutingDecision(
            should_call=True,
            role="coordinator",
            reason="test",
            agent_name="codex",
            next_role="coordinator",
        )

        with patch("luna_supervisor.supervisor.get_caller", side_effect=_mock_caller):
            with patch("luna_supervisor.supervisor.decide_agent", return_value=routing):
                with patch.object(sup, "_write_agent_shared_report") as mock_report:
                    result = sup._process_mission(mission)

        assert result["status"] == "needs_audit"
        mock_report.assert_called_once()
        call_status = mock_report.call_args[0][1].get("status")
        assert call_status == "needs_audit"
        print("TEST OK: mission coordinator invalide -> needs_audit + rapport final")


if __name__ == "__main__":
    test_build_mission_payload_accepts_iteration()
    test_maybe_submit_next_iteration_ignores_terminal_status()
    test_maybe_submit_next_iteration_submits_when_in_progress()
    test_maybe_submit_next_iteration_respects_max_iterations()
    test_call_agent_with_fallback_coordinator_to_kimi()
    test_process_mission_coordinator_invalid_fallback_produces_needs_audit()
    print("\nTous les tests workflow superviseur sont OK")
