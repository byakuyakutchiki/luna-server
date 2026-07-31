#!/usr/bin/env python3
"""Tests unitaires du détecteur de fenêtres."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from window_detector import WindowDetector, WindowInfo


def make_config():
    return {
        "orchestrator": {"simulate": True},
        "window_patterns": {
            "codex": {
                "title_regex": "(?i)(codex|vs code)",
                "process_regex": "(?i)(code)",
            },
            "virtualbox": {
                "title_regex": "(?i)(virtualbox)",
                "process_regex": "(?i)(virtualbox)",
            },
            "terminal": {
                "title_regex": "(?i)(terminal|bash)",
                "process_regex": "(?i)(bash|gnome-terminal)",
            },
        },
    }


def test_classify_codex():
    detector = WindowDetector(make_config(), "/tmp/ui_orchestrator_test")
    windows = [
        WindowInfo(title="Codex - Visual Studio Code", process_name="Code.exe"),
    ]
    matched = detector.classify(windows)
    assert len(matched["codex"]) == 1
    assert matched["codex"][0].matched_role == "codex"
    print("TEST OK: classification Codex")


def test_classify_virtualbox():
    detector = WindowDetector(make_config(), "/tmp/ui_orchestrator_test")
    windows = [
        WindowInfo(title="Oracle VM VirtualBox Manager", process_name="VirtualBox.exe"),
    ]
    matched = detector.classify(windows)
    assert len(matched["virtualbox"]) == 1
    print("TEST OK: classification VirtualBox")


def test_classify_terminal():
    detector = WindowDetector(make_config(), "/tmp/ui_orchestrator_test")
    windows = [
        WindowInfo(title="ludo@luna-vm: bash", process_name="gnome-terminal-server"),
    ]
    matched = detector.classify(windows)
    assert len(matched["terminal"]) == 1
    print("TEST OK: classification Terminal")


def test_classify_unknown():
    detector = WindowDetector(make_config(), "/tmp/ui_orchestrator_test")
    windows = [
        WindowInfo(title="Calculator", process_name="calc.exe"),
    ]
    matched = detector.classify(windows)
    assert len(matched["unknown"]) == 1
    print("TEST OK: classification Unknown")


def test_simulated_probe():
    detector = WindowDetector(make_config(), "/tmp/ui_orchestrator_test")
    windows = detector.probe_windows(simulate=True)
    assert len(windows) >= 4
    matched = detector.classify(windows)
    assert matched["codex"] or matched["virtualbox"] or matched["terminal"]
    print("TEST OK: probe simulé retourne des fenêtres classables")


def test_no_click_or_send():
    # Le module ne doit importer aucune lib de contrôle UI.
    import window_detector as wd

    assert "pyautogui" not in sys.modules
    assert "pywinauto" not in sys.modules
    print("TEST OK: aucun contrôle UI chargé")


if __name__ == "__main__":
    test_classify_codex()
    test_classify_virtualbox()
    test_classify_terminal()
    test_classify_unknown()
    test_simulated_probe()
    test_no_click_or_send()
    print("\nTous les tests window_detector sont OK.")
