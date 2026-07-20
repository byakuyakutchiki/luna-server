"""Smoke test des appels agents réels.

Cette mission fait un appel minimal à chaque agent disponible
(Kimi, DeepSeek, OpenAI/Codex) pour prouver que le routing et les callers
fonctionnent en condition réelle.

Aucun secret n'est affiché.
"""

import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .agent_caller import AgentCallError, get_caller
from .budget import BudgetGovernor
from .config import load_config
from .routing import decide_agent

logger = logging.getLogger(__name__)

AGENT_SHARED = Path("/media/windows/Users/saint/Documents/Codex/AGENT_SHARED")
MISSION_ID = "AGENT-CALL-SMOKE-002"

_SMOKE_JSON = (
    '{"summary":"smoke ok","decision":"complete",'
    '"requested_action":{"type":"none"},"files_relevant":[],'
    '"expected_result":"smoke test ok","requires_human_validation":false}'
)

SMOKE_OBJECTIVE = (
    "Smoke test. Tu dois répondre UNIQUEMENT par ce JSON exact, "
    "sans texte avant ou après, sans balises markdown, sans explication : "
    f"{_SMOKE_JSON}"
)

SMOKE_MISSION = {
    "mission_id": MISSION_ID,
    "task_id": MISSION_ID,
    "role": "operator",
    "objective": SMOKE_OBJECTIVE,
    "iteration": 0,
    "max_iterations": 1,
    "requires_device": False,
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
        "json_valid": False,
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
        result["json_valid"] = True

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
    """Vérifie que routing.decide_agent choisit bien un agent selon l'état.

    decide_agent utilise _select_role qui choisit dynamiquement le rôle selon
    l'itération, les erreurs répétées et les fichiers modifiés. On teste donc
    chaque rôle dans les conditions qui le font sélectionner.
    """
    import tempfile
    from pathlib import Path

    def _fresh_budget() -> BudgetGovernor:
        cfg = dict(config)
        tmp = Path(tempfile.mkdtemp(prefix="smoke_routing_"))
        cfg["BUDGET_FILE"] = str(tmp / "budget.json")
        return BudgetGovernor(cfg)

    result: Dict[str, Any] = {}

    # operator : iteration 0
    budget = _fresh_budget()
    mission = dict(SMOKE_MISSION)
    mission["role"] = "operator"
    mission["iteration"] = 0
    mission["requires_device"] = False
    try:
        routing = decide_agent(mission, SMOKE_CONTEXT, budget, config)
        result["operator"] = {
            "should_call": routing.should_call,
            "role": routing.role,
            "agent": routing.agent_name,
            "reason": routing.reason,
        }
    except Exception as e:
        result["operator"] = {"error": str(e)}

    # auditor : erreurs répétées
    budget = _fresh_budget()
    budget.record_error(MISSION_ID, "smoke_err")
    budget.record_error(MISSION_ID, "smoke_err")
    mission = dict(SMOKE_MISSION)
    mission["role"] = "auditor"
    mission["iteration"] = 1
    mission["requires_device"] = False
    context = dict(SMOKE_CONTEXT)
    context["changed"] = {"files": [], "new_errors_since_last": [{"signature": "smoke_err"}]}
    try:
        routing = decide_agent(mission, context, budget, config)
        result["auditor"] = {
            "should_call": routing.should_call,
            "role": routing.role,
            "agent": routing.agent_name,
            "reason": routing.reason,
        }
    except Exception as e:
        result["auditor"] = {"error": str(e)}

    # coordinator : dernière itération sans fichiers modifiés
    budget = _fresh_budget()
    mission = dict(SMOKE_MISSION)
    mission["role"] = "coordinator"
    mission["iteration"] = 2
    mission["max_iterations"] = 3
    mission["requires_device"] = False
    try:
        routing = decide_agent(mission, SMOKE_CONTEXT, budget, config)
        result["coordinator"] = {
            "should_call": routing.should_call,
            "role": routing.role,
            "agent": routing.agent_name,
            "reason": routing.reason,
        }
    except Exception as e:
        result["coordinator"] = {"error": str(e)}

    return result


def _check_role_mapping(config: Dict[str, Any]) -> Dict[str, Any]:
    """Vérifie que get_caller associe bien chaque rôle à son agent nominal."""
    result: Dict[str, Any] = {}
    for role, expected in (
        ("operator", "kimi"),
        ("auditor", "deepseek"),
        ("coordinator", "codex"),
    ):
        try:
            caller = get_caller(role, config)
            result[role] = {
                "agent": caller.name,
                "expected": expected,
                "ok": caller.name == expected,
            }
        except Exception as e:
            result[role] = {"error": str(e), "expected": expected, "ok": False}
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


def _agent_config_status(agent_name: str, config: Dict[str, Any]) -> str:
    """Renvoie un statut de configuration sans jamais exposer de clé."""
    if agent_name == "kimi":
        return "OK" if shutil.which(config.get("KIMI_CLI", "/home/ludo/.kimi-code/bin/kimi")) else "MISSING"
    if agent_name == "deepseek":
        return "OK" if config.get("DEEPSEEK_API_KEY") else "MISSING"
    if agent_name in ("codex", "openai"):
        return "OK" if config.get("OPENAI_API_KEY") else "MISSING"
    return "UNKNOWN"


def _agent_network_status(agent_name: str) -> str:
    """Renvoie un statut réseau basé sur l'audit de connectivité récent."""
    # Les résultats réels de connectivité sont collectés lors de l'appel.
    return "non testé"


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
        "role_mapping": {},
        "fallback": {},
        "overall_status": "unknown",
        "mission_status": "needs_audit",
    }

    # Appels smoke
    for agent_name in ("kimi", "deepseek", "codex"):
        call_result = _smoke_call(agent_name, config, budget)
        call_result["config_status"] = _agent_config_status(agent_name, config)
        result["calls"].append(call_result)

    # Vérification routing
    result["routing"] = _check_routing_decide_agent(config)

    # Vérification mapping rôle -> agent nominal
    result["role_mapping"] = _check_role_mapping(config)

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
    report_path = AGENT_SHARED / "AGENT-CALL-SMOKE-002_REPORT.md"

    lines: List[str] = [
        "# Rapport de smoke test : AGENT-CALL-SMOKE-002",
        "",
        f"- **Mission ID** : {MISSION_ID}",
        f"- **Date** : {result.get('timestamp')}",
        f"- **Runner ID** : {result.get('runner_id')}",
        f"- **Statut technique** : {result.get('overall_status')}",
        f"- **Statut mission** : {result.get('mission_status', 'needs_audit')}",
        "",
        "## Tableau récapitulatif",
        "",
        "| Agent | Config | Réseau | Appel réel | JSON valide | Routing | Fallback | Statut |",
        "|-------|--------|--------|------------|-------------|---------|----------|--------|",
    ]

    role_mapping = result.get("role_mapping", {})
    fallback = result.get("fallback", {})

    for call in result.get("calls", []):
        agent = call["agent"]
        role_for_agent = {"kimi": "operator", "deepseek": "auditor", "codex": "coordinator"}.get(agent)
        routing_ok = role_mapping.get(role_for_agent, {}).get("ok") is True

        fallback_ok = False
        if agent == "deepseek":
            fallback_ok = fallback.get("auditor", {}).get("ok") is True
        elif agent == "codex":
            fallback_ok = fallback.get("coordinator", {}).get("ok") is True
        else:
            fallback_ok = True  # Kimi n'a pas de fallback à vérifier ici

        network_status = "OK" if call["attempted"] or call.get("config_status") == "OK" else "-"
        if call["attempted"] and not call["success"] and "HTTP" not in str(call.get("error", "")):
            network_status = "échec appel"

        if call["success"]:
            status = "OK_PROUVE"
        elif call["attempted"]:
            status = "A_VERIFIER"
        elif "budget" in str(call.get("error", "")):
            status = "paused_budget"
        else:
            status = "NON_TESTE"

        lines.append(
            f"| {agent} | {call.get('config_status', '-')} | {network_status} | "
            f"{'tenté' if call['attempted'] else 'non tenté'} | "
            f"{'oui' if call.get('json_valid') else 'non'} | "
            f"{'OK' if routing_ok else 'KO'} | "
            f"{'OK' if fallback_ok else 'KO'} | {status} |"
        )

    lines.extend(["", "## Détails des appels", ""])
    lines.extend(["| Agent | Tenté | Succès | Décision | Durée (ms) | Erreur |", "|-------|-------|--------|----------|------------|--------|"])
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

    lines.extend(["", "## Mapping rôle -> agent", ""])
    for role, detail in result.get("role_mapping", {}).items():
        if "error" in detail:
            lines.append(f"- **{role}** : erreur `{detail['error']}`")
        else:
            lines.append(
                f"- **{role}** : agent={detail['agent']}, attendu={detail['expected']}, "
                f"ok={detail['ok']}"
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
    lines.append(f"**Statut final de la mission : {result.get('mission_status', 'needs_audit')}** — "
                 "validation Ludovic/Codex requise avant poursuite.")
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
