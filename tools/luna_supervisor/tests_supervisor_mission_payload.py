"""Regression tests for mission payload safety context."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from luna_supervisor.mission_queue import build_mission_payload


def test_mission_payload_budget_limits_follow_policy():
    payload = build_mission_payload({
        "mission_id": "TEST-BUDGET-POLICY",
        "objective": "Verifier le contexte budget superviseur",
        "role": "operator",
        "max_iterations": 2,
    })
    context = json.loads(payload["mission_context_json"])
    limits = context["budget_limits"]
    assert limits["kimi_per_day"] == 45
    assert limits["total_per_day"] == 55
    assert limits["codex_per_day"] == 1


if __name__ == "__main__":
    test_mission_payload_budget_limits_follow_policy()
    print("Tous les tests mission payload sont OK")
