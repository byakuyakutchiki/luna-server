"""Regression tests for read_files payload hygiene."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from luna_supervisor.action_executor import ActionExecutor
from luna_supervisor.config import load_config


def _executor(project: Path, shared: Path) -> ActionExecutor:
    config = load_config(project_path=str(project))
    config["PROJECT_PATH"] = str(project)
    config["RUNS_DIR"] = str(project / "runs")
    config["AGENT_SHARED_PATH"] = str(shared)
    config["MAX_CONTEXT_CHARACTERS"] = 100
    return ActionExecutor(config)


def test_read_files_skips_binary_content():
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as shared_tmp:
        project = Path(tmp)
        png = project / "screenshot.png"
        png.write_bytes(b"\x89PNG\r\n" + b"x" * 1000)
        result = _executor(project, Path(shared_tmp))._action_read_files({"files": ["screenshot.png"]}, "M", "T")
        info = result["files"]["screenshot.png"]
        assert info["type"] == "binary"
        assert "PNG" not in info["content"]
        assert info["size"] > 0
        print("TEST OK: read_files ne lit pas les binaires")


def test_read_files_resolves_agent_shared_alias():
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as shared_tmp:
        project = Path(tmp)
        shared = Path(shared_tmp)
        (shared / "REPORT.md").write_text("rapport ok", encoding="utf-8")
        result = _executor(project, shared)._action_read_files({"files": ["AGENT_SHARED/REPORT.md"]}, "M", "T")
        info = result["files"]["AGENT_SHARED/REPORT.md"]
        assert info["type"] == "text"
        assert info["content"] == "rapport ok"
        print("TEST OK: read_files résout AGENT_SHARED")


def test_read_files_reports_directory_entries():
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as shared_tmp:
        project = Path(tmp)
        (project / "core").mkdir()
        (project / "core" / "a.py").write_text("x", encoding="utf-8")
        result = _executor(project, Path(shared_tmp))._action_read_files({"files": ["core"]}, "M", "T")
        info = result["files"]["core"]
        assert info["type"] == "directory"
        assert "a.py" in info["entries"]
        print("TEST OK: read_files décrit les dossiers")


def test_read_files_honors_offset_and_max_chars():
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as shared_tmp:
        project = Path(tmp)
        (project / "large.txt").write_text("0123456789" * 20, encoding="utf-8")
        result = _executor(project, Path(shared_tmp))._action_read_files({
            "files": ["large.txt"],
            "read_options": {"offset": 10, "max_chars": 15},
        }, "M", "T")
        info = result["files"]["large.txt"]
        assert info["offset"] == 10
        assert info["max_chars"] == 15
        assert "012345678901234" in info["content"]
        assert info["truncated_before"] is True
        assert info["truncated_after"] is True
        print("TEST OK: read_files respecte offset/max_chars")


if __name__ == "__main__":
    test_read_files_skips_binary_content()
    test_read_files_resolves_agent_shared_alias()
    test_read_files_reports_directory_entries()
    test_read_files_honors_offset_and_max_chars()
    print("Tous les tests read_files hygiene sont OK")
