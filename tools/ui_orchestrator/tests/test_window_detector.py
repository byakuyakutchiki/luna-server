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


def test_real_windows_examples():
    """Vérifie que les vrais titres/processus observés par Codex sont classés correctement."""
    import yaml

    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "orchestrator_config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    detector = WindowDetector(config, "/tmp/ui_orchestrator_test")
    windows = [
        WindowInfo(title="Codex", process_name="ChatGPT"),
        WindowInfo(title="ChatGPT", process_name="ChatGPT"),
        WindowInfo(title="debrt (PRE_REPRISE_LOCAL_2026-07-08) [En fonction] - Oracle VirtualBox : 1", process_name="VirtualBoxVM"),
        WindowInfo(title="Oracle VirtualBox - Gestionnaire de machines", process_name="VirtualBox"),
        WindowInfo(title="powershell", process_name="WindowsTerminal"),
        WindowInfo(title="C:\\WINDOWS\\system32\\cmd.exe", process_name="WindowsTerminal"),
        WindowInfo(title="Automatisation des clics - Google Chrome", process_name="chrome"),
        WindowInfo(title="WhatsApp", process_name="WhatsApp.Root"),
    ]
    matched = detector.classify(windows)

    assert len(matched["codex"]) == 1, f"codex attendu 1, obtenu {len(matched['codex'])}"
    assert len(matched["chatgpt"]) == 1, f"chatgpt attendu 1, obtenu {len(matched['chatgpt'])}"
    assert len(matched["virtualbox"]) == 2, f"virtualbox attendu 2, obtenu {len(matched['virtualbox'])}"
    assert len(matched["terminal"]) == 2, f"terminal attendu 2, obtenu {len(matched['terminal'])}"
    assert len(matched["browser_reference"]) == 1, f"browser_reference attendu 1, obtenu {len(matched['browser_reference'])}"
    assert len(matched["unknown"]) == 1, f"unknown attendu 1, obtenu {len(matched['unknown'])}"
    print("TEST OK: vrais exemples Windows classés correctement")


if __name__ == "__main__":
    test_classify_codex()
    test_classify_virtualbox()
    test_classify_terminal()
    test_classify_unknown()
    test_simulated_probe()
    test_no_click_or_send()
    test_real_windows_examples()
    print("\nTous les tests window_detector sont OK.")

