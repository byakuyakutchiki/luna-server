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



def test_backend_blocks_duplicate_vocal_sos_before_triggering_alert_actions():
    source = LUNA_WEB.read_text(encoding="utf-8")

    assert "def _guardian_source_rate_limit" in source
    assert "guardian:sos_source_lock" in source
    assert "[GUARDIAN_SOS_RATE_LIMIT]" in source
    assert "rate_limited" in source

    rate_limit_pos = source.index('if sos_source == "vocal" and not _guardian_source_rate_limit')
    trigger_pos = source.index("event = engine.trigger_sos", rate_limit_pos)
    sms_pos = source.index("send_guardian_alerts", trigger_pos)
    call_pos = source.index("_call_on = os.getenv", trigger_pos)

    assert rate_limit_pos < trigger_pos < sms_pos
    assert rate_limit_pos < trigger_pos < call_pos


def test_backend_guardian_sos_uses_last_known_geolocation_when_session_has_no_position():
    source = LUNA_WEB.read_text(encoding="utf-8")

    assert "def _guardian_get_last_known_position" in source
    assert "luna:{tid}:geolocation" in source
    assert "GeoPoint(" in source
    assert "pos = _guardian_get_last_known_position(tid)" in source
    assert "Guardian SOS using last known geolocation" in source

    fallback_pos = source.index("pos = _guardian_get_last_known_position(tid)")
    dm_pos = source.index("send_guardian_dm_alerts", fallback_pos)
    sms_pos = source.index("build_sms_alert_v1", fallback_pos)
    call_pos = source.index("_call_on = os.getenv", fallback_pos)

    assert fallback_pos < dm_pos
    assert fallback_pos < sms_pos
    assert fallback_pos < call_pos
