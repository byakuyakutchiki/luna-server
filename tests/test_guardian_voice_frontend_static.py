from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = ROOT / "static" / "index.html"


def test_guardian_voice_paths_share_trigger_function():
    html = INDEX_HTML.read_text(encoding="utf-8")

    assert "function guardianHandleFinalVoiceText(text, source)" in html
    assert 'guardianHandleFinalVoiceText(text, "speech_recognition")' in html
    assert "sendGuardianTextToLunaVoice(text);" in html
    assert "guardianVoiceHasEmergencyKeyword" in html
    assert ".replace(/[’`]/g, \"'\")" in html
    assert "window.onGuardianSrFinal" not in html
    assert "window.onGuardianVoskFinal" not in html


def test_guardian_sr_logs_are_present():
    html = INDEX_HTML.read_text(encoding="utf-8")

    assert "[GUARDIAN_SR] keyword detected" in html
    assert "[GUARDIAN_SR] forwarding to sendGuardianTextToLunaVoice" in html
