from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LUNA_WEB = ROOT / "luna_web.py"
GUARDIAN_SERVICE = ROOT / "android-app" / "java" / "fr" / "yawatch" / "luna" / "GuardianService.java"


def test_backend_guardian_sos_route_is_real_emergency_chain():
    source = LUNA_WEB.read_text(encoding="utf-8")

    assert '@app.post("/api/guardian/sos/{session_id}")' in source
    assert "guardian_sos" in source
    assert '"event_type": "sos_triggered"' in source or "sos_triggered" in source
    assert "GUARDIAN_SMS_ENABLED" in source
    assert "GUARDIAN_CALL_ENABLED" in source
    assert "sms_blocked" in source
    assert "calls_placed" in source


def test_guardian_service_native_vosk_route_does_not_depend_on_trigger_endpoint():
    service = GUARDIAN_SERVICE.read_text(encoding="utf-8")

    assert "VOSK_POC_KEYWORD" in service
    assert "VOICE_EMERGENCY_DETECTED nativeWillPost=" in service
    assert "hasSavedGuardianSession()" in service
    assert "triggerNativeVoiceSos" in service
    assert "VOICE_SOS_NATIVE_POST" in service
    assert "/api/guardian/sos/" in service
    assert "VOICE_EMERGENCY_DEBOUNCED" in service
