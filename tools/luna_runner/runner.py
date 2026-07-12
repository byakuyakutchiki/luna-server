"""Moteur d'exécution des missions Luna Local Runner."""

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .actions import ADBActions, ActionError, GitActions, wait_for_device
from .config import load_config, require
from .evidence import EvidenceCollector
from .n8n_client import N8NClient


class Runner:
    """Orchestre le diagnostic ADB et la collecte de preuves."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or load_config()
        self.runner_id = self.config["RUNNER_ID"]
        self.device_id = self.config.get("ANDROID_DEVICE_ID", "")
        self.package = self.config.get("ANDROID_PACKAGE", "fr.yawatch.luna")
        self.activity = self.config.get("ANDROID_MAIN_ACTIVITY", "fr.yawatch.luna.MainActivity")
        self.project_path = self.config["PROJECT_PATH"]
        self.runs_dir = Path(self.config.get("RUNS_DIR", "runs"))

    def health(self) -> Dict[str, Any]:
        """Vérifie l'état de santé du runner."""
        result = {
            "runner_id": self.runner_id,
            "project_path": self.project_path,
            "adb_available": False,
            "device_connected": False,
            "device_id": self.device_id,
            "device_model": None,
            "android_version": None,
            "git_branch": None,
        }
        try:
            import shutil

            result["adb_available"] = shutil.which("adb") is not None
            if result["adb_available"] and self.device_id:
                adb = ADBActions(self.device_id)
                devices = adb.devices()
                result["device_connected"] = self.device_id in devices and "device" in devices
                if result["device_connected"]:
                    result["device_model"] = adb.getprop("ro.product.model")
                    result["android_version"] = adb.getprop("ro.build.version.release")
        except Exception as e:
            result["error"] = str(e)

        try:
            git = GitActions(self.project_path)
            result["git_branch"] = git.current_branch()
        except Exception:
            pass

        return result

    def _device_status(self) -> str:
        try:
            if not self.device_id:
                return "unknown"
            adb = ADBActions(self.device_id)
            state = adb.get_state()
            return "connected" if state == "device" else state
        except Exception:
            return "unavailable"

    def execute_diagnostic(self, mission_id: str, task_id: str) -> Dict[str, Any]:
        """Exécute une mission de diagnostic en lecture seule."""
        collector = EvidenceCollector(self.runs_dir, mission_id)
        errors: List[str] = []
        artifacts: List[str] = []
        device_status = "unavailable"

        result: Dict[str, Any] = {
            "mission_id": mission_id,
            "task_id": task_id,
            "runner_id": self.runner_id,
            "status": "success",
            "evidence_directory": str(collector.base),
            "build_status": "not_run",
            "device_status": device_status,
            "error_summary": errors,
            "artifacts": artifacts,
            "requires_ai_analysis": False,
            "requires_human_validation": False,
        }

        mission_payload = {
            "mission_id": mission_id,
            "task_id": task_id,
            "runner_id": self.runner_id,
            "type": "diagnostic",
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        collector.write_json("mission.json", mission_payload)

        try:
            git = GitActions(self.project_path)
            git_info = {
                "branch": git.current_branch(),
                "status": git.status(),
                "last_log": git.last_log(),
            }
            collector.write("git-status-before.txt", json.dumps(git_info, indent=2))
        except Exception as e:
            errors.append(f"Git diagnostic failed: {e}")
            collector.error(str(e))

        try:
            adb = ADBActions(self.device_id)
            device_status = "connected"
            collector.info("ADB device connected")

            devices = adb.devices()
            collector.write("adb-devices.txt", devices)

            state = adb.get_state()
            collector.write("adb-state.txt", state)

            model = adb.getprop("ro.product.model")
            version = adb.getprop("ro.build.version.release")
            collector.write("device-info.txt", f"model={model}\nandroid_version={version}\n")

            # Démarre Luna pour capturer son état UI
            collector.info("Starting Luna app")
            try:
                adb.start_app(self.package, self.activity)
                time.sleep(3)
            except ActionError as e:
                errors.append(f"Start app failed: {e}")
                collector.error(str(e))

            # Screenshot
            try:
                screenshot_path = collector.path("screenshot.png")
                adb.screencap(screenshot_path)
                artifacts.append(str(screenshot_path.relative_to(collector.base)))
            except ActionError as e:
                errors.append(f"Screenshot failed: {e}")
                collector.error(str(e))

            # UI hierarchy
            try:
                ui_path = collector.path("ui-hierarchy.xml")
                adb.uiautomator_dump(ui_path)
                artifacts.append(str(ui_path.relative_to(collector.base)))
            except ActionError as e:
                errors.append(f"UI dump failed: {e}")
                collector.error(str(e))

            # Logcat
            try:
                logcat = adb.logcat(lines=1000)
                collector.write("logcat-full.txt", collector.sanitize(logcat))
                errors_logcat = collector.extract_errors(logcat)
                collector.write("logcat-errors.txt", collector.sanitize(errors_logcat))
                artifacts.append("logcat-full.txt")
                artifacts.append("logcat-errors.txt")
            except ActionError as e:
                errors.append(f"Logcat failed: {e}")
                collector.error(str(e))

            # Dumpsys
            try:
                activity = adb.dumpsys("activity")
                collector.write("dumpsys-activity.txt", collector.sanitize(activity))
                artifacts.append("dumpsys-activity.txt")
            except ActionError as e:
                errors.append(f"dumpsys activity failed: {e}")
                collector.error(str(e))

            try:
                package_info = adb.dumpsys("package")
                collector.write("dumpsys-package.txt", collector.sanitize(package_info))
                artifacts.append("dumpsys-package.txt")
            except ActionError as e:
                errors.append(f"dumpsys package failed: {e}")
                collector.error(str(e))

            # Arrête proprement Luna
            try:
                adb.force_stop(self.package)
            except ActionError as e:
                errors.append(f"Force stop failed: {e}")
                collector.error(str(e))

        except ActionError as e:
            device_status = "unavailable"
            errors.append(f"ADB unavailable: {e}")
            collector.error(str(e))
            result["status"] = "device_unavailable"

        result["device_status"] = device_status
        result["error_summary"] = errors
        result["ended_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Résumé markdown
        summary = self._build_summary(result)
        collector.write("summary.md", summary)
        collector.write_json("result.json", result)

        if errors and result["status"] == "success":
            result["status"] = "success_with_errors"

        return result

    def _build_summary(self, result: Dict[str, Any]) -> str:
        lines = [
            "# Luna Local Runner - Rapport de mission",
            "",
            f"- **mission_id**: {result['mission_id']}",
            f"- **task_id**: {result['task_id']}",
            f"- **runner_id**: {result['runner_id']}",
            f"- **status**: {result['status']}",
            f"- **device_status**: {result['device_status']}",
            f"- **evidence_directory**: {result['evidence_directory']}",
            f"- **build_status**: {result['build_status']}",
            "",
            "## Erreurs",
        ]
        for err in result["error_summary"]:
            lines.append(f"- {err}")
        lines.append("")
        lines.append("## Artifacts")
        for artifact in result["artifacts"]:
            lines.append(f"- {artifact}")
        lines.append("")
        lines.append("## Délai d'analyse IA")
        lines.append("Non requis pour un diagnostic en lecture seule.")
        return "\n".join(lines)

    def poll_once(self) -> Optional[Dict[str, Any]]:
        """Interroge n8n une fois et retourne la mission ou None."""
        client = N8NClient(
            next_job_url=require(self.config, "N8N_NEXT_JOB_URL"),
            report_url=require(self.config, "N8N_REPORT_URL"),
            header_name=self.config.get("N8N_HEADER_NAME", ""),
            header_value=self.config.get("N8N_HEADER_VALUE", ""),
            runner_id=self.runner_id,
        )
        device_status = self._device_status()
        response = client.poll_next_job(device_status=device_status)
        return response

    def send_report(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Envoie un rapport à n8n."""
        client = N8NClient(
            next_job_url=require(self.config, "N8N_NEXT_JOB_URL"),
            report_url=require(self.config, "N8N_REPORT_URL"),
            header_name=self.config.get("N8N_HEADER_NAME", ""),
            header_value=self.config.get("N8N_HEADER_VALUE", ""),
            runner_id=self.runner_id,
        )
        return client.send_report(result)
