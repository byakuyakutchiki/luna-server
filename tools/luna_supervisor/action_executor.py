"""Exécuteur d'actions validées par le superviseur.

Aucune commande shell arbitraire n'est exécutée. Chaque action correspond à une
fonction Python prédéfinie avec validation stricte des paramètres.
"""

import json
import re
import logging
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from luna_runner.actions import ADBActions, ActionError, GitActions
from luna_runner.config import load_config as load_runner_config
from luna_runner.evidence import EvidenceCollector
from luna_runner.runner import Runner
from .adb_utils import resolve_android_device

logger = logging.getLogger(__name__)


class ExecutorError(Exception):
    pass


class ActionExecutor:
    """Exécute les actions demandées par les agents après validation."""

    SAFE_BRANCH_PREFIX = "automation/"

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.project_path = Path(config["PROJECT_PATH"])
        self.device_id, _ = resolve_android_device(config)
        self.package = config.get("ANDROID_PACKAGE", "fr.yawatch.luna")
        self.activity = config.get("ANDROID_MAIN_ACTIVITY", "fr.yawatch.luna.MainActivity")
        self.runs_dir = Path(config.get("RUNS_DIR", str(self.project_path / "runs")))
        self.agent_shared_path = Path(config.get("AGENT_SHARED_PATH", "/media/windows/Users/saint/Documents/Codex/AGENT_SHARED"))

    BINARY_EXTENSIONS = {
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".apk", ".dex",
        ".keystore", ".jks", ".so", ".zip", ".tar", ".gz", ".pdf",
    }

    PROTECTED_PATH_PATTERNS = (
        "android-app/src/",
        ".env",
        "data/",
        "config/agent_budget_policy.yaml",
        "config/luna_mission_charter.yaml",
    )

    def execute(
        self,
        action: Dict[str, Any],
        mission_id: str,
        task_id: str,
        mission: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Exécute une action structurée et retourne le résultat."""
        action_type = action.get("type", "none")
        params = action.get("parameters") or {}
        mission = mission or {}

        handlers = {
            "none": self._action_none,
            "read_files": self._action_read_files,
            "edit_files": self._action_edit_files,
            "run_tests": self._action_run_tests,
            "build_debug": self._action_build_debug,
            "install_debug": self._action_install_debug,
            "collect_adb": self._action_collect_adb,
            "collect_guardian_evidence": self._action_collect_guardian_evidence,
            "commit_local": self._action_commit_local,
            "write_report": self._action_write_report,
        }

        handler = handlers.get(action_type)
        if handler is None:
            raise ExecutorError(f"Type d'action non géré: {action_type}")

        logger.info("Exécution action: %s", action_type)

        if action_type == "edit_files":
            self._guard_edit_files(params, mission)

        result = handler(params, mission_id, task_id)
        if isinstance(result, dict):
            result["action_type"] = action_type
        return result

    def _action_none(self, params: Dict[str, Any], mission_id: str, task_id: str) -> Dict[str, Any]:
        return {"status": "success", "message": "Aucune action demandée"}

    def _action_read_files(self, params: Dict[str, Any], mission_id: str, task_id: str) -> Dict[str, Any]:
        paths = params.get("paths")
        if paths is None:
            paths = params.get("files")
        if paths is None:
            paths = params.get("file_paths")
        if paths is None:
            paths = params.get("target_files", [])
        if not isinstance(paths, list):
            raise ExecutorError("read_files: paths, files, file_paths ou target_files doit etre une liste")

        global_read_options = params.get("read_options") or {}
        if not isinstance(global_read_options, dict):
            raise ExecutorError("read_files: read_options doit etre un objet")

        default_max_chars = int(self.config.get("MAX_CONTEXT_CHARACTERS", 6000))

        def _normalize_entry(entry: Any) -> Tuple[str, Dict[str, Any]]:
            if isinstance(entry, dict):
                entry_path = (
                    entry.get("path")
                    or entry.get("file")
                    or entry.get("file_path")
                    or entry.get("target_file")
                )
                if not entry_path:
                    raise ExecutorError("read_files: chaque objet doit contenir path, file, file_path ou target_file")
                entry_options = dict(global_read_options)
                nested_options = entry.get("read_options") or {}
                if not isinstance(nested_options, dict):
                    raise ExecutorError("read_files: read_options d'un fichier doit etre un objet")
                entry_options.update(nested_options)
                for key in ("offset", "max_chars"):
                    if key in entry:
                        entry_options[key] = entry[key]
                return str(entry_path), entry_options
            return str(entry), dict(global_read_options)

        def _read_window(options: Dict[str, Any]) -> Tuple[int, int]:
            requested_max_chars = options.get("max_chars", default_max_chars)
            try:
                max_chars = max(1, min(int(requested_max_chars), default_max_chars))
            except (TypeError, ValueError):
                raise ExecutorError("read_files: read_options.max_chars doit etre un entier")

            requested_offset = options.get("offset", 0)
            try:
                offset = max(0, int(requested_offset))
            except (TypeError, ValueError):
                raise ExecutorError("read_files: read_options.offset doit etre un entier")
            return offset, max_chars

        results = {}
        for entry in paths:
            path_label, entry_options = _normalize_entry(entry)
            offset, max_chars = _read_window(entry_options)
            safe_path = self._safe_path(path_label)
            if safe_path is None:
                results[path_label] = {"error": "chemin non autorisé"}
                continue
            try:
                if safe_path.is_dir():
                    entries = sorted(child.name for child in safe_path.iterdir())[:50]
                    results[path_label] = {
                        "type": "directory",
                        "entries": entries,
                        "truncated": len(entries) >= 50,
                    }
                    continue
                size = safe_path.stat().st_size
                suffix = safe_path.suffix.lower()
                if suffix in self.BINARY_EXTENSIONS:
                    results[path_label] = {
                        "type": "binary",
                        "path": str(safe_path),
                        "extension": suffix,
                        "size": size,
                        "content": "[fichier binaire non lu; utiliser le chemin comme preuve]",
                    }
                    continue
                full_content = safe_path.read_text(encoding="utf-8", errors="replace")
                content = full_content[offset:offset + max_chars]
                end_offset = offset + len(content)
                truncated_before = offset > 0
                truncated_after = end_offset < len(full_content)
                if truncated_before or truncated_after:
                    content = (
                        f"[extrait offset={offset}, max_chars={max_chars}, total={len(full_content)}]\n"
                        + content
                        + (
                            f"\n\n[... tronqué après {end_offset} caractères lus sur {len(full_content)}]"
                            if truncated_after else ""
                        )
                    )
                results[path_label] = {
                    "type": "text",
                    "content": content,
                    "size": size,
                    "offset": offset,
                    "max_chars": max_chars,
                    "truncated_before": truncated_before,
                    "truncated_after": truncated_after,
                }
            except Exception as e:
                results[path_label] = {"error": str(e)}

        return {"status": "success", "files": results}

    def _guard_edit_files(self, params: Dict[str, Any], mission: Dict[str, Any]) -> None:
        """Vérifie que edit_files ne touche pas à des zones protégées."""
        if not self._is_safe_branch():
            raise ExecutorError(
                "edit_files refusé: la branche active n'est pas automation/*. "
                "Crée ou bascule vers une branche automation/<nom> avant toute modification."
            )

        allows_guardian = bool(mission.get("allows_guardian_modification"))
        edits = params.get("edits", [])
        if not isinstance(edits, list):
            return

        for edit in edits:
            path = edit.get("path", "")
            if allows_guardian:
                continue
            path_str = str(path).lower()
            for protected in self.PROTECTED_PATH_PATTERNS:
                if protected.lower() in path_str:
                    raise ExecutorError(
                        f"edit_files refusé: '{path}' correspond à une zone protégée ({protected}). "
                        "Utilise allows_guardian_modification=true pour forcer."
                    )

    def _action_edit_files(self, params: Dict[str, Any], mission_id: str, task_id: str) -> Dict[str, Any]:
        """Applique des remplacements exacts dans des fichiers du projet."""
        edits = params.get("edits", [])
        if not isinstance(edits, list):
            raise ExecutorError("edit_files: 'edits' doit être une liste")
        if not edits:
            raise ExecutorError(
                "edit_files: 'edits' est vide. Fournis une liste de remplacements exacts "
                "avec path, old_string et new_string."
            )

        results = []
        for edit in edits:
            path = edit.get("path")
            old_string = edit.get("old_string")
            new_string = edit.get("new_string")

            if not path or old_string is None or new_string is None:
                results.append({"path": path, "status": "error", "error": "champs manquants"})
                continue

            safe_path = self._safe_path(path)
            if safe_path is None:
                results.append({"path": path, "status": "error", "error": "chemin non autorisé"})
                continue

            try:
                content = safe_path.read_text(encoding="utf-8")
                if old_string not in content:
                    results.append({
                        "path": str(path),
                        "status": "error",
                        "error": "old_string introuvable dans le fichier",
                    })
                    continue
                content = content.replace(old_string, new_string, 1)
                safe_path.write_text(content, encoding="utf-8")
                results.append({"path": str(path), "status": "modified"})
            except Exception as e:
                results.append({"path": str(path), "status": "error", "error": str(e)})

        return {"status": "success", "edits": results}

    def _action_run_tests(self, params: Dict[str, Any], mission_id: str, task_id: str) -> Dict[str, Any]:
        suite = params.get("suite", "python")
        if suite == "gradle":
            return self._run_gradle(["test"])
        if suite == "guardian_p0":
            return self._run_command(
                ["python3", "tests/test_guardian_p0.py"],
                cwd=self.project_path,
                timeout=120,
            )
        if suite == "guardian_exit_check":
            return self._run_command(
                ["python3", "tools/luna_supervisor/guardian_exit_check.py"],
                cwd=self.project_path,
                timeout=45,
            )
        if suite == "python":
            return self._run_command(
                ["python3", "-m", "pytest", "-q"],
                cwd=self.project_path,
                timeout=120,
            )
        raise ExecutorError(f"Suite de tests inconnue: {suite}")

    def _action_build_debug(self, params: Dict[str, Any], mission_id: str, task_id: str) -> Dict[str, Any]:
        return self._run_gradle(["assembleDebug"])

    def _action_install_debug(self, params: Dict[str, Any], mission_id: str, task_id: str) -> Dict[str, Any]:
        apk_path = params.get("apk_path") or str(self.project_path / "android-app" / "build" / "apk" / "base.apk")
        safe_apk = self._safe_path(apk_path)
        if safe_apk is None:
            raise ExecutorError("APK path non autorisé")
        if not safe_apk.exists():
            raise ExecutorError(f"APK introuvable: {safe_apk}")

        adb = ADBActions(self.device_id)
        rc, out, err = adb._run(["install", "-r", str(safe_apk)], timeout=120)
        if rc != 0:
            raise ExecutorError(f"adb install failed: {err or out}")
        return {"status": "success", "apk": str(safe_apk), "output": out}

    def _action_collect_adb(self, params: Dict[str, Any], mission_id: str, task_id: str) -> Dict[str, Any]:
        self._validate_collect_adb_params(params)
        runner = Runner(self.config)
        result = runner.execute_diagnostic(mission_id, task_id)
        result["requested_phase"] = params.get("phase") or params.get("objective") or "diagnostic"
        result["android_package"] = self.package
        result["android_activity"] = self.activity
        return {"status": result.get("status", "unknown"), "result": result}

    def _action_collect_guardian_evidence(self, params: Dict[str, Any], mission_id: str, task_id: str) -> Dict[str, Any]:
        """Collecte des preuves Guardian ciblées avec commandes ADB prédéfinies."""
        self._validate_collect_adb_params(params)
        collector = EvidenceCollector(self.runs_dir, mission_id)
        adb = ADBActions(self.device_id)
        artifacts: List[str] = []
        errors: List[str] = []

        def write_artifact(name: str, content: str) -> None:
            collector.write(name, collector.sanitize(content))
            artifacts.append(name)

        def adb_shell_artifact(name: str, command: str) -> None:
            try:
                write_artifact(name, adb.shell(command))
            except ActionError as exc:
                errors.append(f"{name}: {exc}")
                write_artifact(name, f"ERROR: {exc}\n")

        try:
            write_artifact("adb-devices.txt", adb.devices())
            write_artifact("adb-state.txt", adb.get_state())
            model = adb.getprop("ro.product.model")
            version = adb.getprop("ro.build.version.release")
            write_artifact("device-info.txt", f"model={model}\nandroid_version={version}\n")
        except ActionError as exc:
            raise ExecutorError(f"collect_guardian_evidence: ADB indisponible: {exc}")

        if params.get("start_app", True):
            try:
                adb.start_app(self.package, self.activity)
                time.sleep(float(params.get("start_wait_seconds", 2)))
            except ActionError as exc:
                errors.append(f"start_app: {exc}")

        adb_shell_artifact("top-activity-before.txt", "dumpsys activity top | head -120")
        adb_shell_artifact("luna-processes-before.txt", f"ps -A | grep {self.package} || true")
        adb_shell_artifact("luna-services-before.txt", f"dumpsys activity services {self.package}")
        adb_shell_artifact("guardian-notifications-before.txt", "dumpsys notification --noshade | grep -A 60 -iE 'guardian|luna|sos' || true")
        adb_shell_artifact(
            "guardian-logcat-filtered-before.txt",
            "logcat -d -b all -v threadtime | grep -iE 'fr\.yawatch\.luna|guardian|LunaVoice|LunaGuardian|SOS|VOICE EMERGENCY|dry.run|sms_success|call_success|internal_dm_success|native_posts|location' || true",
        )

        try:
            screenshot_path = collector.path("screenshot-before.png")
            adb.screencap(screenshot_path)
            artifacts.append("screenshot-before.png")
        except ActionError as exc:
            errors.append(f"screenshot-before.png: {exc}")
        try:
            ui_path = collector.path("ui-hierarchy-before.xml")
            adb.uiautomator_dump(ui_path)
            artifacts.append("ui-hierarchy-before.xml")
        except ActionError as exc:
            errors.append(f"ui-hierarchy-before.xml: {exc}")

        if params.get("close_app_check", False):
            try:
                adb.force_stop(self.package)
                time.sleep(float(params.get("after_stop_wait_seconds", 2)))
            except ActionError as exc:
                errors.append(f"force_stop: {exc}")
            adb_shell_artifact("luna-processes-after-stop.txt", f"ps -A | grep {self.package} || true")
            adb_shell_artifact("luna-services-after-stop.txt", f"dumpsys activity services {self.package}")
            adb_shell_artifact("guardian-notifications-after-stop.txt", "dumpsys notification --noshade | grep -A 60 -iE 'guardian|luna|sos' || true")
            adb_shell_artifact(
                "guardian-logcat-filtered-after-stop.txt",
                "logcat -d -b all -v threadtime | grep -iE 'fr\.yawatch\.luna|guardian|LunaVoice|LunaGuardian|SOS|VOICE EMERGENCY|dry.run|foreground|mic|audio|sms_success|call_success|internal_dm_success|native_posts' || true",
            )

        result = {
            "status": "success_with_errors" if errors else "success",
            "evidence_directory": str(collector.base),
            "artifacts": artifacts,
            "errors": errors,
            "android_package": self.package,
            "android_activity": self.activity,
        }
        collector.write_json("guardian-evidence-result.json", result)
        return {"status": result["status"], "result": result}

    def _validate_collect_adb_params(self, params: Dict[str, Any]) -> None:
        """Refuse les actions ADB qui ciblent un package different du package configure."""
        text = json.dumps(params, ensure_ascii=False)
        known_wrong = ("fr.luna.guardian", "com.luna.guardian")
        for wrong in known_wrong:
            if wrong in text:
                raise ExecutorError(
                    f"collect_adb refusé: package Android invalide '{wrong}'. "
                    f"Package réel configuré: '{self.package}'."
                )
        package_like = re.findall(r"(?:[a-zA-Z_][\w-]*\.){2,}[a-zA-Z_][\w-]*", text)
        for candidate in package_like:
            if candidate.startswith(("android.", "java.", "kotlin.", "com.android.")):
                continue
            if candidate not in (self.package, self.activity):
                if candidate.endswith(".MainActivity") and candidate != self.activity:
                    raise ExecutorError(
                        f"collect_adb refusé: activité Android invalide '{candidate}'. "
                        f"Activité réelle configurée: '{self.activity}'."
                    )

    def _action_commit_local(self, params: Dict[str, Any], mission_id: str, task_id: str) -> Dict[str, Any]:
        if not self._is_safe_branch():
            raise ExecutorError("commit_local refusé: pas sur une branche automation/*")

        files = params.get("files", [])
        if not isinstance(files, list) or not files:
            raise ExecutorError("commit_local refusé : liste 'files' obligatoire")

        message = params.get("message", f"{mission_id}: modifications agent")
        lower_message = message.lower()
        for forbidden in ("push", "merge", "reset"):
            if forbidden in lower_message:
                raise ExecutorError(f"commit_local refusé: message interdit contient '{forbidden}'")

        git = GitActions(str(self.project_path))
        for path in files:
            safe_path = self._safe_path(path)
            if safe_path is None:
                raise ExecutorError(f"commit_local refusé : chemin non autorisé '{path}'")
            rc, out, err = git._run(["add", str(safe_path.relative_to(self.project_path))])
            if rc != 0:
                raise ExecutorError(f"git add failed for '{path}': {err}")

        rc, out, err = git._run(["commit", "-m", message])
        if rc != 0:
            # Peut échouer s'il n'y a rien à committer
            if "nothing to commit" in out.lower() or "nothing to commit" in err.lower():
                return {"status": "success", "message": "Rien à committer"}
            raise ExecutorError(f"git commit failed: {err}")
        return {"status": "success", "message": out.strip()}

    def _action_write_report(self, params: Dict[str, Any], mission_id: str, task_id: str) -> Dict[str, Any]:
        """Crée un fichier markdown local dans le run_dir."""
        run_dir = self.runs_dir / mission_id / str(int(time.time()))
        run_dir.mkdir(parents=True, exist_ok=True)
        filename = params.get("filename", f"{mission_id}_report.md")
        title = params.get("title", f"Rapport {mission_id}")
        content = params.get("content", "")

        report_path = run_dir / filename
        try:
            report_path.write_text(f"# {title}\n\n{content}\n", encoding="utf-8")
            return {
                "status": "success",
                "path": str(report_path.relative_to(self.project_path)),
                "absolute_path": str(report_path),
            }
        except Exception as e:
            raise ExecutorError(f"Échec écriture rapport: {e}")

    def _run_gradle(self, args: List[str]) -> Dict[str, Any]:
        gradlew = self.project_path / "android-app" / "gradlew"
        if not gradlew.exists():
            raise ExecutorError("gradlew introuvable dans android-app/")
        return self._run_command([str(gradlew)] + args, cwd=self.project_path / "android-app", timeout=300)

    def _run_command(self, cmd: List[str], cwd: Path, timeout: int) -> Dict[str, Any]:
        logger.info("Commande: %s (cwd=%s)", " ".join(cmd), cwd)
        try:
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            raise ExecutorError(f"Timeout après {timeout}s: {' '.join(cmd)}")
        except Exception as e:
            raise ExecutorError(f"Échec commande: {e}")

        return {
            "status": "success" if proc.returncode == 0 else "error",
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }

    def _safe_path(self, path: Any) -> Optional[Path]:
        """Vérifie qu'un chemin reste dans le projet ou AGENT_SHARED."""
        if path is None:
            return None
        raw_path = str(path)
        if raw_path == "AGENT_SHARED" or raw_path.startswith("AGENT_SHARED/"):
            suffix = raw_path.removeprefix("AGENT_SHARED").lstrip("/")
            return (self.agent_shared_path / suffix).resolve()

        p = Path(path)
        if p.is_absolute():
            resolved = p.resolve()
        else:
            resolved = (self.project_path / p).resolve()

        try:
            resolved.relative_to(self.project_path)
        except ValueError:
            try:
                resolved.relative_to(self.agent_shared_path.resolve())
            except ValueError:
                return None
        return resolved

    def _is_safe_branch(self) -> bool:
        """Vérifie que la branche active commence par automation/."""
        try:
            git = GitActions(str(self.project_path))
            branch = git.current_branch()
            return branch.startswith(self.SAFE_BRANCH_PREFIX)
        except Exception:
            return False

    def git_diff_since_start(self) -> str:
        """Retourne le diff actuel du dépôt."""
        try:
            git = GitActions(str(self.project_path))
            return git.diff()
        except Exception as e:
            return f"Impossible d'obtenir le diff: {e}"
