"""Guardian post-mission runtime exit check.

Read-only guardrail for Luna Supervisor/Kimi/Codex missions touching Guardian/APK.
It verifies that the phone/backend are not left in a loop or in a real-alert
configuration after a mission.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE = os.getenv("ANDROID_PACKAGE", "fr.yawatch.luna")


def _run(cmd: List[str], timeout: int = 12, cwd: Path | None = None) -> Tuple[int, str, str]:
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd or PROJECT_ROOT),
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except FileNotFoundError as e:
        return 127, "", str(e)
    except subprocess.TimeoutExpired as e:
        return 124, e.stdout or "", e.stderr or "timeout"


def _adb(args: List[str], timeout: int = 12) -> Tuple[int, str, str]:
    return _run(["adb", *args], timeout=timeout)


def _backend_env() -> Dict[str, Any]:
    rc, out, _ = _run(["bash", "-lc", "pgrep -f 'python3 -m uvicorn luna_web:app' | head -1"], timeout=5)
    pid = out.strip() if rc == 0 else ""
    result: Dict[str, Any] = {"pid": pid, "env": {}, "safe": False}
    if not pid:
        result["reason"] = "uvicorn_not_running"
        return result
    rc, env_out, err = _run(["bash", "-lc", f"tr '\\0' '\\n' </proc/{pid}/environ"], timeout=5)
    if rc != 0:
        result["reason"] = err or "environ_unreadable"
        return result
    wanted = {
        "GUARDIAN_SMS_ENABLED",
        "GUARDIAN_CALL_ENABLED",
        "VOICE_EMERGENCY_DRY_RUN",
        "VOICE_EMERGENCY_ENABLED",
    }
    env = {}
    for line in env_out.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in wanted:
            env[key] = value
    result["env"] = env
    result["safe"] = (
        env.get("GUARDIAN_SMS_ENABLED") == "false"
        and env.get("GUARDIAN_CALL_ENABLED") == "false"
        and env.get("VOICE_EMERGENCY_DRY_RUN") == "true"
    )
    return result


def _phone_state() -> Dict[str, Any]:
    rc, devices, err = _adb(["devices", "-l"], timeout=8)
    state: Dict[str, Any] = {"adb_rc": rc, "adb_devices": devices, "adb_error": err}
    connected = [line for line in devices.splitlines()[1:] if " device " in f" {line} "]
    state["adb_available"] = rc == 0 and bool(connected)
    if not state["adb_available"]:
        state["safe"] = False
        state["reason"] = "adb_unavailable"
        return state

    _, pid, _ = _adb(["shell", "pidof", PACKAGE], timeout=6)
    state["app_pid"] = pid.strip()

    _, services, _ = _adb(["shell", "dumpsys", "activity", "services", PACKAGE], timeout=8)
    state["guardian_service_present"] = "GuardianService" in services
    state["guardian_foreground"] = "isForeground=true" in services
    state["notification_silent"] = "sound=null" in services and "vibrate=null" in services
    state["safe"] = True
    return state


def _recent_loop_signals() -> Dict[str, Any]:
    _, logs, _ = _adb(["logcat", "-d", "-t", "700"], timeout=12)
    patterns = {
        "native_posts": r"VOICE_SOS_NATIVE_POST status=200",
        "debounced": r"VOICE_EMERGENCY_DEBOUNCED",
        "vosk_keywords": r"VOSK_POC_KEYWORD",
        "rate_limited": r"GUARDIAN_SOS_RATE_LIMIT|rate_limited",
        "internal_dm_success": r"dm_sent_to\":\s*[1-9]|Guardian DM alerts sent",
        "sms_success": r"sms_sent_to\":\s*[1-9]",
        "call_success": r"calls_placed\":\s*[1-9]",
    }
    counts = {name: len(re.findall(pattern, logs)) for name, pattern in patterns.items()}
    # A post-mission check should not see repeated successful posts in the recent log window.
    loop_risk = counts["native_posts"] > 1 or counts["internal_dm_success"] > 1
    return {"counts": counts, "loop_risk": loop_risk}


def run_check() -> Dict[str, Any]:
    backend = _backend_env()
    phone = _phone_state()
    loops = _recent_loop_signals() if phone.get("adb_available") else {"counts": {}, "loop_risk": True}
    failures = []
    warnings = []

    if not backend.get("safe"):
        failures.append("backend_not_safe_flags")
    if not phone.get("adb_available"):
        failures.append("adb_unavailable")
    if loops.get("loop_risk"):
        failures.append("recent_guardian_loop_risk")
    if phone.get("guardian_service_present") and not phone.get("notification_silent"):
        warnings.append("guardian_notification_not_proven_silent")

    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "warnings": warnings,
        "backend": backend,
        "phone": phone,
        "recent_loop_signals": loops,
    }


def main() -> int:
    result = run_check()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
