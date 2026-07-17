"""Generation automatique du rapport du matin.

Ne consomme aucun appel IA. S'appuie uniquement sur le ledger local,
le budget, l'etat Git et ADB.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from luna_runner.actions import GitActions

from .budget import BudgetGovernor

logger = logging.getLogger(__name__)


class MorningReport:
    """Cree le rapport quotidien sans appel IA."""

    def __init__(
        self,
        config: Dict[str, Any],
        budget: Optional[BudgetGovernor] = None,
    ):
        self.config = config
        self.project_path = Path(config.get("PROJECT_PATH", ".")).resolve()
        self.budget = budget or BudgetGovernor(config)
        self.report_dir = Path(config.get("DAILY_REPORT_DIR", "runs/daily-reports"))
        if not self.report_dir.is_absolute():
            self.report_dir = self.project_path / self.report_dir
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, mission_result: Optional[Dict[str, Any]] = None) -> Path:
        """Genere le rapport et retourne son chemin."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = self.report_dir / f"{today}-morning-report.md"

        budget_status = self.budget.status()
        ledger = self.budget.ledger()
        today_ledger = [e for e in ledger if e.get("timestamp", "").startswith(today)]

        lines: List[str] = []
        lines.append(f"# Rapport du matin — {today}")
        lines.append("")
        lines.append(f"- **Heure de generation** : {datetime.now(timezone.utc).isoformat()}")
        lines.append(f"- **Runner** : {self.config.get('RUNNER_ID', 'unknown')}")
        lines.append("")

        # Mission traitee
        lines.append("## Mission traitee")
        if mission_result:
            lines.append(f"- **mission_id** : {mission_result.get('mission_id', 'N/A')}")
            lines.append(f"- **status** : {mission_result.get('status', 'N/A')}")
            lines.append(f"- **resume** : {mission_result.get('summary', 'Aucun')}")
        else:
            lines.append("Aucune mission traitee pendant cette periode.")
        lines.append("")

        # Agents appeles
        lines.append("## Agents appeles")
        if today_ledger:
            for entry in today_ledger:
                lines.append(
                    f"- `{entry.get('agent')}` ({entry.get('mission_id')}) — "
                    f"{entry.get('reason')} — succes={entry.get('success')}"
                )
        else:
            lines.append("Aucun appel IA effectue.")
        lines.append("")

        # Budget
        lines.append("## Budget journalier")
        lines.append(f"- **Total utilise aujourd'hui** : {budget_status.get('total_today', 0)}")
        lines.append(f"- **Plafond journalier** : {budget_status.get('max_total_per_day', 0)}")
        lines.append(f"- **Ratio** : {budget_status.get('usage_ratio', 0):.2%}")
        lines.append(f"- **Etat** : {budget_status.get('governor_state', 'unknown')}")
        lines.append(f"- **Detail** : {json.dumps(budget_status.get('daily', {}), ensure_ascii=False)}")
        lines.append("")

        # Actions effectuees
        lines.append("## Actions effectuees")
        if mission_result:
            action = mission_result.get("action_result", {})
            if action:
                lines.append(f"```json\n{json.dumps(action, indent=2, ensure_ascii=False)}\n```")
            else:
                lines.append("Aucune action executee.")
        else:
            lines.append("Aucune action executee.")
        lines.append("")

        # Fichiers modifies
        lines.append("## Fichiers modifies")
        try:
            git = GitActions(str(self.project_path))
            diff_names = git.status()
            if diff_names.strip():
                lines.append("```")
                lines.append(diff_names[:4000])
                lines.append("```")
            else:
                lines.append("Aucun fichier modifie non commit.")
        except Exception as e:
            lines.append(f"Git indisponible : {e}")
        lines.append("")

        # Compilation
        lines.append("## Etat de compilation")
        build_status = "non teste" if not mission_result else mission_result.get("build_status", "non teste")
        lines.append(f"- {build_status}")
        lines.append("")

        # ADB
        lines.append("## Etat ADB")
        device_id = self.config.get("ANDROID_DEVICE_ID", "")
        lines.append(f"- **device_id** : {device_id}")
        try:
            from luna_runner.actions import ADBActions
            adb = ADBActions(device_id)
            lines.append(f"- **modele** : {adb.getprop('ro.product.model')}")
            lines.append(f"- **android** : {adb.getprop('ro.build.version.release')}")
            lines.append(f"- **etat** : {adb.get_state()}")
        except Exception as e:
            lines.append(f"- **etat** : indisponible ({e})")
        lines.append("")

        # Captures
        lines.append("## Captures produites")
        if mission_result and mission_result.get("evidence_paths"):
            lines.append("```json")
            lines.append(json.dumps(mission_result.get("evidence_paths"), indent=2, ensure_ascii=False))
            lines.append("```")
        else:
            lines.append("Aucune capture produite.")
        lines.append("")

        # Erreurs
        lines.append("## Erreurs rencontrees")
        errors = [e for e in today_ledger if not e.get("success")]
        if errors:
            for e in errors:
                lines.append(f"- `{e.get('agent')}` : {e.get('result_summary', 'erreur')}")
        else:
            lines.append("Aucune erreur enregistree.")
        lines.append("")

        # Decision
        lines.append("## Prochaine action recommandee")
        if budget_status.get("governor_state") == "exhausted":
            lines.append("Budget epuise. Attendre le jour suivant ou demander une validation humaine.")
        elif mission_result and mission_result.get("status") == "waiting_human_approval":
            lines.append("Validation humaine requise avant de poursuivre.")
        elif mission_result and mission_result.get("status") in ("success", "complete"):
            lines.append("Mission terminee. Attendre la prochaine mission.")
        else:
            lines.append("Aucune action couteuse recommandee. Le superviseur reste en attente.")
        lines.append("")

        body = "\n".join(lines)
        path.write_text(body, encoding="utf-8")
        logger.info("Rapport du matin genere: %s", path)
        return path
