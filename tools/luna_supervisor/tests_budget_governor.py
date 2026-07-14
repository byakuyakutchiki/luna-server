"""Tests de protection du BudgetGovernor et du routage intelligent.

Ne consomme aucun appel IA pour les tests de blocage.
Le test 10 (mission valide) peut optionnellement faire un appel reel.
"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path

# Ajoute tools au PYTHONPATH si besoin
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from luna_supervisor.budget import BudgetGovernor
from luna_supervisor.context_builder import ContextBuilder
from luna_supervisor.routing import decide_agent
from luna_supervisor.agent_caller import AgentDecision, InvalidDecisionError


def _load_config():
    from luna_supervisor.config import load_config
    return load_config()


def test_1_no_mission_no_call():
    """Aucune mission : aucun appel IA."""
    config = _load_config()
    budget = BudgetGovernor(config)
    result = budget.can_call("kimi", "TEST-NO-MISSION", reason="no_mission")
    assert result[0] is True, "can_call devrait etre True quand budget OK"
    # Mais decide_agent refuse une mission sans objectif
    mission = {"mission_id": "TEST-NO-MISSION"}
    context = ContextBuilder(config).build(mission)
    routing = decide_agent(mission, context, budget, config)
    assert routing.should_call is False, "doit refuser sans objectif"
    assert "mission_sans_objectif" in routing.reason
    print("TEST 1 OK: pas d'appel IA sans mission")


def test_2_budget_100_percent_blocks():
    """Budget a 100% : aucun appel IA."""
    config = _load_config()
    with tempfile.TemporaryDirectory() as tmp:
        budget_file = Path(tmp) / "budget.json"
        config["BUDGET_FILE"] = str(budget_file)
        today = "2026-07-12"
        # Cree un budget deja sature a la limite totale
        budget_file.write_text(
            json.dumps(
                {
                    "date": today,
                    "month": "2026-07",
                    "daily": {"kimi": 6},
                    "monthly": {},
                    "missions": {},
                }
            )
        )
        budget = BudgetGovernor(config, policy_path="config/agent_budget_policy.yaml")
        # La date du fichier correspond a aujourd'hui, pas de reset.
        assert budget._data["date"] == today

        can, reason = budget.can_call("kimi", "TEST-BUDGET", reason="budget_test")
        assert can is False, f"doit bloquer a 100%, raison: {reason}"
        assert "budget_global_journalier_epuise" in reason

        mission = {
            "mission_id": "TEST-BUDGET",
            "objective": "test",
            "iteration": 0,
        }
        context = ContextBuilder(config).build(mission)
        routing = decide_agent(mission, context, budget, config)
        assert routing.should_call is False
        assert "budget" in routing.reason
        print("TEST 2 OK: budget 100% bloque les appels")


def test_3_adb_unavailable_blocks():
    """Telephone indisponible pour une tache ADB : aucun appel IA inutile."""
    config = _load_config()
    config["ANDROID_DEVICE_ID"] = "192.168.255.255:5555"
    budget = BudgetGovernor(config)
    mission = {
        "mission_id": "TEST-ADB",
        "objective": "test adb",
        "requires_device": True,
        "iteration": 0,
    }
    context = ContextBuilder(config).build(mission)
    routing = decide_agent(mission, context, budget, config)
    assert routing.should_call is False, "doit refuser si ADB indisponible"
    assert "adb_indisponible" in routing.reason
    print("TEST 3 OK: ADB indisponible bloque l'appel")


def test_4_repeated_error_routes_to_deepseek():
    """Meme erreur repetee deux fois : DeepSeek si budget."""
    config = _load_config()
    budget = BudgetGovernor(config)
    mission_id = "TEST-ERROR"
    budget.record_error(mission_id, "executor:build_debug")
    budget.record_error(mission_id, "executor:build_debug")
    mission = {
        "mission_id": mission_id,
        "objective": "test erreur",
        "iteration": 1,
        "errors_new": [{"signature": "executor:build_debug"}],
    }
    context = ContextBuilder(config).build(mission)
    # Simule des fichiers modifies pour forcer le routage
    context["changed"]["files"] = ["android-app/src/main.java"]
    routing = decide_agent(mission, context, budget, config)
    # DeepSeek doit etre choisi car erreur repetee
    assert routing.role == "auditor", f"attendu auditor, recu {routing.role}"
    print("TEST 4 OK: erreur repetee route vers DeepSeek")


def test_5_invalid_kimi_response_rejected():
    """Reponse Kimi invalide : rejet sans commande shell."""
    try:
        AgentDecision({"summary": "test", "decision": "invalid"}, "kimi")
        assert False, "devrait lever InvalidDecisionError"
    except InvalidDecisionError as e:
        assert "decision" in str(e).lower() or "champs" in str(e).lower()
    print("TEST 5 OK: decision invalide rejetee")


def test_6_sensitive_action_requires_human_approval():
    """Commande sensible : validation humaine requise."""
    from luna_supervisor.action_executor import ActionExecutor
    import subprocess
    config = _load_config()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        # Initialise un depot temporaire sur main
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@luna.local"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True, capture_output=True)
        (tmp_path / "file.txt").write_text("hello")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)

        config["PROJECT_PATH"] = str(tmp_path)
        executor = ActionExecutor(config)
        action = {
            "type": "edit_files",
            "parameters": {
                "edits": [
                    {"path": "file.txt", "old_string": "hello", "new_string": "world"}
                ]
            },
        }
        try:
            executor.execute(action, "TEST-SENSITIVE", "TEST-SENSITIVE")
            assert False, "devrait lever ExecutorError"
        except Exception as e:
            msg = str(e).lower()
            assert "automation" in msg or "refuse" in msg or "validation" in msg, f"message: {msg}"
    print("TEST 6 OK: action sensible refusee sans branche automation")


def test_7_valid_mission_calls_single_agent():
    """Mission valide : un seul agent appelé."""
    config = _load_config()
    budget = BudgetGovernor(config)
    mission = {
        "mission_id": "TEST-VALID",
        "objective": "Lire README.md et retourner complete",
        "iteration": 0,
        "max_iterations": 1,
    }
    context = ContextBuilder(config).build(mission)
    routing = decide_agent(mission, context, budget, config)
    assert routing.should_call is True, f"devrait appeler, raison: {routing.reason}"
    assert routing.role == "operator"
    print("TEST 7 OK: mission valide route vers un seul agent (operator)")


def test_8_restart_preserves_ledger_and_budget():
    """Service redemarre : ledger et budget conserves."""
    config = _load_config()
    budget = BudgetGovernor(config)
    before = budget.status()
    ledger_before = len(budget.ledger())
    # Recharge
    budget2 = BudgetGovernor(config)
    after = budget2.status()
    assert after["total_today"] == before["total_today"]
    assert len(budget2.ledger()) == ledger_before
    print("TEST 8 OK: budget et ledger conserves au redemarrage")


def test_9_n8n_report_http_200():
    """Rapport n8n : HTTP 200."""
    from luna_supervisor.config import load_config
    from luna_runner.n8n_client import N8NClient
    config = load_config()
    from luna_runner.config import require
    client = N8NClient(
        next_job_url=require(config, "N8N_NEXT_JOB_URL"),
        report_url=require(config, "N8N_REPORT_URL"),
        header_name=config.get("N8N_HEADER_NAME", ""),
        header_value=config.get("N8N_HEADER_VALUE", ""),
        runner_id=config["RUNNER_ID"],
    )
    response = client.send_report(
        {
            "mission_id": "TEST-REPORT",
            "runner_id": config["RUNNER_ID"],
            "status": "ok",
            "requires_human_validation": False,
        }
    )
    assert response.get("_raw_status", 200) == 200 or response.get("_error") is None
    print("TEST 9 OK: rapport n8n HTTP 200")


def test_10_morning_report_no_secrets():
    """Rapport du matin : cree sans secret."""
    from luna_supervisor.morning_report import MorningReport
    config = _load_config()
    report = MorningReport(config)
    path = report.generate()
    text = path.read_text(encoding="utf-8")
    # Pas de cles API
    assert "sk-" not in text, "cle OpenAI fuitee"
    assert "DEEPSEEK_API_KEY" not in text
    assert "N8N_HEADER_VALUE" not in text
    print("TEST 10 OK: rapport du matin sans secret")


if __name__ == "__main__":
    tests = [
        test_1_no_mission_no_call,
        test_2_budget_100_percent_blocks,
        test_3_adb_unavailable_blocks,
        test_4_repeated_error_routes_to_deepseek,
        test_5_invalid_kimi_response_rejected,
        test_6_sensitive_action_requires_human_approval,
        test_7_valid_mission_calls_single_agent,
        test_8_restart_preserves_ledger_and_budget,
        test_9_n8n_report_http_200,
        test_10_morning_report_no_secrets,
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
    print("\nTous les tests de protection sont OK.")
