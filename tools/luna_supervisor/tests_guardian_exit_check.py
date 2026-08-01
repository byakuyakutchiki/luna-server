"""Static regression tests for Guardian post-mission exit check."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CHECK = ROOT / "tools" / "luna_supervisor" / "guardian_exit_check.py"
EXECUTOR = ROOT / "tools" / "luna_supervisor" / "action_executor.py"


def test_guardian_exit_check_blocks_backend_real_alert_flags():
    source = CHECK.read_text(encoding="utf-8")

    assert "GUARDIAN_SMS_ENABLED" in source
    assert "GUARDIAN_CALL_ENABLED" in source
    assert "VOICE_EMERGENCY_DRY_RUN" in source
    assert 'env.get("GUARDIAN_SMS_ENABLED") == "false"' in source
    assert 'env.get("GUARDIAN_CALL_ENABLED") == "false"' in source
    assert 'env.get("VOICE_EMERGENCY_DRY_RUN") == "true"' in source


def test_guardian_exit_check_detects_runtime_loop_signals():
    source = CHECK.read_text(encoding="utf-8")

    assert "VOICE_SOS_NATIVE_POST status=200" in source
    assert "VOICE_EMERGENCY_DEBOUNCED" in source
    assert "dm_sent_to" in source
    assert "recent_guardian_loop_risk" in source
    assert 'counts["native_posts"] > 1' in source


def test_action_executor_exposes_guardian_exit_check_suite():
    source = EXECUTOR.read_text(encoding="utf-8")

    assert 'suite == "guardian_exit_check"' in source
    assert 'tools/luna_supervisor/guardian_exit_check.py' in source



def test_supervisor_auto_detects_guardian_apk_missions():
    source = (ROOT / "tools" / "luna_supervisor" / "supervisor.py").read_text(encoding="utf-8")

    assert "def _mission_requires_guardian_exit_check" in source
    assert '"guardian", "apk", "vosk", "sos"' in source
    assert "_run_guardian_exit_check" in source
    assert 'result["guardian_exit_check"] = guardian_exit' in source


def test_supervisor_downgrades_final_status_when_guardian_exit_check_fails():
    source = (ROOT / "tools" / "luna_supervisor" / "supervisor.py").read_text(encoding="utf-8")

    assert 'guardian_exit.get("status") != "pass"' in source
    assert 'result["status"] = "needs_audit"' in source
    assert 'result["requires_human_validation"] = True' in source
    assert "Guardian exit check failed" in source
