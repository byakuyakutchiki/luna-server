from pathlib import Path


def test_guardian_voice_status_uses_existing_guardian_engine():
    source = Path("luna_web.py").read_text(encoding="utf-8")
    start = source.index('async def guardian_voice_status')
    end = source.index('@app.post("/api/guardian/voice/simulate")', start)
    block = source[start:end]

    assert '_get_guardian_engine' not in block
    assert '_get_guardian()' in block
    assert 'get_active_sessions(tid)' in block
    assert 'is_active' in block
