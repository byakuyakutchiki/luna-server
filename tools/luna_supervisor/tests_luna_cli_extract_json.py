"""Regression test for the human luna CLI JSON extractor implementation."""

import subprocess
from pathlib import Path

PROJECT_PATH = Path(__file__).resolve().parents[2]
LUNA_BIN = PROJECT_PATH / "tools" / "luna_supervisor" / "bin" / "luna"


def test_extract_json_is_linear_style_and_not_nested_quadratic_loop():
    content = LUNA_BIN.read_text(encoding="utf-8")
    assert "for j in range(len(text), i, -1)" not in content
    assert "stack = []" in content
    assert "last = candidate" in content
    print("TEST OK: luna _extract_json utilise un scan lineaire")


def test_luna_status_returns_quickly():
    result = subprocess.run(
        [str(LUNA_BIN), "--status"],
        cwd=PROJECT_PATH,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "État de Luna Supervisor" in result.stdout
    print("TEST OK: luna --status retourne sans blocage")


if __name__ == "__main__":
    test_extract_json_is_linear_style_and_not_nested_quadratic_loop()
    test_luna_status_returns_quickly()
    print("Tous les tests luna CLI extract JSON sont OK")
