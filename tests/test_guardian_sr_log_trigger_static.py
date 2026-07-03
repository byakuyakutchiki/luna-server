from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LUNA_WEB = ROOT / "luna_web.py"


def test_guardian_sr_client_log_triggers_emergency_chain():
    source = LUNA_WEB.read_text(encoding="utf-8")

    assert "sr_emergency" in source
    assert "_extract_guardian_sr_emergency_text" in source
    assert "_trigger_from_guardian_sr_log" in source
    assert "[GUARDIAN_SR] calling /trigger from sr_emergency" in source
    assert "GUARDIAN /trigger received source=%s" in source
    assert "_trigger_voice_emergency(" in source
