from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "bin" / "luna-workday"


def test_luna_workday_uses_script_dir_luna_mission_fallback():
    src = SCRIPT.read_text(encoding="utf-8")
    assert 'SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"' in src
    assert 'LUNA_MISSION_BIN="${SCRIPT_DIR}/luna-mission"' in src
    assert 'command -v luna-mission' in src
    assert 'exec "${LUNA_MISSION_BIN}"' in src
