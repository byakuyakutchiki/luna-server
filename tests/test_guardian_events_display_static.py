from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARDIAN = ROOT / "static" / "guardian.html"
LUNA_WEB = ROOT / "luna_web.py"


def _guardian_route_slice():
    src = GUARDIAN.read_text(encoding="utf-8")
    return src[src.index("function cleanGuardianEventText"):src.index("// ── TIMELINE", src.index("function cleanGuardianEventText"))]


def test_guardian_event_history_sanitizes_hostile_transcript_noise():
    block = _guardian_route_slice()
    assert "replace(/\\[unk\\]/gi,'')" in block
    assert "replace(/^(🆘\\s*)+/,'')" in block
    assert "cleanGuardianEventText(e.description,e.event_type)" in block


def test_guardian_event_history_maps_link_has_visible_button_class():
    src = GUARDIAN.read_text(encoding="utf-8")
    assert ".ev-maps" in src
    assert "min-width:44px" in src
    assert "rel=\"noopener\"" in src
    assert "<span class=\"ev-text\">" in src


def test_location_unavailable_user_text_is_not_technical():
    src = LUNA_WEB.read_text(encoding="utf-8")
    assert "Position temporairement indisponible. Guardian reste actif." in src
    route = src[src.index("async def guardian_location_denied"):src.index("# ── Issue #32", src.index("async def guardian_location_denied"))]
    assert "HTTP local" not in route
    assert "permission refusee" not in route
