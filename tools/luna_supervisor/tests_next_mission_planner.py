"""Tests unitaires du planificateur de prochaine mission.

Ne consomme aucun appel IA ni aucune requête réseau (requests est mocké).
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from luna_supervisor.config import load_config
from luna_supervisor.next_mission_planner import NextMissionPlanner


def _make_planner(tmp_path: Path):
    config = load_config(project_path=str(tmp_path))
    config["AGENT_SHARED"] = str(tmp_path / "AGENT_SHARED")
    return NextMissionPlanner(config)


def _write_roadmap(agent_shared: Path):
    agent_shared.mkdir(parents=True, exist_ok=True)
    roadmap = agent_shared / "AUTONOMY_COMPLETE_ROADMAP.md"
    roadmap.write_text(
        "# AUTONOMY_COMPLETE_ROADMAP\n\n"
        "## Missions a faire dans l'ordre\n\n"
        "### 1. SAFE-AUDIT-001\n\n"
        "But : auditer le fichier README.md en lecture seule.\n\n"
        "Statut attendu : `needs_audit`.\n\n"
        "### 2. SAFE-REVIEW-002\n\n"
        "But : review du code du superviseur sans modification.\n\n"
        "Statut attendu : `needs_audit`.\n\n"
        "### 3. GUARDIAN-AUDIT-003\n\n"
        "But : audit non destructif de Guardian voix.\n\n"
        "Statut attendu : `needs_audit`.\n\n"
        "### 4. DANGER-DEPLOY-004\n\n"
        "But : deploy en production.\n\n"
        "Statut attendu : `waiting_human_approval`.\n\n"
        "### 5. DANGER-PUSH-005\n\n"
        "But : faire un push sur GitHub.\n\n"
        "Statut attendu : `waiting_human_approval`.\n\n",
        encoding="utf-8",
    )
    return roadmap


def test_load_candidates():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        planner = _make_planner(tmp_path)
        _write_roadmap(tmp_path / "AGENT_SHARED")

        candidates = planner._load_candidates()
        assert len(candidates) == 5, f"attendu 5 candidates, recu {len(candidates)}"
        assert candidates[0]["mission_id"] == "SAFE-AUDIT-001"
        print("TEST OK: load_candidates retourne 5 missions")


def test_assess_risk_safe():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        planner = _make_planner(tmp_path)

        assert planner._assess_risk({"mission_id": "X", "objective": "Lire README.md"}) == "safe"
        print("TEST OK: mission lecture -> safe")


def test_assess_risk_guarded():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        planner = _make_planner(tmp_path)

        risk = planner._assess_risk({"mission_id": "X", "objective": "Audit non destructif Guardian voix"})
        assert risk == "guarded", f"attendu guarded, recu {risk}"
        print("TEST OK: mission Guardian audit -> guarded")


def test_assess_risk_forbidden():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        planner = _make_planner(tmp_path)

        assert planner._assess_risk({"mission_id": "X", "objective": "Faire un push production"}) == "forbidden"
        assert planner._assess_risk({"mission_id": "X", "objective": "Installer l'APK debug"}) == "forbidden"
        print("TEST OK: missions push/APK -> forbidden")


def test_assess_risk_no_ai_marker():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        planner = _make_planner(tmp_path)

        risk = planner._assess_risk({"mission_id": "CODEX-REVIEW-X", "objective": "audit sans appel Kimi du code"})
        assert risk == "guarded", f"attendu guarded, recu {risk}"

        risk = planner._assess_risk({"mission_id": "Y", "objective": "review par Codex du superviseur"})
        assert risk == "guarded", f"attendu guarded, recu {risk}"
        print("TEST OK: missions sans IA/Codex -> guarded")


def test_plan_proposes_first_safe():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        planner = _make_planner(tmp_path)
        _write_roadmap(tmp_path / "AGENT_SHARED")

        plan = planner.plan(auto_next=False)
        assert plan["planner_status"] == "proposed"
        assert plan["next_mission_id"] == "SAFE-AUDIT-001"
        assert plan["risk_level"] == "safe"
        assert plan["auto_created"] is False
        print("TEST OK: plan propose SAFE-AUDIT-001 sans la créer")


def test_plan_creates_when_auto_next():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        planner = _make_planner(tmp_path)
        _write_roadmap(tmp_path / "AGENT_SHARED")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "queued", "mission_id": "SAFE-AUDIT-001"}

        with patch("luna_supervisor.next_mission_planner.requests.post", return_value=mock_response):
            plan = planner.plan(auto_next=True)

        assert plan["planner_status"] == "created"
        assert plan["auto_created"] is True
        assert plan["next_mission_id"] == "SAFE-AUDIT-001"
        print("TEST OK: plan crée SAFE-AUDIT-001 avec auto_next=true")


def test_plan_paused_budget():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        planner = _make_planner(tmp_path)
        _write_roadmap(tmp_path / "AGENT_SHARED")

        mock_budget = MagicMock()
        mock_budget.status.return_value = {
            "governor_state": "exhausted",
            "usage_ratio": 1.0,
            "total_today": 10,
            "max_total_per_day": 10,
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "queued", "mission_id": "SAFE-AUDIT-001"}

        with patch("luna_supervisor.next_mission_planner.BudgetGovernor", return_value=mock_budget):
            with patch("luna_supervisor.next_mission_planner.requests.post", return_value=mock_response):
                plan = planner.plan(auto_next=True)

        assert plan["planner_status"] == "paused_budget"
        assert plan["auto_created"] is False
        assert "budget" in plan["reason"].lower()
        print("TEST OK: plan s'arrete quand le budget est epuise")


def test_plan_skips_forbidden_to_safe():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        planner = _make_planner(tmp_path)
        _write_roadmap(tmp_path / "AGENT_SHARED")

        # On supprime la première mission safe pour forcer le planificateur
        # à sauter DANGER-DEPLOY-004 et DANGER-PUSH-005.
        (tmp_path / "AGENT_SHARED" / "AUTONOMY_COMPLETE_ROADMAP.md").write_text(
            "# AUTONOMY_COMPLETE_ROADMAP\n\n"
            "## Missions a faire dans l'ordre\n\n"
            "### 1. DANGER-DEPLOY-004\n\n"
            "But : deploy en production.\n\n"
            "### 2. DANGER-PUSH-005\n\n"
            "But : faire un push sur GitHub.\n\n"
            "### 3. SAFE-REVIEW-002\n\n"
            "But : review du code du superviseur sans modification.\n\n",
            encoding="utf-8",
        )

        plan = planner.plan(auto_next=False)
        assert plan["next_mission_id"] == "SAFE-REVIEW-002"
        assert plan["risk_level"] == "safe"
        print("TEST OK: plan saute les missions interdites")


def test_plan_stops_on_guarded_without_auto_next():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        planner = _make_planner(tmp_path)
        _write_roadmap(tmp_path / "AGENT_SHARED")

        # On supprime les missions safe pour ne garder que GUARDIAN-AUDIT-003
        (tmp_path / "AGENT_SHARED" / "AUTONOMY_COMPLETE_ROADMAP.md").write_text(
            "# AUTONOMY_COMPLETE_ROADMAP\n\n"
            "## Missions a faire dans l'ordre\n\n"
            "### 1. GUARDIAN-AUDIT-003\n\n"
            "But : audit non destructif de Guardian voix.\n\n",
            encoding="utf-8",
        )

        plan = planner.plan(auto_next=True)
        assert plan["planner_status"] == "guarded"
        assert plan["risk_level"] == "guarded"
        assert plan["auto_created"] is False
        print("TEST OK: mission Guardian reste guarded meme avec auto_next=true")


def test_write_report():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        planner = _make_planner(tmp_path)
        _write_roadmap(tmp_path / "AGENT_SHARED")

        plan = planner.plan(auto_next=False)
        path = planner.write_report(plan)
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "SAFE-AUDIT-001" in content
        print("TEST OK: rapport planificateur écrit")


if __name__ == "__main__":
    tests = [
        test_load_candidates,
        test_assess_risk_safe,
        test_assess_risk_guarded,
        test_assess_risk_forbidden,
        test_assess_risk_no_ai_marker,
        test_plan_proposes_first_safe,
        test_plan_creates_when_auto_next,
        test_plan_paused_budget,
        test_plan_skips_forbidden_to_safe,
        test_plan_stops_on_guarded_without_auto_next,
        test_write_report,
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
    print("\nTous les tests du planificateur sont OK.")
