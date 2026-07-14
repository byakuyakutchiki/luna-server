"""Superviseur principal Luna Agent Supervisor.

Orchestre le cycle : poll n8n → appel agent → validation → exécution → rapport.
"""

import json
import logging
import sqlite3
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from luna_runner.actions import ADBActions, GitActions
from luna_runner.n8n_client import N8NClient
from luna_runner.runner import Runner

from .action_executor import ActionExecutor, ExecutorError
from .agent_caller import AgentCallError, get_caller
from .budget import BudgetGovernor
from .context_builder import ContextBuilder
from .morning_report import MorningReport
from .routing import decide_agent

logger = logging.getLogger(__name__)


class SupervisorError(Exception):
    pass


class LunaAgentSupervisor:
    """Superviseur autonome multi-agents pour Luna."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.project_path = Path(config["PROJECT_PATH"])
        self.runner_id = config["RUNNER_ID"]
        self.budget = BudgetGovernor(config)
        self.executor = ActionExecutor(config)
        self.context_builder = ContextBuilder(config)
        self.morning_report = MorningReport(config, self.budget)
        self.charter = self._load_charter()
        self.lock_file = Path(config.get("RUNS_DIR", str(self.project_path / "runs"))) / ".supervisor.lock"
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_n8n_client()

    def _load_charter(self) -> Dict[str, Any]:
        """Charge la charte produit versionnee si elle existe."""
        charter_path = self.project_path / "config" / "luna_mission_charter.yaml"
        if not charter_path.exists():
            return {}
        try:
            import yaml
            with open(charter_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning("Impossible de charger la charte produit: %s", e)
            return {}

    def _ensure_n8n_client(self) -> None:
        from luna_runner.config import require
        self.n8n_client = N8NClient(
            next_job_url=require(self.config, "N8N_NEXT_JOB_URL"),
            report_url=require(self.config, "N8N_REPORT_URL"),
            header_name=self.config.get("N8N_HEADER_NAME", ""),
            header_value=self.config.get("N8N_HEADER_VALUE", ""),
            runner_id=self.runner_id,
        )

    def health(self) -> Dict[str, Any]:
        """Retourne l'état de santé du superviseur."""
        runner = Runner(self.config)
        runner_health = runner.health()
        return {
            "runner_id": self.runner_id,
            "project_path": str(self.project_path),
            "git_branch": runner_health.get("git_branch"),
            "adb_available": runner_health.get("adb_available"),
            "device_connected": runner_health.get("device_connected"),
            "device_model": runner_health.get("device_model"),
            "android_version": runner_health.get("android_version"),
            "budget": self.budget.status(),
            "locked": self.lock_file.exists(),
        }

    def acquire_lock(self, mission_id: str) -> bool:
        """Tente d'acquérir le verrou du superviseur."""
        if self.lock_file.exists():
            try:
                current = self.lock_file.read_text(encoding="utf-8").strip()
            except Exception:
                current = "unknown"
            logger.warning("Verrou déjà actif: %s", current)
            return False
        try:
            self.lock_file.write_text(mission_id, encoding="utf-8")
            return True
        except Exception as e:
            logger.error("Impossible de créer le verrou: %s", e)
            return False

    def release_lock(self) -> None:
        try:
            self.lock_file.unlink(missing_ok=True)
        except Exception as e:
            logger.warning("Impossible de supprimer le verrou: %s", e)

    def poll_once(self) -> Optional[Dict[str, Any]]:
        """Interroge n8n une fois pour une mission."""
        runner = Runner(self.config)
        device_status = self._device_status()
        response = self.n8n_client.poll_next_job(device_status=device_status)
        # n8n peut renvoyer une liste [{status: ..., mission: ...}] avec allIncomingItems
        if isinstance(response, list) and response:
            response = response[0]
        # n8n renvoie {status: "assigned", mission: {...}} ou {status: "idle"}
        if response and response.get("status") == "assigned":
            mission = response.get("mission")
            if mission:
                return mission
        return response

    def _device_status(self) -> str:
        try:
            runner = Runner(self.config)
            return runner._device_status()
        except Exception:
            return "unavailable"

    def run_once(self, mission_override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Exécute un cycle complet : récupération, traitement, rapport."""
        if mission_override:
            mission = mission_override
        else:
            mission = self.poll_once()
            if mission is None or mission.get("status") == "idle":
                return {
                    "status": "idle",
                    "message": "Aucune mission disponible",
                    "runner_id": self.runner_id,
                }

        mission_id = mission.get("mission_id", "UNKNOWN")
        task_id = mission.get("task_id", mission_id)

        if not self.acquire_lock(mission_id):
            return {
                "status": "locked",
                "message": "Un autre run est déjà actif",
                "runner_id": self.runner_id,
            }

        try:
            result = self._process_mission(mission)
        except Exception as e:
            logger.exception("Échec du traitement de la mission")
            result = {
                "mission_id": mission_id,
                "task_id": task_id,
                "runner_id": self.runner_id,
                "status": "error",
                "error_summary": [str(e)],
                "requires_human_validation": True,
            }
        finally:
            self.release_lock()

        # Envoi du rapport à n8n
        try:
            report_response = self.n8n_client.send_report(result)
            result["n8n_report_response"] = report_response
        except Exception as e:
            logger.error("Échec envoi rapport n8n: %s", e)
            result["n8n_report_error"] = str(e)

        return result

    def _process_mission(self, mission: Dict[str, Any]) -> Dict[str, Any]:
        mission_id = mission.get("mission_id", "UNKNOWN")
        task_id = mission.get("task_id", mission_id)
        role = mission.get("role", "operator")
        iteration = int(mission.get("iteration", 0))
        max_iterations = int(mission.get("max_iterations", self.config.get("MAX_ITERATIONS", 3)))

        logger.info("Traitement mission %s/%s rôle=%s iteration=%d/%d", mission_id, task_id, role, iteration, max_iterations)

        # Prépare le contexte minimal
        run_dir = self._run_dir(mission_id, task_id)
        context = self.context_builder.build(mission, run_dir)

        # Routage intelligent : mission, ADB, Git, tests, changements, budget
        routing = decide_agent(mission, context, self.budget, self.config)
        if not routing.should_call:
            logger.info("Appel IA bloque par le routeur: %s", routing.reason)
            result = {
                "mission_id": mission_id,
                "task_id": task_id,
                "runner_id": self.runner_id,
                "status": "paused_routing",
                "reason": routing.reason,
                "requires_human_validation": False,
            }
            self._write_agent_shared_report(mission, result, run_dir, routing.agent_name or "routing")
            return result

        # Appelle l'agent
        try:
            caller = get_caller(routing.role, self.config)
            if not caller.is_available():
                result = {
                    "mission_id": mission_id,
                    "task_id": task_id,
                    "runner_id": self.runner_id,
                    "status": "error",
                    "error_summary": [f"Agent {routing.role} indisponible"],
                    "requires_human_validation": False,
                }
                self._write_agent_shared_report(mission, result, run_dir, routing.agent_name or routing.role)
                return result

            agent_name = caller.name
            can_call, budget_reason = self.budget.can_call(
                agent_name, mission_id, reason=routing.reason
            )
            if not can_call:
                result = {
                    "mission_id": mission_id,
                    "task_id": task_id,
                    "runner_id": self.runner_id,
                    "status": "paused_budget",
                    "error_summary": [f"Budget atteint: {budget_reason}"],
                    "requires_human_validation": False,
                }
                self._write_agent_shared_report(mission, result, run_dir, agent_name)
                return result

            start = time.time()
            decision = caller.call(mission, context)
            duration_ms = int((time.time() - start) * 1000)
            context_size = len(json.dumps(context, ensure_ascii=False))
            self.budget.record_call(
                agent_name,
                mission_id,
                reason=routing.reason,
                context_size=context_size,
                duration_ms=duration_ms,
                success=True,
                result_summary=decision.summary[:200],
            )
        except AgentCallError as e:
            agent_for_ledger = agent_name if "agent_name" in locals() else routing.agent_name
            self.budget.record_call(
                agent_for_ledger,
                mission_id,
                reason=routing.reason,
                success=False,
                result_summary=str(e)[:200],
            )
            result = {
                "mission_id": mission_id,
                "task_id": task_id,
                "runner_id": self.runner_id,
                "status": "error",
                "error_summary": [f"Appel agent {routing.role} échoué: {e}"],
                "requires_human_validation": False,
            }
            self._write_agent_shared_report(mission, result, run_dir, agent_for_ledger or routing.role)
            return result

        # Loggue la décision
        logger.info("Décision agent: %s", decision.decision)

        # Cas audit non destructif : aboutit sur needs_audit, pas waiting_human_approval
        if decision.decision == "audit":
            forbidden_actions = self._get_mission_field(mission, "forbidden_actions", [])
            requested_action_type = decision.requested_action.get("type", "none")
            action_is_forbidden = requested_action_type in forbidden_actions
            action_is_destructive = self._is_destructive_action(requested_action_type)

            if action_is_forbidden or (action_is_destructive and decision.requires_human_validation):
                logger.info("Audit avec action sensible/interdite : validation humaine requise")
                result = {
                    "mission_id": mission_id,
                    "task_id": task_id,
                    "runner_id": self.runner_id,
                    "status": "waiting_human_approval",
                    "agent_decision": decision.to_dict(),
                    "summary": decision.summary,
                    "requires_human_validation": True,
                }
                self._write_agent_shared_report(mission, result, run_dir, agent_name)
                return result

            # Execute une eventuelle action d'inspection non destructive
            action_result: Dict[str, Any] = {}
            if requested_action_type not in ("none",):
                try:
                    action_result = self.executor.execute(
                        decision.requested_action, mission_id, task_id, mission=mission
                    )
                except ExecutorError as e:
                    self.budget.record_error(mission_id, f"executor:{requested_action_type}")
                    result = {
                        "mission_id": mission_id,
                        "task_id": task_id,
                        "runner_id": self.runner_id,
                        "status": "error",
                        "agent_decision": decision.to_dict(),
                        "error_summary": [f"Exécution action échouée: {e}"],
                        "requires_human_validation": False,
                    }
                    self._write_agent_shared_report(mission, result, run_dir, agent_name)
                    return result

            diff = self.executor.git_diff_since_start()
            result = {
                "mission_id": mission_id,
                "task_id": task_id,
                "runner_id": self.runner_id,
                "status": self._determine_final_status(mission, decision, action_result),
                "agent_decision": decision.to_dict(),
                "action_result": action_result,
                "summary": decision.summary,
                "git_diff": diff,
                "requires_human_validation": False,
                "iteration": iteration,
                "max_iterations": max_iterations,
                "next_role": routing.next_role or role,
            }
            self._write_agent_shared_report(mission, result, run_dir, agent_name)
            return result

        # Validation humaine demandée par l'agent
        if decision.requires_human_validation:
            result = {
                "mission_id": mission_id,
                "task_id": task_id,
                "runner_id": self.runner_id,
                "status": "waiting_human_approval",
                "agent_decision": decision.to_dict(),
                "summary": decision.summary,
                "requires_human_validation": True,
            }
            self._write_agent_shared_report(mission, result, run_dir, agent_name)
            return result

        # Actions bloquées ou terminées
        if decision.decision == "blocked":
            result = {
                "mission_id": mission_id,
                "task_id": task_id,
                "runner_id": self.runner_id,
                "status": "blocked",
                "agent_decision": decision.to_dict(),
                "summary": decision.summary,
                "requires_human_validation": True,
            }
            self._write_agent_shared_report(mission, result, run_dir, agent_name)
            return result

        if decision.decision in ("complete", "approved"):
            result = {
                "mission_id": mission_id,
                "task_id": task_id,
                "runner_id": self.runner_id,
                "status": "complete",
                "agent_decision": decision.to_dict(),
                "summary": decision.summary,
                "requires_human_validation": False,
            }
            self._write_agent_shared_report(mission, result, run_dir, agent_name)
            return result

        # Vérifie les actions interdites explicitement par la mission
        forbidden_actions = self._get_mission_field(mission, "forbidden_actions", [])
        requested_action_type = decision.requested_action.get("type", "none")
        if requested_action_type in forbidden_actions:
            logger.warning("Action interdite par la mission: %s", requested_action_type)
            result = {
                "mission_id": mission_id,
                "task_id": task_id,
                "runner_id": self.runner_id,
                "status": "blocked",
                "agent_decision": decision.to_dict(),
                "summary": f"Action '{requested_action_type}' interdite par la mission",
                "requires_human_validation": True,
            }
            self._write_agent_shared_report(mission, result, run_dir, agent_name)
            return result

        # Exécute l'action demandée
        action_result: Dict[str, Any] = {}
        try:
            action_result = self.executor.execute(
                decision.requested_action, mission_id, task_id, mission=mission
            )
        except ExecutorError as e:
            error_signature = f"executor:{decision.requested_action.get('type')}"
            self.budget.record_error(mission_id, error_signature)
            result = {
                "mission_id": mission_id,
                "task_id": task_id,
                "runner_id": self.runner_id,
                "status": "error",
                "agent_decision": decision.to_dict(),
                "error_summary": [f"Exécution action échouée: {e}"],
                "requires_human_validation": False,
            }
            self._write_agent_shared_report(mission, result, run_dir, agent_name)
            return result

        # Diff après modification
        diff = self.executor.git_diff_since_start()

        # Boucle : une seule itération à la fois
        if decision.decision == "execute" and iteration + 1 < max_iterations:
            return {
                "mission_id": mission_id,
                "task_id": task_id,
                "runner_id": self.runner_id,
                "status": "in_progress",
                "agent_decision": decision.to_dict(),
                "action_result": action_result,
                "summary": decision.summary,
                "git_diff": diff,
                "requires_human_validation": False,
                "iteration": iteration + 1,
                "max_iterations": max_iterations,
                "next_role": routing.next_role or role,
            }

        # Dernière itération : statut final et rapport
        final_status = self._determine_final_status(mission, decision, action_result)
        result = {
            "mission_id": mission_id,
            "task_id": task_id,
            "runner_id": self.runner_id,
            "status": final_status,
            "agent_decision": decision.to_dict(),
            "action_result": action_result,
            "summary": decision.summary,
            "git_diff": diff,
            "requires_human_validation": False,
            "iteration": iteration,
            "max_iterations": max_iterations,
            "next_role": routing.next_role or role,
        }
        self._write_agent_shared_report(mission, result, run_dir, agent_name)
        return result

    def _get_mission_field(
        self, mission: Dict[str, Any], field: str, default: Any = None
    ) -> Any:
        """Lit un champ de mission, soit au premier niveau, soit dans mission_context_json."""
        if field in mission:
            return mission[field]
        ctx = mission.get("mission_context_json") or "{}"
        if isinstance(ctx, str):
            try:
                ctx_obj = json.loads(ctx)
            except Exception:
                ctx_obj = {}
        else:
            ctx_obj = ctx or {}
        return ctx_obj.get(field, default)

    def _is_terminal_status(self, status: str) -> bool:
        """Dit si un statut est terminal (pas de ré-itération automatique)."""
        return status in (
            "success",
            "needs_audit",
            "blocked",
            "complete",
            "waiting_human_approval",
            "error",
            "paused_budget",
            "paused_routing",
        )

    def _has_action_error(self, action_result: Dict[str, Any]) -> bool:
        """Vérifie si le résultat d'une action signale une erreur."""
        if action_result.get("status") == "error":
            return True
        for edit in action_result.get("edits", []):
            if edit.get("status") == "error":
                return True
        return False

    @staticmethod
    def _is_destructive_action(action_type: str) -> bool:
        """Dit si une action est destructive ou necessite validation humaine."""
        return action_type in (
            "edit_files", "build_debug", "install_debug", "commit_local"
        )

    def _determine_final_status(
        self,
        mission: Dict[str, Any],
        decision: Any,
        action_result: Dict[str, Any],
    ) -> str:
        """Détermine le statut final après la dernière itération exécutée."""
        expected = self._get_mission_field(mission, "expected_final_status")
        action_error = self._has_action_error(action_result)

        if expected:
            if action_error and str(expected) != "needs_audit":
                return "error"
            return str(expected)

        if decision.decision == "blocked":
            return "blocked"
        if decision.decision in ("complete", "approved"):
            return "complete"
        if decision.requires_human_validation:
            return "waiting_human_approval"

        if action_error:
            return "error"

        action_type = action_result.get("action_type") or decision.requested_action.get("type", "none")
        if action_type in ("collect_adb", "read_files", "audit", "inspect"):
            return "needs_audit"

        return "success"

    def _collect_status_report(self) -> Dict[str, Any]:
        """Collecte un etat rapide des services, missions recentes et budget."""
        report: Dict[str, Any] = {"services": {}, "recent_missions": [], "budget": {}}

        # Services systemd utilisateur
        for service in ("luna-agent-supervisor.service", "luna-mission-store.service"):
            try:
                proc = subprocess.run(
                    ["systemctl", "--user", "is-active", service],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                report["services"][service] = proc.stdout.strip() or "unknown"
            except Exception as e:
                report["services"][service] = f"erreur: {e}"

        # Dernieres missions dans la DB SQLite
        db_path = self.project_path / "data" / "luna_missions.db"
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path), timeout=5)
            cur = conn.cursor()
            cur.execute(
                "SELECT mission_id, status, current_role, iteration, max_iterations, updated_at "
                "FROM luna_missions ORDER BY updated_at DESC LIMIT 10"
            )
            report["recent_missions"] = [
                {
                    "mission_id": row[0],
                    "status": row[1],
                    "role": row[2],
                    "iteration": row[3],
                    "max_iterations": row[4],
                    "updated_at": row[5],
                }
                for row in cur.fetchall()
            ]
            conn.close()
        except Exception as e:
            report["recent_missions_error"] = str(e)

        # Budget restant
        try:
            budget_status = self.budget.status()
            report["budget"] = {
                "date": budget_status.get("date"),
                "total_today": budget_status.get("total_today", 0),
                "max_total_per_day": budget_status.get("max_total_per_day", 0),
                "daily": budget_status.get("daily", {}),
                "usage_ratio": budget_status.get("usage_ratio", 0.0),
                "governor_state": budget_status.get("governor_state", "unknown"),
            }
        except Exception as e:
            report["budget_error"] = str(e)

        return report

    def _write_agent_shared_report(
        self,
        mission: Dict[str, Any],
        result: Dict[str, Any],
        run_dir: Path,
        agent_name: str,
    ) -> Optional[Path]:
        """Crée un rapport court dans AGENT_SHARED pour les statuts terminaux."""
        status = result.get("status", "")
        if not self._is_terminal_status(status):
            return None

        agent_shared = Path("/media/windows/Users/saint/Documents/Codex/AGENT_SHARED")
        try:
            agent_shared.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning("Impossible de créer AGENT_SHARED: %s", e)
            return None

        mission_id = result.get("mission_id", "UNKNOWN")
        report_path = agent_shared / f"{mission_id}_REPORT.md"

        objective = mission.get("objective", mission.get("description", ""))
        action = result.get("action_result", {})
        action_type = action.get("action_type", result.get("agent_decision", {}).get("requested_action", {}).get("type", "none"))
        modified_files_info = self._extract_modified_files(result)
        mission_files = modified_files_info.get("mission_files", [])
        workspace_dirty = modified_files_info.get("workspace_dirty", [])
        evidence_paths = self._extract_evidence_paths(run_dir)
        budget_status = self.budget.status()
        mission_budget = budget_status.get("missions", {}).get(mission_id, {})

        lines: List[str] = [
            f"# Rapport de mission : {mission_id}",
            "",
            f"- **Mission ID** : {mission_id}",
            f"- **Objectif** : {objective}",
            f"- **Date** : {datetime.now(timezone.utc).isoformat()}",
            f"- **Agent appelé** : {agent_name}",
            f"- **Action exécutée** : {action_type}",
            f"- **Statut final** : {status}",
            "",
            "## Fichiers modifiés par cette mission",
        ]
        if mission_files:
            for f in mission_files:
                lines.append(f"- {f}")
        else:
            lines.append("- Aucun fichier modifié par cette mission")

        lines.extend(["", "## Fichiers du workspace deja modifies avant la mission"])
        if workspace_dirty:
            for f in workspace_dirty:
                lines.append(f"- {f}")
        else:
            lines.append("- Aucun fichier preexistant modifie")

        lines.extend(["", "## Chemins des preuves locales"])
        if evidence_paths:
            for p in evidence_paths:
                lines.append(f"- {p}")
        else:
            lines.append(f"- Run directory : {run_dir}")

        lines.extend(["", "## Budget consommé"])
        lines.append(f"- Appels mission : {dict(mission_budget)}")
        lines.append(f"- Total journalier : {budget_status.get('total_today', 0)}")

        # Enrichissement automatique : etat des services, missions, budget restant
        status_report = self._collect_status_report()
        lines.extend(["", "## État des services systemd"])
        for svc, svc_status in status_report.get("services", {}).items():
            lines.append(f"- {svc}: {svc_status}")

        lines.extend(["", "## Dernières missions"])
        recent_missions = status_report.get("recent_missions", [])
        if recent_missions:
            for m in recent_missions:
                lines.append(
                    f"- {m['mission_id']} | {m['status']} | {m['role']} | "
                    f"it={m['iteration']}/{m['max_iterations']} | {m['updated_at']}"
                )
        else:
            lines.append(f"- {status_report.get('recent_missions_error', 'Aucune mission recente')}")

        lines.extend(["", "## Budget restant"])
        budget_report = status_report.get("budget", {})
        lines.append(f"- Date: {budget_report.get('date')}")
        lines.append(f"- Consommation: {budget_report.get('total_today', 0)} / {budget_report.get('max_total_per_day', 0)}")
        lines.append(f"- Détail journalier: {budget_report.get('daily', {})}")
        lines.append(f"- Ratio d'usage: {budget_report.get('usage_ratio', 0.0):.2%}")
        lines.append(f"- État du gouverneur: {budget_report.get('governor_state', 'unknown')}")

        lines.extend(["", "## Prochaine action recommandée"])
        lines.append(self._recommended_next_action(status))
        lines.append("")

        try:
            report_path.write_text("\n".join(lines), encoding="utf-8")
            logger.info("Rapport AGENT_SHARED créé: %s", report_path)
            return report_path
        except Exception as e:
            logger.warning("Impossible d'écrire le rapport AGENT_SHARED: %s", e)
            return None

    def _extract_modified_files(self, result: Dict[str, Any]) -> Dict[str, List[str]]:
        """Extrait la liste des fichiers modifies par la mission et ceux deja sales dans le workspace."""
        workspace_dirty: List[str] = []
        try:
            from luna_runner.actions import GitActions
            git = GitActions(str(self.project_path))
            rc, out, _ = git._run(["diff", "--name-only"])
            if rc == 0:
                for line in out.splitlines():
                    line = line.strip()
                    if line:
                        workspace_dirty.append(line)
        except Exception as e:
            logger.debug("Impossible de récupérer les fichiers modifiés: %s", e)

        mission_files: List[str] = []
        action = result.get("action_result", {})
        if isinstance(action.get("edits"), list):
            for edit in action["edits"]:
                if edit.get("status") == "modified" and edit.get("path"):
                    mission_files.append(edit["path"])

        return {
            "mission_files": sorted(set(mission_files)),
            "workspace_dirty": sorted(set(workspace_dirty)),
        }

    def _extract_evidence_paths(self, run_dir: Path) -> List[str]:
        """Retourne les chemins relatifs des preuves collectées dans le run."""
        paths: List[str] = []
        if not run_dir.exists():
            return paths
        for name in ("screenshot.png", "ui-hierarchy.xml", "logcat-errors.txt", "logcat-full.txt", "adb-devices.txt"):
            candidate = run_dir / name
            if candidate.exists():
                try:
                    paths.append(str(candidate.relative_to(self.project_path)))
                except Exception:
                    paths.append(str(candidate))
        return paths

    def _recommended_next_action(self, status: str) -> str:
        if status == "needs_audit":
            return "Revue humaine / audit requis avant poursuite."
        if status == "blocked":
            return "Validation humaine requise pour débloquer la mission."
        if status == "waiting_human_approval":
            return "Décision humaine attendue."
        if status == "complete":
            return "Mission terminée. Aucune action supplémentaire."
        if status == "success":
            return "Mission terminée avec succès."
        return "Vérifier le statut et relancer si nécessaire."

    def _build_context(self, mission: Dict[str, Any]) -> str:
        """Construit un contexte minimal pour l'agent."""
        lines: List[str] = []

        # État Git
        try:
            git = self._git()
            lines.append(f"Branche active: {git.current_branch()}")
            status = git.status()
            if status:
                lines.append("Fichiers modifiés non commités:")
                lines.append(status)
        except Exception as e:
            lines.append(f"État Git indisponible: {e}")

        # État ADB
        try:
            if self.config.get("ANDROID_DEVICE_ID"):
                adb = ADBActions(self.config["ANDROID_DEVICE_ID"])
                model = adb.getprop("ro.product.model")
                version = adb.getprop("ro.build.version.release")
                state = adb.get_state()
                lines.append(f"Téléphone: {model} (Android {version}) - état: {state}")
        except Exception as e:
            lines.append(f"État ADB indisponible: {e}")

        # Budget restant
        budget_status = self.budget.status()
        lines.append(f"Budget journalier: {budget_status.get('daily', {})}")

        # Historique de la mission si fourni
        history = mission.get("history", [])
        if history:
            lines.append("=== HISTORIQUE RÉCENT ===")
            for entry in history[-3:]:
                lines.append(json.dumps(entry, ensure_ascii=False))

        return "\n".join(lines)

    def _run_dir(self, mission_id: str, task_id: str) -> Path:
        """Retourne le repertoire de run pour cette mission/tache."""
        run_id = f"{int(time.time())}"
        run_dir = Path(self.config.get("RUNS_DIR", str(self.project_path / "runs"))) / mission_id / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def generate_morning_report(self, mission_result: Optional[Dict[str, Any]] = None) -> Path:
        """Genere le rapport du matin sans appel IA."""
        return self.morning_report.generate(mission_result)

    def _git(self):
        # Helper interne pour l'exécuteur
        from luna_runner.actions import GitActions
        return GitActions(str(self.project_path))
