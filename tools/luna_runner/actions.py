"""Actions prédéfinies et contrôlées du runner.

Aucune commande shell arbitraire n'est autorisée. Chaque action est construite
par une fonction Python avec validation stricte des arguments.
"""

import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ActionError(Exception):
    pass


class ADBActions:
    """Encapsule toutes les commandes ADB autorisées."""

    def __init__(self, device_id: str, timeout: int = 60):
        self.device_id = device_id
        self.timeout = timeout
        self.adb = shutil.which("adb")
        if not self.adb:
            raise ActionError("adb introuvable dans le PATH")

    def _run(
        self,
        args: List[str],
        capture_output: bool = True,
        timeout: Optional[int] = None,
    ) -> Tuple[int, str, str]:
        cmd = [self.adb, "-s", self.device_id] + args
        try:
            proc = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                timeout=timeout or self.timeout,
            )
            return proc.returncode, proc.stdout or "", proc.stderr or ""
        except subprocess.TimeoutExpired:
            raise ActionError(f"Timeout adb: {' '.join(cmd)}")
        except FileNotFoundError:
            raise ActionError("adb non trouve")

    def devices(self) -> str:
        rc, out, err = self._run(["devices", "-l"])
        if rc != 0:
            raise ActionError(f"adb devices failed: {err}")
        return out

    def get_state(self) -> str:
        rc, out, err = self._run(["get-state"])
        if rc != 0:
            raise ActionError(f"adb get-state failed: {err}")
        return out.strip()

    def shell(self, command: str) -> str:
        rc, out, err = self._run(["shell", command])
        if rc != 0:
            raise ActionError(f"adb shell failed: {err}")
        return out

    def getprop(self, prop: str) -> str:
        return self.shell(f"getprop {prop}").strip()

    def dumpsys(self, service: str) -> str:
        return self.shell(f"dumpsys {service}")

    def logcat(self, lines: int = 500) -> str:
        rc, out, err = self._run(["logcat", "-d", "-t", str(lines)], timeout=60)
        if rc != 0:
            raise ActionError(f"adb logcat failed: {err}")
        return out

    def screencap(self, dest: Path) -> None:
        cmd = [self.adb, "-s", self.device_id, "exec-out", "screencap", "-p"]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=30)
        except subprocess.TimeoutExpired:
            raise ActionError("adb screencap timeout")
        if proc.returncode != 0:
            raise ActionError(f"adb screencap failed: {proc.stderr.decode('utf-8', errors='replace')}")
        dest.write_bytes(proc.stdout)

    def uiautomator_dump(self, dest: Path) -> None:
        rc, out, err = self._run(["shell", "uiautomator", "dump", "/sdcard/window_dump.xml"])
        if rc != 0:
            raise ActionError(f"adb uiautomator dump failed: {err}")
        rc, out, err = self._run(["pull", "/sdcard/window_dump.xml", str(dest)])
        if rc != 0:
            raise ActionError(f"adb pull ui dump failed: {err}")

    def start_app(self, package: str, activity: str) -> None:
        rc, out, err = self._run(["shell", "am", "start", "-n", f"{package}/{activity}"])
        if rc != 0:
            raise ActionError(f"adb start app failed: {err}")

    def force_stop(self, package: str) -> None:
        rc, out, err = self._run(["shell", "am", "force-stop", package])
        if rc != 0:
            raise ActionError(f"adb force-stop failed: {err}")


class GitActions:
    """Actions Git autorisées (lecture seule pour l'instant)."""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.git = shutil.which("git")
        if not self.git:
            raise ActionError("git introuvable dans le PATH")

    def _run(self, args: List[str]) -> Tuple[int, str, str]:
        try:
            proc = subprocess.run(
                [self.git] + args,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return proc.returncode, proc.stdout or "", proc.stderr or ""
        except subprocess.TimeoutExpired:
            raise ActionError(f"Timeout git: {' '.join(args)}")

    def status(self) -> str:
        rc, out, err = self._run(["status", "--short"])
        if rc != 0:
            raise ActionError(f"git status failed: {err}")
        return out

    def diff(self) -> str:
        rc, out, err = self._run(["diff"])
        if rc != 0:
            raise ActionError(f"git diff failed: {err}")
        return out

    def current_branch(self) -> str:
        rc, out, err = self._run(["branch", "--show-current"])
        if rc != 0:
            raise ActionError(f"git branch failed: {err}")
        return out.strip()

    def last_log(self, n: int = 5) -> str:
        rc, out, err = self._run(["log", "--oneline", f"-{n}"])
        if rc != 0:
            raise ActionError(f"git log failed: {err}")
        return out


def wait_for_device(device_id: str, timeout: int = 30) -> bool:
    adb = shutil.which("adb")
    if not adb:
        return False
    cmd = [adb, "-s", device_id, "wait-for-device"]
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
