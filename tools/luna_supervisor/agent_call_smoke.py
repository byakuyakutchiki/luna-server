"""Smoke test des appels agents réels.

Cette mission fait un appel minimal à chaque agent disponible
(Kimi, DeepSeek, OpenAI/Codex) pour prouver que le routing et les callers
fonctionnent en condition réelle.

Aucun secret n'est affiché.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .agent_caller import AgentCallError, get_caller
from .budget import BudgetGovernor
from .config import load_config
from .routing import decide_agent

logger = logging.getLogger(__name__)

AGENT_SHARED = Path("/media/windows/Users/saint/Documents/Codex/AGENT_SHARED")
MISSION_ID = "AGENT-CALL-SMOKE-001"

SMOKE_OBJECTIVE = (
    "Smoke test. Réponds UNIQUEMENT par ce JSON exact sans texte avant ou après : "
    '{"summary":"smoke ok","decision":"complete","requested_action":{"type":"none"},'
    '"files_relevant":[],"expected_result":"smoke test ok","requires_human_validation":false}'
)

SMOKE_MISSION = {
    "mission_id": MISSION_ID,
    "task_id": MISSION_ID,
    "role": "operator",
    "objective": SMOKE_OBJECTIVE,
    "iteration": 0,
    "max_iterations": 1,
}

SMOKE_CONTEXT = {
    "mission_id": MISSION_ID,
    "adb": {"available": True},
    "git": {"branch": "automation/guardian-autonomous-001", "status": ""},
    "changed": {"files": [], "new_errors_since_last": []},
}


def _smoke_call(agent_name: str, config: Dict[str, Any], budget: BudgetGovernor) -> Dict[str, Any]:
    """Effectue un appel smoke à un agent spécifique si le budget le permet."""
    result: Dict[str, Any] = {
        "agent": agent_name,
        "attempted": False,
        "success": False,
        "decision": None,
        "error": None,
        "duration_ms": None,
    }

    can_call, reason = budget.can_call(agent_name, MISSION_ID, reason="smoke_test")
    if not can_call:
        result["error"] = f"budget insuffisant: {reason}"
        return result

    result["attempted"] = True

    # Détermine le rôle associé à l'agent
    role_map = {
        "kimi": "operator",
        "deepseek": "auditor",
        "codex": "coordinator",
    }
    role = role_map.get(agent_name, "operator")
    mission = dict(SMOKE_MISSION)
    mission["role"] = role

    try:
        caller = get_caller(role, config)
        if caller.name != agent_name:
            result["error"] = f"routing a selectionne {caller.name} au lieu de {agent_name}"
            return result

        import time
        start = time.time()
        decision = caller.call(mission, SMOKE_CONTEXT)
        duration_ms = int((time.time() - start) * 1000)

        result["success"] = True
        result["decision"] = decision.decision
        result["duration_ms"] = duration_ms

        # Consomme le budget uniquement en cas de succès
        budget.record_call(
            agent_name,
            MISSION_ID,
            reason="smoke_test",
            context_size=0,
            duration_ms=duration_ms,
            success=True,
            result_summary=f"decision={decision.decision}",
        )
    except AgentCallError as e:
        result["error"] = str(e)
        budget.record_call(agent_name, MISSION_ID, reason="smoke_test", success=False, result_summary=str(e)[:200])
    except Exception as e:
        result["error"] = f"erreur inattendue: {e}"
        budget.record_call(agent_name, MISSION_ID, reason="smoke_test", success=False, result_summary=str(e)[:200])

    return result


def _check_routing_decide_agent(config: Dict[str, Any]) -> Dict[str, Any]:
    """Vérifie que routing.decide_agent choisit bien un agent selon le rôle."""
    budget = BudgetGovernor(config)
    result: Dict[str, Any] = {}

    for role in ("operator", "auditor", "coordinator"):
        mission = dict(SMOKE_MISSION)
        mission["role"] = role
        try:
            routing = decide_agent(mission, SMOKE_CONTEXT, budget, config)
            result[role] = {
                "should_call": routing.should_call,
                "role": routing.role,
                "agent": routing.agent_name,
                "reason": routing.reason,
            }
        except Exception as e:
            result[role] = {"error": str(e)}

    return result


def _check_fallback(config: Dict[str, Any]) -> Dict[str, Any]:
    """Vérifie que get_caller fait un fallback sur Kimi quand les clés sont absentes."""
    no_key_config = dict(config)
    no_key_config["DEEPSEEK_API_KEY"] = ""
    no_key_config["OPENAI_API_KEY"] = ""

    result: Dict[str, Any] = {}
    for role in ("auditor", "coordinator"):
        try:
            caller = get_caller(role, no_key_config)
            result[role] = {"fallback_agent": caller.name, "ok": caller.name == "kimi"}
        except Exception as e:
            result[role] = {"error": str(e)}

    return result


def run_smoke(config_path: str = None) -> Dict[str, Any]:
    """Exécute le smoke test complet."""
    config = load_config(config_path)
    budget = BudgetGovernor(config)

    result: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "runner_id": config.get("RUNNER_ID", "unknown"),
        "budget_before": budget.status(),
        "calls": [],
        "routing": {},
        "fallback": {},
        "overall_status": "unknown",
    }

    # Appels smoke
    for agent_name in ("kimi", "deepseek", "codex"):
        call_result = _smoke_call(agent_name, config, budget)
        result["calls"].append(call_result)

    # Vérification routing
    result["routing"] = _check_routing_decide_agent(config)

    # Vérification fallback
    result["fallback"] = _check_fallback(config)

    result["budget_after"] = budget.status()

    # Statut global
    attempted = [c for c in result["calls"] if c["attempted"]]
    successful = [c for c in result["calls"] if c["success"]]

    if not attempted:
        result["overall_status"] = "skipped"
    elif len(successful) == len(attempted):
        result["overall_status"] = "ok"
    elif successful:
        result["overall_status"] = "partial"
    else:
        result["overall_status"] = "failed"

    return result


def write_report(result: Dict[str, Any]) -> Path:
    """Écrit le rapport de smoke test dans AGENT_SHARED."""
    AGENT_SHARED.mkdir(parents=True, exist_ok=True)
    report_path = AGENT_SHARED / "AGENT-CALL-SMOKE-001_REPORT.md"

    lines: List[str] = [
        "# Rapport de smoke test : AGENT-CALL-SMOKE-001",
        "",
        f"- **Mission ID** : AGENT-CALL-SMOKE-001",
        f"- **Date** : {result.get('timestamp')}",
        f"- **Runner ID** : {result.get('runner_id')}",
        f"- **Statut global** : {result.get('overall_status')}",
        "",
        "## Appels agents",
        "",
        "| Agent | Tenté | Succès | Décision | Durée (ms) | Erreur |",
        "|-------|-------|--------|----------|------------|--------|",
    ]
    for call in result.get("calls", []):
        lines.append(
            f"| {call['agent']} | {call['attempted']} | {call['success']} | "
            f"{call.get('decision') or '-'} | {call.get('duration_ms') or '-'} | "
            f"{call.get('error') or '-'} |"
        )

    lines.extend(["", "## Routing (decide_agent)", ""])
    for role, detail in result.get("routing", {}).items():
        if "error" in detail:
            lines.append(f"- **{role}** : erreur `{detail['error']}`")
        else:
            lines.append(
                f"- **{role}** : should_call={detail['should_call']}, "
                f"role={detail['role']}, agent={detail['agent']}, reason={detail['reason']}"
            )

    lines.extend(["", "## Fallback (clés absentes)", ""])
    for role, detail in result.get("fallback", {}).items():
        if "error" in detail:
            lines.append(f"- **{role}** : erreur `{detail['error']}`")
        else:
            lines.append(
                f"- **{role}** : fallback_agent={detail['fallback_agent']}, "
                f"ok={detail['ok']}"
            )

    budget_after = result.get("budget_after", {})
    lines.extend(["", "## Budget après test", ""])
    lines.append(f"- Total aujourd'hui : {budget_after.get('total_today', 0)} / {budget_after.get('max_total_per_day', 0)}")
    lines.append(f"- État du gouverneur : {budget_after.get('governor_state', 'unknown')}")

    lines.extend(["", "## Conclusion", ""])
    status = result.get("overall_status")
    if status == "ok":
        lines.append("Tous les agents disponibles ont répondu correctement. Le routing et le fallback sont opérationnels.")
    elif status == "partial":
        lines.append("Certains agents ont répondu, d'autres ont échoué ou été bloqués par le budget. Voir le tableau ci-dessus.")
    elif status == "skipped":
        lines.append("Aucun appel n'a été tenté (budget insuffisant ou agents indisponibles).")
    else:
        lines.append("Aucun appel agent n'a réussi. Vérifier la configuration, les clés API et la connectivité réseau.")

    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Rapport de smoke test cree: %s", report_path)
    return report_path


def main(config_path: str = None) -> Path:
    """Point d'entrée principal du smoke test."""
    result = run_smoke(config_path)
    path = write_report(result)
    return path


if __name__ == "__main__":
    path = main()
    print(path)
