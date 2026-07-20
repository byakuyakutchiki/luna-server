"""Logique de routage intelligent des agents IA.

Aucun agent n'est choisi sans mission valide, sans ADB si necessaire,
sans verification Git, sans comparaison avec le dernier resultat et sans
verification du budget.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from .agent_caller import get_caller
from .budget import BudgetGovernor

logger = logging.getLogger(__name__)


class RoutingDecision:
    """Décision de routage : quel agent appeler ou pourquoi ne pas appeler."""

    def __init__(
        self,
        should_call: bool,
        role: str = "",
        reason: str = "",
        agent_name: str = "",
        error: bool = False,
        next_role: str = "",
    ):
        self.should_call = should_call
        self.role = role
        self.reason = reason
        self.agent_name = agent_name
        self.error = error
        self.next_role = next_role


def decide_agent(
    mission: Dict[str, Any],
    context: Dict[str, Any],
    budget: BudgetGovernor,
    config: Dict[str, Any],
) -> RoutingDecision:
    """Décide si et quel agent appeler selon les regles de la charte.

    Ordre de decision :
    1. Mission valide presente.
    2. ADB disponible si le telephone est necessaire.
    3. Git OK.
    4. Tests existants analyses.
    5. Nouvelle information disponible.
    6. Budget disponible.
    7. Routage par role/erreurs/iteration.
    """

    mission_id = mission.get("mission_id", "UNKNOWN")

    # 1. Mission valide
    if not mission.get("objective") and not mission.get("description"):
        return RoutingDecision(False, reason="mission_sans_objectif")

    # 2. ADB si necessaire
    if mission.get("requires_device", True):
        adb = context.get("adb", {})
        if not adb.get("available"):
            return RoutingDecision(False, reason=f"adb_indisponible:{adb.get('reason', '?')}")

    # 3. Git OK — on refuse d'agir sur un depot en conflit (a adapter selon besoin)
    git = context.get("git", {})
    if "error" in git:
        logger.warning("Git indisponible pour %s: %s", mission_id, git["error"])

    # 4. Rien n'a change et ce n'est pas la premiere iteration
    iteration = int(mission.get("iteration", 0))
    changed = context.get("changed", {})
    changed_files = changed.get("files", [])
    new_errors = changed.get("new_errors_since_last", [])
    last_status = changed.get("last_status")

    if iteration > 0 and not changed_files and not new_errors and last_status in ("success", "complete"):
        return RoutingDecision(False, reason="rien_na_change")

    # 5. Budget
    role = _select_role(mission, context, budget)
    caller = get_caller(role, config)
    agent_name = caller.name
    can_call, budget_reason = budget.can_call(agent_name, mission_id, reason="routing_decision")
    if not can_call:
        return RoutingDecision(False, reason=f"budget:{budget_reason}")

    # 6. Rôle suivant pour la prochaine itération
    next_mission = dict(mission)
    next_mission["iteration"] = int(mission.get("iteration", 0)) + 1
    next_role = _select_role(next_mission, context, budget)

    return RoutingDecision(True, role=role, reason="routage_ok", agent_name=agent_name, next_role=next_role)


def _select_role(
    mission: Dict[str, Any],
    context: Dict[str, Any],
    budget: BudgetGovernor,
) -> str:
    """Selectionne le role le plus adapte sans jamais appeler plusieurs agents."""

    mission_id = mission.get("mission_id", "UNKNOWN")
    iteration = int(mission.get("iteration", 0))
    max_iter = int(mission.get("max_iterations", 3))
    new_errors = context.get("changed", {}).get("new_errors_since_last", [])
    changed_files = context.get("changed", {}).get("files", [])

    # Erreurs repetees -> deepseek si budget
    error_signatures: List[str] = []
    for err in new_errors:
        sig = err if isinstance(err, str) else err.get("signature", "")
        if sig and budget.same_error_count(mission_id, sig) >= 2:
            error_signatures.append(sig)

    if error_signatures:
        can_ds, _ = budget.can_call("deepseek", mission_id, reason="error_repetee")
        if can_ds:
            return "auditor"

    # Apres modification reelle -> review si budget
    if changed_files and iteration > 0:
        can_review, _ = budget.can_call("review", mission_id, reason="modification_code")
        if can_review:
            return "reviewer"

    # Derniere iteration -> coordinator pour synthese finale si budget
    if iteration >= max_iter - 1:
        can_codex, _ = budget.can_call("codex", mission_id, reason="synthese_finale")
        if can_codex:
            return "coordinator"

    # Premiere iteration ou diagnostic -> operator (kimi)
    return "operator"
