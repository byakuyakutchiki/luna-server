"""Regression tests for Android package guardrails in Luna Supervisor."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from luna_supervisor.action_executor import ActionExecutor, ExecutorError
from luna_supervisor.agent_caller import KimiCaller
from luna_supervisor.config import load_config
from luna_supervisor.context_builder import ContextBuilder


def _config(tmp_path: Path):
    config = load_config(project_path=str(tmp_path))
    config["PROJECT_PATH"] = str(tmp_path)
    config["RUNS_DIR"] = str(tmp_path / "runs")
    config["ANDROID_PACKAGE"] = "fr.yawatch.luna"
    config["ANDROID_MAIN_ACTIVITY"] = "fr.yawatch.luna.MainActivity"
    return config


def test_collect_adb_refuses_wrong_android_package():
    with tempfile.TemporaryDirectory() as tmp:
        executor = ActionExecutor(_config(Path(tmp)))
        try:
            executor._validate_collect_adb_params({
                "steps": ["adb shell am start -n fr.luna.guardian/.MainActivity"]
            })
        except ExecutorError as e:
            assert "fr.luna.guardian" in str(e)
            assert "fr.yawatch.luna" in str(e)
        else:
            raise AssertionError("collect_adb must reject hallucinated package fr.luna.guardian")


def test_collect_adb_accepts_configured_android_package():
    with tempfile.TemporaryDirectory() as tmp:
        executor = ActionExecutor(_config(Path(tmp)))
        executor._validate_collect_adb_params({
            "steps": ["adb shell am start -n fr.yawatch.luna/fr.yawatch.luna.MainActivity"]
        })


def test_context_builder_exposes_android_package_guardrail():
    with tempfile.TemporaryDirectory() as tmp:
        config = _config(Path(tmp))
        builder = ContextBuilder(config)
        with patch("luna_supervisor.context_builder.resolve_android_device", return_value=("USB1", "USB1 device")):
            with patch("luna_supervisor.context_builder.ADBActions") as adb_cls:
                adb = adb_cls.return_value
                adb.getprop.side_effect = lambda prop: {"ro.product.model": "TEST", "ro.build.version.release": "16"}[prop]
                adb.get_state.return_value = "device"
                context = builder._adb_context()
        assert context["android_package"] == "fr.yawatch.luna"
        assert context["android_main_activity"] == "fr.yawatch.luna.MainActivity"
        assert "Ne jamais inventer" in context["package_guardrail"]


def test_agent_prompt_mentions_android_package_context():
    caller = KimiCaller({"KIMI_CLI": "/bin/false"})
    prompt = caller._build_prompt("SYSTEM", {"mission_id": "M", "objective": "O"}, "{}")
    assert "adb.android_package" in prompt
    assert "sans inventer de package" in prompt


if __name__ == "__main__":
    test_collect_adb_refuses_wrong_android_package()
    test_collect_adb_accepts_configured_android_package()
    test_context_builder_exposes_android_package_guardrail()
    test_agent_prompt_mentions_android_package_context()
    print("Tous les tests package guardrails sont OK")
