"""Construction d'un paquet contextuel minimal pour les agents IA.

Ne transmet jamais tout le depot, tout l'historique ou tout le logcat.
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from luna_runner.actions import ADBActions, GitActions
from .adb_utils import list_adb_devices, resolve_android_device

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Construit agent-context.json pour chaque cycle."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.project_path = Path(config.get("PROJECT_PATH", ".")).resolve()
        self.max_chars = int(config.get("MAX_CONTEXT_CHARACTERS", 6000))
        self.max_log_lines = int(config.get("MAX_LOG_LINES_FOR_AI", 200))
        self.max_diff_chars = int(config.get("MAX_DIFF_CHARACTERS", 8000))

    def build(
        self,
        mission: Dict[str, Any],
        run_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Retourne le dictionnaire contextuel minimal."""
        mission_id = mission.get("mission_id", "UNKNOWN")
        task_id = mission.get("task_id", mission_id)

        context: Dict[str, Any] = {
            "mission_id": mission_id,
            "task_id": task_id,
            "objective": mission.get("objective", mission.get("description", "")),
            "acceptance_criteria": mission.get("acceptance_criteria", []),
            "iteration": int(mission.get("iteration", 0)),
            "max_iterations": int(mission.get("max_iterations", 3)),
            "history_summary": self._history_summary(mission.get("history", [])),
            "git": self._git_context(),
            "adb": self._adb_context(),
            "tests": self._test_context(),
            "last_result": self._last_result(mission),
            "changed": self._what_changed(mission),
            "errors_new": mission.get("errors_new", []),
            "log_tail": self._log_tail(),
            "evidence_paths": self._evidence_paths(run_dir),
            "requested_decision": self._requested_decision(mission),
        }

        if run_dir:
            run_dir.mkdir(parents=True, exist_ok=True)
            context_path = run_dir / "agent-context.json"
            try:
                with open(context_path, "w", encoding="utf-8") as f:
                    json.dump(context, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.warning("Impossible d'ecrire agent-context.json: %s", e)

        return context

    def _history_summary(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Resume les 3 derniers cycles."""
        summary = []
        for entry in history[-3:]:
            summary.append(
                {
                    "iteration": entry.get("iteration"),
                    "status": entry.get("status"),
                    "agent": entry.get("agent"),
                    "decision": entry.get("decision"),
                    "summary": entry.get("summary", "")[:300],
                }
            )
        return summary

    def _git_context(self) -> Dict[str, Any]:
        try:
            git = GitActions(str(self.project_path))
            return {
                "branch": git.current_branch(),
                "status": git.status()[: self.max_diff_chars],
                "diff": self._truncated_diff(),
            }
        except Exception as e:
            return {"error": str(e)}

    def _truncated_diff(self) -> str:
        try:
            result = subprocess.run(
                ["git", "diff", "--stat"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=15,
            )
            return result.stdout[: self.max_diff_chars]
        except Exception as e:
            return f"diff indisponible: {e}"

    def _adb_context(self) -> Dict[str, Any]:
        # Résolution avec fallback USB si le device configuré est indisponible.
        resolved_id, devices_output = resolve_android_device(self.config)
        if not resolved_id:
            return {
                "available": False,
                "reason": "ANDROID_DEVICE_ID non configure et aucun device ADB detecte",
                "devices": devices_output,
            }
        try:
            adb = ADBActions(resolved_id)
            return {
                "available": True,
                "device_id": resolved_id,
                "model": adb.getprop("ro.product.model"),
                "android_version": adb.getprop("ro.build.version.release"),
                "state": adb.get_state(),
                "devices": devices_output,
            }
        except Exception as e:
            return {
                "available": False,
                "reason": str(e),
                "device_id": resolved_id,
                "devices": devices_output,
            }

    def _test_context(self) -> Dict[str, Any]:
        """Cherche des resultats de tests existants."""
        tests_dir = self.project_path / "runs"
        latest: Optional[Path] = None
        if tests_dir.exists():
            candidates = sorted(tests_dir.glob("*/result.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            if candidates:
                latest = candidates[0]
        if not latest:
            return {"available": False}
        try:
            data = json.loads(latest.read_text(encoding="utf-8"))
            return {
                "available": True,
                "path": str(latest.relative_to(self.project_path)),
                "status": data.get("status"),
                "summary": data.get("summary", "")[:500],
            }
        except Exception as e:
            return {"available": False, "error": str(e)}

    def _last_result(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        history = mission.get("history", [])
        if not history:
            return {}
        last = history[-1]
        return {
            "iteration": last.get("iteration"),
            "status": last.get("status"),
            "summary": last.get("summary", "")[:300],
            "decision": last.get("decision"),
        }

    def _what_changed(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        """Compare l'etat actuel avec le dernier resultat."""
        git_diff = ""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=15,
            )
            git_diff = result.stdout.strip()
        except Exception:
            pass

        changed_files = [f for f in git_diff.splitlines() if f.strip()]
        last = self._last_result(mission)
        return {
            "files": changed_files,
            "new_errors_since_last": mission.get("errors_new", []),
            "last_status": last.get("status"),
            "last_iteration": last.get("iteration"),
        }

    def _log_tail(self) -> List[str]:
        """Retourne les N dernieres lignes de log utiles."""
        logs: List[str] = []
        log_file = self.project_path / "runs" / "supervisor.log"
        if log_file.exists():
            try:
                text = log_file.read_text(encoding="utf-8", errors="replace")
                logs = text.splitlines()[-self.max_log_lines :]
            except Exception:
                pass
        return logs

    def _evidence_paths(self, run_dir: Optional[Path]) -> Dict[str, Optional[str]]:
        if run_dir is None:
            return {}
        paths = {
            "screenshot": None,
            "ui_hierarchy": None,
            "logcat": None,
            "adb_devices": None,
        }
        candidates = {
            "screenshot": ["screenshot.png"],
            "ui_hierarchy": ["ui-hierarchy.xml"],
            "logcat": ["logcat-errors.txt", "logcat-full.txt"],
            "adb_devices": ["adb-devices.txt"],
        }
        for key, names in candidates.items():
            for name in names:
                candidate = run_dir / name
                if candidate.exists():
                    paths[key] = str(candidate.relative_to(self.project_path))
                    break
        return paths

    def _requested_decision(self, mission: Dict[str, Any]) -> str:
        iteration = int(mission.get("iteration", 0))
        max_iter = int(mission.get("max_iterations", 3))
        if iteration >= max_iter - 1:
            return "final_decision_or_complete"
        return "next_action"
