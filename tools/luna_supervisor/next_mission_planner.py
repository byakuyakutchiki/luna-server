"""Planificateur de prochaine mission autonome.

Lit la roadmap et la checklist, choisit une mission sûre,
et la crée dans mission_store si auto_next=True.

Règles :
- ignore les missions contenant des actions explicitement interdites
- propose mais ne crée pas automatiquement les missions sensibles
  (Guardian/APK/Cloud) sans validation humaine
- s'arrête si le budget est insuffisant
- écrit toujours un rapport dans AGENT_SHARED
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from . import safety
from .budget import BudgetGovernor

logger = logging.getLogger(__name__)

DEFAULT_AGENT_SHARED = Path("/media/windows/Users/saint/Documents/Codex/AGENT_SHARED")
ROADMAP_FILE = "AUTONOMY_COMPLETE_ROADMAP.md"
CHECKLIST_FILE = "YAWATCH_AUTONOMY_CHECKLIST.md"

# Zones sensibles : une mission qui les touche doit être qualifiée
# "audit/lecture/non destructif" pour être considérée comme contrôlée.
SENSITIVE_ZONES = ["guardian", "apk", "cloud", "production", "deploy"]

# Marqueurs qui indiquent une mission non destructive / contrôlée.
NON_DESTRUCTIVE_MARKERS = [
    "audit",
    "lecture",
    "non destructif",
    "read_only",
    "review",
    "plan",
    "rapport",
    "checklist",
    "cleanup plan",
    "identifier",
    "verifier",
]

# Marqueurs qui indiquent qu'une mission ne peut pas être exécutée automatiquement
# par le superviseur (nécessite Codex, un humain, ou aucun appel IA).
NO_AUTO_AI_MARKERS = [
    "sans appel kimi",
    "sans appel ia",
    "sans ia",
    "no ai",
    "no kimi",
    "codex",
    "review par codex",
    "humain",
]

# Missions de la roadmap explicitement marquées comme non destructives
# dans leur identifiant ou leur description.
SAFE_MISSION_PREFIXES = [
    "CODEX-REVIEW-",
    "SUPERVISOR-GIT-CLEANUP-PLAN-",
    "SUPERVISOR-COMMAND-ENTRYPOINT-",
    "SUPERVISOR-BUDGET-POLICY-",
    "SUPERVISOR-NEXT-MISSION-PLANNER-",
    "SUPERVISOR-AUDIT-",
    "SUPERVISOR-AUTONOMY-",
    "TEST-",
]


class NextMissionPlanner:
    """Planifie la mission suivante depuis la roadmap autonome."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.agent_shared = Path(config.get("AGENT_SHARED", str(DEFAULT_AGENT_SHARED)))
        self.roadmap_path = self.agent_shared / ROADMAP_FILE
        self.checklist_path = self.agent_shared / CHECKLIST_FILE
        self.mission_store_url = self._mission_store_url()

    def _mission_store_url(self) -> str:
        host = self.config.get("LUNA_MISSION_STORE_HOST", "127.0.0.1")
        port = int(self.config.get("LUNA_MISSION_STORE_PORT", "9876"))
        return f"http://{host}:{port}/create"

    def _has_budget_for_next_mission(self) -> tuple[bool, str]:
        """Vérifie qu'il reste au moins un appel IA disponible pour la suite."""
        try:
            budget = BudgetGovernor(self.config)
            status = budget.status()
            if status.get("governor_state") == "exhausted":
                return False, "budget epuise"
            usage = float(status.get("usage_ratio", 0.0))
            if usage >= 1.0:
                return False, "ratio d usage a 100%"
            total_today = int(status.get("total_today", 0))
            max_total = int(status.get("max_total_per_day", 0))
            if max_total > 0 and total_today >= max_total:
                return False, f"limite journaliere atteinte ({total_today}/{max_total})"
            return True, ""
        except Exception as e:
            logger.warning("Impossible de verifier le budget: %s", e)
            return False, f"erreur budget: {e}"

    def plan(self, auto_next: bool = False) -> Dict[str, Any]:
        """Choisit et éventuellement crée la prochaine mission sûre.

        Retourne un dict avec planner_status, next_mission_id, objective,
        risk_level, auto_created, reason.
        """
        result: Dict[str, Any] = {
            "planner_status": "idle",
            "next_mission_id": None,
            "objective": None,
            "risk_level": None,
            "auto_created": False,
            "reason": "aucune action demandee",
        }

        candidates = self._load_candidates()
        if not candidates:
            result["reason"] = "aucune mission candidate trouvee dans la roadmap"
            return result

        selected: Optional[Dict[str, Any]] = None
        for candidate in candidates:
            risk = self._assess_risk(candidate)
            candidate["risk_level"] = risk
            if risk == "forbidden":
                logger.info("Mission %s ignoree (interdite): %s", candidate["mission_id"], candidate["objective"])
                continue
            if risk == "guarded":
                # On retient la première mission gardée si aucune safe n'existe,
                # mais on ne la créera pas automatiquement.
                if selected is None:
                    selected = candidate
                continue
            # safe : on prend la première et on arrête
            selected = candidate
            break

        if not selected:
            result["reason"] = "aucune mission sure trouvee dans la roadmap"
            return result

        result["next_mission_id"] = selected["mission_id"]
        result["objective"] = selected["objective"]
        result["risk_level"] = selected["risk_level"]

        if selected["risk_level"] == "guarded":
            result["planner_status"] = "guarded"
            result["reason"] = (
                f"mission {selected['mission_id']} touche une zone sensible ; "
                "validation humaine requise avant creation"
            )
            return result

        if not auto_next:
            result["planner_status"] = "proposed"
            result["reason"] = "auto_next=false ; mission proposee mais non creee"
            return result

        # Vérifie le budget avant toute création automatique
        budget_ok, budget_reason = self._has_budget_for_next_mission()
        if not budget_ok:
            result["planner_status"] = "paused_budget"
            result["reason"] = f"budget insuffisant pour créer la mission suivante : {budget_reason}"
            return result

        created = self._create_mission(selected)
        if created:
            result["planner_status"] = "created"
            result["auto_created"] = True
            result["reason"] = f"mission {selected['mission_id']} creee automatiquement"
        else:
            result["planner_status"] = "error"
            result["reason"] = "echec creation mission dans mission_store"

        return result

    def _load_candidates(self) -> List[Dict[str, Any]]:
        """Parse la roadmap et retourne les missions candidates dans l'ordre."""
        if not self.roadmap_path.exists():
            logger.warning("Roadmap introuvable: %s", self.roadmap_path)
            return []

        text = self.roadmap_path.read_text(encoding="utf-8")
        candidates: List[Dict[str, Any]] = []

        # Découpe par blocs ### N. MISSION_ID
        parts = re.split(r"^### \d+\.\s+([A-Z0-9\-_]+)\s*$", text, flags=re.MULTILINE)
        # parts[0] = préambule, puis [id1, bloc1, id2, bloc2, ...]
        for i in range(1, len(parts), 2):
            mission_id = parts[i].strip()
            block = parts[i + 1]

            objective_match = re.search(r"(?im)^But\s*:\s*(.+?)$", block)
            objective = objective_match.group(1).strip() if objective_match else f"Mission {mission_id}"

            status_match = re.search(r"(?im)^Statut attendu\s*:\s*`?([^`\r\n]+)`?", block)
            expected_final_status = status_match.group(1).strip() if status_match else "needs_audit"

            candidates.append({
                "mission_id": mission_id,
                "objective": objective,
                "expected_final_status": expected_final_status,
            })

        return candidates

    def _assess_risk(self, candidate: Dict[str, Any]) -> str:
        """Évalue le niveau de risque d'une mission candidate.

        Retourne 'safe', 'guarded' ou 'forbidden'.
        """
        objective = candidate.get("objective", "")
        mission_id = candidate.get("mission_id", "")

        # Validation stricte via le module safety (mots interdits)
        ok, reason = safety.validate_prompt(objective)
        if not ok:
            logger.info("Mission %s refusee par safety: %s", mission_id, reason)
            return "forbidden"

        normalized = safety._normalize(objective)

        # Mission nécessitant un agent externe (Codex) ou explicitement sans appel IA
        if any(marker in normalized for marker in NO_AUTO_AI_MARKERS):
            logger.info("Mission %s requiert validation externe ou sans IA: %s", mission_id, objective)
            return "guarded"

        has_sensitive = any(zone in normalized for zone in SENSITIVE_ZONES)
        has_non_destructive = any(marker in normalized for marker in NON_DESTRUCTIVE_MARKERS)

        # Certains préfixes sont historiquement des missions d'audit/plan
        is_safe_prefix = any(mission_id.startswith(prefix) for prefix in SAFE_MISSION_PREFIXES)

        if has_sensitive and not has_non_destructive and not is_safe_prefix:
            return "forbidden"

        if has_sensitive:
            return "guarded"

        return "safe"

    def _create_mission(self, candidate: Dict[str, Any]) -> bool:
        """Crée la mission dans mission_store via son endpoint HTTP local."""
        mission_id = candidate["mission_id"]
        objective = candidate["objective"]
        expected_final_status = candidate.get("expected_final_status", "needs_audit")

        mission_context = {
            "objective": objective,
            "priority": "normal",
            "role": "operator",
            "source": "next_mission_planner",
            "expected_final_status": expected_final_status,
            "auto_next": False,  # évite la boucle infinie
            "created_by": "LunaAgentSupervisor",
            "forbidden_actions": [
                "push",
                "merge",
                "reset_hard",
                "real_sms",
                "real_call",
                "production_deploy",
                "secret_modification",
                "cloud_modification",
                "user_data_deletion",
                "install_debug",
                "build_debug",
            ],
        }

        payload = {
            "mission_id": mission_id,
            "task_id": mission_id,
            "status": "queued",
            "current_role": "operator",
            "next_role": "operator",
            "iteration": 0,
            "max_iterations": 1,
            "approval_required": False,
            "budget_allowed": True,
            "mission_context_json": mission_context,
        }

        try:
            response = requests.post(self.mission_store_url, json=payload, timeout=10)
            if response.status_code != 200:
                logger.warning("Creation mission %s HTTP %s: %s", mission_id, response.status_code, response.text)
                return False
            body = response.json()
            if body.get("status") != "queued":
                logger.warning("Creation mission %s reponse inattendue: %s", mission_id, body)
                return False
            logger.info("Mission suivante creee: %s", mission_id)
            return True
        except Exception as e:
            logger.warning("Echec creation mission %s: %s", mission_id, e)
            return False

    def write_report(self, result: Dict[str, Any]) -> Path:
        """Écrit le rapport du planificateur dans AGENT_SHARED."""
        self.agent_shared.mkdir(parents=True, exist_ok=True)
        mission_id = result.get("next_mission_id") or "NEXT-MISSION"
        report_path = self.agent_shared / f"{mission_id}_PLAN.md"

        lines = [
            f"# Plan de prochaine mission : {mission_id}",
            "",
            f"- **Date** : {datetime.now(timezone.utc).isoformat()}",
            f"- **Mission proposee** : {mission_id}",
            f"- **Objectif** : {result.get('objective') or 'N/A'}",
            f"- **Niveau de risque** : {result.get('risk_level') or 'N/A'}",
            f"- **Auto-creee** : {result.get('auto_created', False)}",
            f"- **Statut planificateur** : {result.get('planner_status')}",
            f"- **Raison** : {result.get('reason')}",
            "",
            "## Garde-fous appliques",
            "",
            "- Aucune mission contenant un mot interdit n'est proposee.\n"
            "- Les missions touchant Guardian/APK/Cloud sans marqueur 'audit/lecture/non destructif' sont refusees.\n"
            "- Les missions sensibles mais non destructives sont proposees avec validation humaine requise.\n"
            "- La creation automatique n'a lieu que si auto_next=true.\n",
            "",
        ]

        report_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Rapport planificateur cree: %s", report_path)
        return report_path
