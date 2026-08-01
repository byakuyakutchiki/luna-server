from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUARDIAN_HTML = ROOT / "static" / "guardian.html"
MAIN_ACTIVITY = ROOT / "android-app" / "java" / "fr" / "yawatch" / "luna" / "MainActivity.java"
GUARDIAN_SERVICE = ROOT / "android-app" / "java" / "fr" / "yawatch" / "luna" / "GuardianService.java"
VOSK_SPOTTER = ROOT / "android-app" / "java" / "fr" / "yawatch" / "luna" / "VoskKeywordSpotter.java"


def test_guardian_webview_entrypoint_still_posts_to_guardian_sos():
    html = GUARDIAN_HTML.read_text(encoding="utf-8")

    assert "window.lunaEmergencyVoiceDetected=function(text, confidence, context)" in html
    assert "authFetch('/api/guardian/sos/'+SID" in html
    assert "source:'vocal'" in html
    assert "context:_voiceContext||''" in html
    assert "transcript:_voiceTranscript||''" in html


def test_guardian_apk_vosk_entrypoint_posts_natively_to_guardian_sos():
    main_activity = MAIN_ACTIVITY.read_text(encoding="utf-8")
    service = GUARDIAN_SERVICE.read_text(encoding="utf-8")
    vosk = VOSK_SPOTTER.read_text(encoding="utf-8")

    assert "window.lunaEmergencyVoiceDetected" in main_activity
    assert 'putString("guardian_session_id"' in main_activity
    assert "VOSK_POC_KEYWORD" in service
    assert "onEmergencyDetected(text, confidence)" in service
    assert "VOICE_EMERGENCY_DEBOUNCE_MS" in service
    assert "VOICE_EMERGENCY_DEBOUNCED" in service
    assert "triggerNativeVoiceSos(safe, confidence)" in service
    assert 'BACKEND_BASE_URL + "/api/guardian/sos/" + safeSid' in service
    assert "guardian_session_id" in service
    assert "VOICE_SOS_NATIVE_POST" in service
    assert "newRecognizer(recCls, modelCls, model)" in vosk
    assert "grammar_enabled" in vosk
