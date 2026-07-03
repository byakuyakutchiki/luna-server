from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUARDIAN_HTML = ROOT / "static" / "guardian.html"


def test_guardian_apk_vosk_entrypoint_calls_trigger_directly():
    html = GUARDIAN_HTML.read_text(encoding="utf-8")

    assert "window.lunaEmergencyVoiceDetected=function(text, confidence)" in html
    assert "[GUARDIAN_SR] calling /trigger from sr_emergency" in html
    assert "authFetch('/trigger'" in html
    assert "source:'guardian_apk_vosk'" in html
    assert "last_words:text" in html
    assert "summary:text" in html
