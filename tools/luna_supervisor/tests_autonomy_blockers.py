"""Tests des corrections des blocages autonomie (SUPERVISOR-AUTONOMY-BLOCKERS-FIX-001).

Couvre :
- Fallback ADB USB quand le device configuré est indisponible.
- Routage workday vers Kimi/operator (pas de coordinator Codex).
- Désactivation de la planification automatique par luna-workday.
"""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from luna_supervisor import adb_utils, routing
from luna_supervisor.routing import _select_role


class FakeBudget:
    """Budget governor factice qui autorise tous les appels."""

    def can_call(self, agent: str, mission_id: str, reason: str = "") -> tuple:
        return True, ""

    def same_error_count(self, mission_id: str, signature: str) -> int:
        return 0


def _budget() -> FakeBudget:
    return FakeBudget()


def test_parse_adb_devices_with_usb_and_wifi():
    output = (
        "List of devices attached\n"
        "192.168.1.62:5555      device product:DummyWiFi model:WiFiPhone device:wifi\n"
        "A6KXVB4912001918       device usb:1-1 product:LLY-NX1EEA model:LLY_NX1 device:HNLLY-M1\n"
        "emulator-5554          offline\n"
    )
    devices = adb_utils.parse_adb_devices(output)
    assert len(devices) == 2, f"Attendu 2 devices, obtenu {len(devices)}"
    assert devices[0]["id"] == "192.168.1.62:5555"
    assert devices[0]["usb"] == "False"
    assert devices[1]["id"] == "A6KXVB4912001918"
    assert devices[1]["usb"] == "True"
    print("TEST OK: parse adb devices distingue USB et wifi")


def test_resolve_android_device_keeps_configured_if_available():
    config = {"ANDROID_DEVICE_ID": "A6KXVB4912001918"}
    output = (
        "List of devices attached\n"
        "A6KXVB4912001918       device usb:1-1 product:LLY-NX1EEA model:LLY_NX1 device:HNLLY-M1\n"
    )
    with patch.object(adb_utils, "list_adb_devices", return_value=output):
        resolved, _ = adb_utils.resolve_android_device(config)
    assert resolved == "A6KXVB4912001918"
    assert config["ANDROID_DEVICE_ID"] == "A6KXVB4912001918"
    print("TEST OK: resolve garde le device configuré s'il est disponible")


def test_resolve_android_device_fallback_usb():
    config = {"ANDROID_DEVICE_ID": "192.168.1.62:5555"}
    output = (
        "List of devices attached\n"
        "A6KXVB4912001918       device usb:1-1 product:LLY-NX1EEA model:LLY_NX1 device:HNLLY-M1\n"
    )
    with patch.object(adb_utils, "list_adb_devices", return_value=output):
        resolved, _ = adb_utils.resolve_android_device(config)
    assert resolved == "A6KXVB4912001918"
    assert config["ANDROID_DEVICE_ID"] == "A6KXVB4912001918"
    print("TEST OK: fallback USB quand le device configuré est indisponible")


def test_resolve_android_device_no_device():
    config = {"ANDROID_DEVICE_ID": ""}
    with patch.object(adb_utils, "list_adb_devices", return_value="List of devices attached\n"):
        resolved, _ = adb_utils.resolve_android_device(config)
    assert resolved == ""
    print("TEST OK: resolve retourne vide si aucun device disponible")


def test_select_role_workday_last_iteration_uses_operator_not_coordinator():
    mission = {"mission_id": "WORKDAY-TEST-001", "iteration": 2, "max_iterations": 3}
    context = {"changed": {"files": [], "new_errors_since_last": []}}
    role = _select_role(mission, context, _budget())
    assert role == "operator", f"Attendu operator pour workday dernière itération, obtenu {role}"
    print("TEST OK: workday dernière itération -> operator (pas coordinator)")


def test_select_role_non_workday_last_iteration_uses_coordinator():
    mission = {"mission_id": "SUPERVISOR-TEST-001", "iteration": 2, "max_iterations": 3}
    context = {"changed": {"files": [], "new_errors_since_last": []}}
    role = _select_role(mission, context, _budget())
    assert role == "coordinator", f"Attendu coordinator pour non-workday dernière itération, obtenu {role}"
    print("TEST OK: non-workday dernière itération -> coordinator")


def test_select_role_workday_first_iteration_uses_operator():
    mission = {"mission_id": "WORKDAY-TEST-002", "iteration": 0, "max_iterations": 3}
    context = {"changed": {"files": [], "new_errors_since_last": []}}
    role = _select_role(mission, context, _budget())
    assert role == "operator"
    print("TEST OK: workday première itération -> operator")


def test_luna_workday_no_auto_next_in_command():
    """Vérifie que le script luna-workday ne passe plus --auto-next par défaut."""
    script_path = Path.home() / ".local" / "bin" / "luna-workday"
    content = script_path.read_text(encoding="utf-8")
    assert "--auto-next" not in content, "luna-workday ne doit plus contenir --auto-next par défaut"
    print("TEST OK: luna-workday ne force pas --auto-next")


if __name__ == "__main__":
    test_parse_adb_devices_with_usb_and_wifi()
    test_resolve_android_device_keeps_configured_if_available()
    test_resolve_android_device_fallback_usb()
    test_resolve_android_device_no_device()
    test_select_role_workday_last_iteration_uses_operator_not_coordinator()
    test_select_role_non_workday_last_iteration_uses_coordinator()
    test_select_role_workday_first_iteration_uses_operator()
    test_luna_workday_no_auto_next_in_command()
    print("\nTous les tests des blocages autonomie sont OK")
