from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUARDIAN_HTML = ROOT / "static" / "guardian.html"


def test_guardian_voice_paths_share_guardian_sos_endpoint():
    html = GUARDIAN_HTML.read_text(encoding="utf-8")

    assert "window.lunaEmergencyVoiceDetected=function(text, confidence, context)" in html
    assert "_queueVoiceEmergency(text, confidence, context" in html
    assert "_flushPendingVoiceEmergency" in html
    assert "openVocalCountdown()" in html
    assert "_triggerSOSVocal" in html
    assert "authFetch('/api/guardian/sos/'+SID" in html
    assert "source:'vocal'" in html
    assert "context:_voiceContext||''" in html
    assert "transcript:_voiceTranscript||''" in html


def test_guardian_sr_diagnostic_logs_are_present():
    html = GUARDIAN_HTML.read_text(encoding="utf-8")

    assert "tag:'GUARDIAN_SR'" in html
    assert "_dbgSR('emergency_received')" in html
    assert "msg:'TRACE_'+step" in html
    assert "_traceGuardian('vosk_received'" in html
    assert "_traceGuardian('sos_request'" in html
    assert "_traceGuardian('sos_response'" in html
