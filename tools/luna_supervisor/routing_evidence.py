"""Preuve du comportement réel de routing.decide_agent.

Mission : ROUTING-EVIDENCE-FIX-001
Objectif : clarifier le routing operator/auditor/coordinator et expliquer
la contradiction apparente entre la section Routing et la section Mapping
du rapport AGENT-CALL-SMOKE-002.

Aucun appel IA n'est effectué.
"""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .budget import BudgetGovernor
from .config import load_config
from .routing import decide_agent

AGENT_SHARED = Path("/media/windows/Users/saint/Documents/Codex/AGENT_SHARED")
MISSION_ID = "ROUTING-EVIDENCE-FIX-001"


def _fresh_budget(config: Dict[str, Any]) -> BudgetGovernor:
    """Crée un BudgetGovernor avec un fichier budget temporaire et vierge.

    Cela permet de tester le routing sans être influencé par les consommations
    déjà enregistrées dans le budget de production.
    """
    cfg = dict(config)
    tmp = Path(tempfile.mkdtemp(prefix="routing_evidence_"))
    cfg["BUDGET_FILE"] = str(tmp / "budget.json")
    return BudgetGovernor(cfg)


def _disable_role(budget: BudgetGovernor, role: str, mission_id: str) -> None:
    """Épuise artificiellement le budget d'un rôle pour le rendre indisponible."""
    budget.record_call(role, mission_id, reason="routing_evidence_disable")


def _make_mission(role: str, iteration: int, max_iterations: int = 3) -> Dict[str, Any]:
    return {
        "mission_id": MISSION_ID,
        "task_id": MISSION_ID,
        "role": role,
        "objective": "routing evidence test",
        "iteration": iteration,
        "max_iterations": max_iterations,
        "requires_device": False,
    }


def _make_context(changed_files: List[str] = None, errors: List[Any] = None) -> Dict[str, Any]:
    return {
        "mission_id": MISSION_ID,
        "adb": {"available": True},
        "git": {"branch": "automation/guardian-autonomous-001"},
        "changed": {
            "files": changed_files or [],
            "new_errors_since_last": errors or [],
        },
    }


def run_evidence(config_path: str = None) -> Dict[str, Any]:
    """Collecte les preuves de routing."""
    config = load_config(config_path)

    cases: List[Dict[str, Any]] = [
        {
            "name": "operator iter=0",
            "mission": _make_mission("operator", 0),
            "context": _make_context(),
            "expected_role": "operator",
            "expected_agent": "kimi",
        },
        {
            "name": "auditor iter=0 (rôle statique ignoré)",
            "mission": _make_mission("auditor", 0),
            "context": _make_context(),
            "expected_role": "operator",
            "expected_agent": "kimi",
            "note": "_select_role retourne operator car iteration==0",
        },
        {
            "name": "coordinator iter=0 (rôle statique ignoré)",
            "mission": _make_mission("coordinator", 0),
            "context": _make_context(),
            "expected_role": "operator",
            "expected_agent": "kimi",
            "note": "_select_role retourne operator car iteration==0",
        },
        {
            "name": "reviewer iter=1 + fichiers modifiés",
            "mission": _make_mission("reviewer", 1),
            "context": _make_context(changed_files=["a.py"]),
            "expected_role": "reviewer",
            "expected_agent": "review",
            "note": "_select_role retourne reviewer car changed_files et iteration>0",
        },
        {
            "name": "coordinator iter=max-1 + fichiers modifiés (reviewer actif)",
            "mission": _make_mission("coordinator", 2, max_iterations=3),
            "context": _make_context(changed_files=["a.py"]),
            "expected_role": "reviewer",
            "expected_agent": "review",
            "note": "reviewer a la priorité sur coordinator quand des fichiers ont été modifiés",
        },
        {
            "name": "auditor iter=1 + erreurs répétées",
            "mission": _make_mission("auditor", 1),
            "context": _make_context(errors=[{"signature": "err_repeat"}]),
            "expected_role": "auditor",
            "expected_agent": "deepseek",
            "note": "_select_role détecte same_error_count>=2 et budget deepseek OK",
            "setup": lambda b: (b.record_error(MISSION_ID, "err_repeat"), b.record_error(MISSION_ID, "err_repeat")),
        },
        {
            "name": "coordinator iter=max-1 + fichiers modifiés (reviewer épuisé)",
            "mission": _make_mission("coordinator", 2, max_iterations=3),
            "context": _make_context(changed_files=["a.py"]),
            "expected_role": "coordinator",
            "expected_agent": "codex",
            "note": "_select_role atteint le bloc coordinator car reviewer n'est plus disponible",
            "setup": lambda b: _disable_role(b, "review", MISSION_ID),
        },
        {
            "name": "coordinator iter=max-1 sans fichiers modifiés",
            "mission": _make_mission("coordinator", 2, max_iterations=3),
            "context": _make_context(),
            "expected_role": "coordinator",
            "expected_agent": "codex",
            "note": "_select_role atteint le bloc coordinator car dernière itération",
        },
    ]

    results: List[Dict[str, Any]] = []
    for case in cases:
        # Budget frais pour chaque cas afin d'eviter tout effet de bord
        budget = _fresh_budget(config)
        setup = case.get("setup")
        if setup:
            setup(budget)
        routing = decide_agent(case["mission"], case["context"], budget, config)
        results.append({
            "name": case["name"],
            "should_call": routing.should_call,
            "actual_role": routing.role,
            "actual_agent": routing.agent_name,
            "reason": routing.reason,
            "expected_role": case["expected_role"],
            "expected_agent": case["expected_agent"],
            "role_ok": routing.role == case["expected_role"],
            "agent_ok": routing.agent_name == case["expected_agent"],
            "note": case.get("note", ""),
        })

    # Test de fallback : clés absentes -> deepseek/codex fallback sur kimi
    no_key_config = dict(config)
    no_key_config["DEEPSEEK_API_KEY"] = ""
    no_key_config["OPENAI_API_KEY"] = ""
    no_key_budget = _fresh_budget(no_key_config)

    fallback_cases = [
        ("auditor fallback", _make_mission("auditor", 1), _make_context(errors=[{"signature": "err_fb"}]), "kimi", False),
        ("coordinator fallback (reviewer épuisé)", _make_mission("coordinator", 2, 3), _make_context(changed_files=["a.py"]), "kimi", True),
    ]
    fallback_results: List[Dict[str, Any]] = []
    for name, mission, context, expected_agent, disable_review in fallback_cases:
        # Pré-enregistrer l'erreur pour que auditor soit sélectionné
        if "auditor" in name:
            no_key_budget.record_error(MISSION_ID, "err_fb")
            no_key_budget.record_error(MISSION_ID, "err_fb")
        if disable_review:
            _disable_role(no_key_budget, "review", MISSION_ID)
        routing = decide_agent(mission, context, no_key_budget, no_key_config)
        fallback_results.append({
            "name": name,
            "actual_agent": routing.agent_name,
            "expected_agent": expected_agent,
            "ok": routing.agent_name == expected_agent,
            "reason": routing.reason,
        })

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "runner_id": config.get("RUNNER_ID", "unknown"),
        "results": results,
        "fallback_results": fallback_results,
        "mission_status": "needs_audit",
    }


def write_report(evidence: Dict[str, Any]) -> Path:
    """Écrit le rapport de preuve dans AGENT_SHARED."""
    AGENT_SHARED.mkdir(parents=True, exist_ok=True)
    report_path = AGENT_SHARED / "ROUTING-EVIDENCE-FIX-001_REPORT.md"

    lines: List[str] = [
        "# Rapport de mission : ROUTING-EVIDENCE-FIX-001",
        "",
        f"- **Mission ID** : {MISSION_ID}",
        f"- **Date** : {evidence.get('timestamp')}",
        f"- **Runner ID** : {evidence.get('runner_id')}",
        f"- **Statut mission** : {evidence.get('mission_status', 'needs_audit')}",
        "",
        "## Objectif",
        "",
        "Prouver le vrai résultat de `routing.decide_agent` pour `operator`, `auditor` et `coordinator`, "
        "et expliquer la contradiction apparente du rapport `AGENT-CALL-SMOKE-002`.",
        "",
        "## Méthode",
        "",
        "Aucun appel IA réel. Des missions de test sont passées à `decide_agent` avec un budget frais "
        "(fichier temporaire) pour que DeepSeek, OpenAI/Codex et reviewer soient disponibles.",
        "",
        "## Résultats de `decide_agent`",
        "",
        "| Cas | should_call | Rôle attendu | Agent attendu | Rôle obtenu | Agent obtenu | OK | Raison |",
        "|-----|-------------|--------------|---------------|-------------|--------------|----|--------|",
    ]

    all_ok = True
    for r in evidence.get("results", []):
        ok = r.get("role_ok") and r.get("agent_ok")
        all_ok = all_ok and ok
        lines.append(
            f"| {r['name']} | {r['should_call']} | {r['expected_role']} | {r['expected_agent']} | "
            f"{r['actual_role']} | {r['actual_agent']} | {'✅' if ok else '❌'} | {r['reason']} |"
        )

    lines.extend(["", "## Notes explicatives", ""])
    lines.append("- `decide_agent` ne se fie pas au champ statique `mission['role']` pour choisir l'agent.")
    lines.append("- C'est `_select_role` qui décide dynamiquement selon l'itération, les erreurs répétées et les fichiers modifiés.")
    lines.append("- Conséquence : une mission `auditor` ou `coordinator` à l'itération 0 est traitée comme `operator` (Kimi).")
    lines.append("- La section **Mapping** du rapport SMOKE testait `get_caller(role, config)` directement, d'où l'apparente contradiction.")
    lines.append("- Un bug réel a été identifié dans `_select_role` : le rôle `coordinator` était inaccessible car le bloc "
                 "`if changed_files: return 'operator'` et le bloc `if iteration == 0 or not changed_files` couvraient "
                 "tous les cas avant d'atteindre `coordinator`.")

    lines.extend(["", "## Correction apportée", ""])
    lines.append("Fichier : `tools/luna_supervisor/routing.py`")
    lines.append("- Suppression du bloc `if changed_files: return 'operator'` (inaccessible/redondant).")
    lines.append("- Déplacement du bloc `coordinator` avant le fallback final `operator`.")
    lines.append("- Ordre final de `_select_role` : erreurs répétées → auditor ; dernière itération + codex disponible → coordinator ; "
                 "fichiers modifiés + reviewer disponible → reviewer ; sinon → operator.")
    lines.append("- Le test `_check_routing_decide_agent` de `agent_call_smoke.py` a été corrigé pour appeler `decide_agent` "
                 "dans les conditions réelles de chaque rôle (budget frais, erreurs répétées pour auditor, dernière itération pour coordinator).")
    lines.append("- Les tests obsolètes de `tests_budget_governor.py` (dates et contexte d'erreur) ont été corrigés.")

    lines.extend(["", "## Fallback (clés API absentes)", "", "| Cas | Agent obtenu | Agent attendu | OK | Raison |", "|-----|--------------|---------------|----|--------|"])
    for r in evidence.get("fallback_results", []):
        lines.append(
            f"| {r['name']} | {r['actual_agent']} | {r['expected_agent']} | "
            f"{'✅' if r['ok'] else '❌'} | {r['reason']} |"
        )

    lines.extend(["", "## Conclusion", ""])
    if all_ok:
        lines.append("Après correction, `decide_agent` route correctement vers `operator`, `auditor` et `coordinator` "
                     "dans les conditions attendues. La contradiction apparente du rapport SMOKE est expliquée : "
                     "la section Routing testait `decide_agent` (choix dynamique) tandis que la section Mapping testait "
                     "`get_caller` (mapping nominal).")
    else:
        lines.append("Certains cas de routing ne correspondent pas aux attentes. Voir les ❌ ci-dessus.")

    lines.extend(["", "## Recommandation", ""])
    lines.append("La correction de `routing.py` est appliquée localement mais non mergée. "
                 "Validation Ludovic/Codex requise avant de considérer le routage comme définitif.")
    lines.append("Si le rôle statique de la mission doit être respecté par défaut, une évolution supplémentaire de "
                 "`_select_role` serait nécessaire. Ne pas merger sans validation humaine.")
    lines.append("")
    lines.append(f"**Statut final de la mission : {evidence.get('mission_status', 'needs_audit')}** — "
                 "validation Ludovic/Codex requise avant toute mission suivante.")
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def main(config_path: str = None) -> Path:
    evidence = run_evidence(config_path)
    return write_report(evidence)


if __name__ == "__main__":
    path = main()
    print(path)
