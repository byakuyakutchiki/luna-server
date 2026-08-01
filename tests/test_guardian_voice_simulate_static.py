from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "luna_web.py"


def test_voice_simulate_accepts_real_guardian_payload_aliases():
    src = SOURCE.read_text(encoding="utf-8")
    route = src[src.index("async def guardian_voice_simulate"): src.index("@app.get(\"/guardian-live/{token}\")")]
    assert 'body.get("transcript")' in route
    assert 'body.get("keyword")' in route
    assert 'body.get("last_words")' in route
    assert 'body.get("guardian_session_id")' in route


def test_voice_simulate_preview_contains_context_and_maps_link():
    src = SOURCE.read_text(encoding="utf-8")
    route = src[src.index("async def guardian_voice_simulate"): src.index("@app.get(\"/guardian-live/{token}\")")]
    assert "circumstances=phrase" in route
    assert "Circonstances : {phrase[:220]}" in route
    assert "https://maps.google.com/?q={lat},{lng}" in route
