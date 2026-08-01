"""Regression tests for actionable Supervisor reports."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from luna_supervisor.supervisor import LunaAgentSupervisor
from luna_supervisor.config import load_config


def test_action_result_summary_lists_read_files():
    with tempfile.TemporaryDirectory() as tmp:
        config = load_config(project_path=tmp)
        config["PROJECT_PATH"] = tmp
        supervisor = LunaAgentSupervisor(config)
        lines = []
        supervisor._append_action_result_summary(lines, {
            "status": "success",
            "files": {
                "static/guardian.html": {"type": "text", "size": 123},
                "runs/a/screenshot.png": {"type": "binary", "size": 456},
                "missing.py": {"error": "introuvable"},
            },
        })
        text = "\n".join(lines)
        assert "## Synthèse action exécutée" in text
        assert "static/guardian.html: type=text, size=123" in text
        assert "runs/a/screenshot.png: type=binary, size=456" in text
        assert "missing.py: erreur introuvable" in text
        print("TEST OK: rapport synthétise les fichiers lus")


if __name__ == "__main__":
    test_action_result_summary_lists_read_files()
    print("Tous les tests rapport superviseur sont OK")
