"""Gouverneur dur de budget pour les appels aux agents IA.

Charge une politique versionnee (config/agent_budget_policy.yaml), persiste les
compteurs quotidiens et mensuels, et tient un ledger de chaque appel.
Aucun agent ne peut modifier ses propres limites : elles proviennent uniquement
de la politique.
"""

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

logger = logging.getLogger(__name__)

DEFAULT_POLICY_PATH = "config/agent_budget_policy.yaml"


class BudgetGovernor:
    """Controle strict du nombre d'appels IA par jour, par mission et par agent."""

    def __init__(
        self,
        config: Dict[str, Any],
        policy_path: Optional[str] = None,
    ):
        self.config = config
        self.project_path = Path(config.get("PROJECT_PATH", ".")).resolve()
        self.policy_path = Path(policy_path or DEFAULT_POLICY_PATH)
        if not self.policy_path.is_absolute():
            self.policy_path = self.project_path / self.policy_path

        self.policy = self._load_policy()
        self._apply_policy_overrides()

        self.budget_file = Path(config.get("BUDGET_FILE", "runs/supervisor-budget.json"))
        if not self.budget_file.is_absolute():
            self.budget_file = self.project_path / self.budget_file
        self.budget_file.parent.mkdir(parents=True, exist_ok=True)

        self.ledger_file = Path(self.policy.get("ledger", {}).get("file", "runs/ai-budget-ledger.json"))
        if not self.ledger_file.is_absolute():
            self.ledger_file = self.project_path / self.ledger_file
        self.ledger_file.parent.mkdir(parents=True, exist_ok=True)

        self._data = self._load_budget()
        self._today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._this_month = datetime.now(timezone.utc).strftime("%Y-%m")
        self._reset_if_new_day()

    # ------------------------------------------------------------------
    # Chargement politique
    # ------------------------------------------------------------------
    def _load_policy(self) -> Dict[str, Any]:
        if yaml is None:
            logger.warning("PyYAML non disponible. Politique par defaut utilisee.")
            return self._default_policy()
        if not self.policy_path.exists():
            logger.warning("Politique de budget absente: %s. Defaut utilise.", self.policy_path)
            return self._default_policy()
        try:
            with open(self.policy_path, "r", encoding="utf-8") as f:
                policy = yaml.safe_load(f) or {}
            logger.info("Politique de budget chargee: %s", self.policy_path)
            return policy
        except Exception as e:
            logger.warning("Impossible de charger la politique: %s. Defaut utilise.", e)
            return self._default_policy()

    @staticmethod
    def _default_policy() -> Dict[str, Any]:
        return {
            "poll_interval_seconds": 1800,
            "max_parallel_missions": 1,
            "max_iterations_per_mission": 3,
            "max_same_error_attempts": 2,
            "max_total_ai_calls_per_day": 6,
            "max_total_ai_calls_per_mission": 8,
            "providers": {
                "kimi": {"enabled": True, "max_calls_per_day": 4, "max_calls_per_mission": 5, "role": "operator"},
                "deepseek": {"enabled": True, "max_calls_per_day": 1, "max_calls_per_mission": 1, "role": "auditor"},
                "codex": {"enabled_if_configured": True, "max_calls_per_day": 1, "max_calls_per_mission": 1, "role": "coordinator"},
                "review": {"max_calls_per_day": 1, "max_calls_per_mission": 1, "role": "reviewer"},
                "n8n_ai": {"enabled": False, "max_calls_per_day": 0, "max_calls_per_mission": 0, "role": "none"},
            },
            "thresholds": {"log_only": 0.50, "block_non_essential": 0.75, "kimi_only": 0.90, "exhausted": 1.00},
            "context": {
                "max_characters": 6000,
                "max_log_lines": 200,
                "max_diff_characters": 8000,
                "send_full_repository": False,
                "send_full_logcat": False,
                "screenshots_only_when_changed": True,
            },
            "ledger": {"file": "runs/ai-budget-ledger.json", "max_entries": 10000},
            "reporting": {"daily_report_dir": "runs/daily-reports", "morning_report_enabled": True},
        }

    def _apply_policy_overrides(self) -> None:
        """Surcharge legere par variables d'environnement si presentes."""
        for key in ("MAX_TOTAL_AI_CALLS_PER_DAY", "MAX_TOTAL_AI_CALLS_PER_MISSION"):
            env_val = self.config.get(key)
            if env_val is not None:
                policy_key = key.replace("MAX_", "max_").lower()
                self.policy[policy_key] = int(env_val)

    # ------------------------------------------------------------------
    # Persistance budget
    # ------------------------------------------------------------------
    def _load_budget(self) -> Dict[str, Any]:
        if self.budget_file.exists():
            try:
                with open(self.budget_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Impossible de charger le budget: %s", e)
        return {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "month": datetime.now(timezone.utc).strftime("%Y-%m"),
            "daily": {},
            "monthly": {},
            "missions": {},
        }

    def _save_budget(self) -> None:
        try:
            with open(self.budget_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning("Impossible de sauvegarder le budget: %s", e)

    def _reset_if_new_day(self) -> None:
        if self._data.get("date") != self._today:
            self._data = {
                "date": self._today,
                "month": self._this_month,
                "daily": {},
                "monthly": self._data.get("monthly", {}),
                "missions": {},
            }
            if self._data.get("month") != self._this_month:
                self._data["monthly"] = {}
                self._data["month"] = self._this_month
            self._save_budget()

    # ------------------------------------------------------------------
    # Helpers limites
    # ------------------------------------------------------------------
    def _provider_policy(self, agent: str) -> Dict[str, Any]:
        return self.policy.get("providers", {}).get(agent.lower(), {})

    def _provider_enabled(self, agent: str) -> bool:
        pol = self._provider_policy(agent)
        name = agent.lower()
        if name == "n8n_ai":
            return False
        if pol.get("enabled") is False:
            return False
        if pol.get("enabled_if_configured"):
            # Pour codex/openai, on verifie que la CLI/api est reellement configuree
            if name == "codex":
                return bool(shutil.which("codex"))
            if name in ("openai", "codex"):
                return bool(self.config.get("OPENAI_API_KEY"))
        return True

    def _daily_limit(self, agent: str) -> int:
        pol = self._provider_policy(agent)
        return int(pol.get("max_calls_per_day", 0))

    def _mission_limit(self, agent: str) -> int:
        pol = self._provider_policy(agent)
        return int(pol.get("max_calls_per_mission", 0))

    def _total_today(self) -> int:
        return sum(self._data.get("daily", {}).values())

    def _usage_ratio(self) -> float:
        limit = int(self.policy.get("max_total_ai_calls_per_day", 1))
        if limit <= 0:
            return 0.0
        return self._total_today() / limit

    def _threshold(self, name: str) -> float:
        return float(self.policy.get("thresholds", {}).get(name, 1.0))

    # ------------------------------------------------------------------
    # Gouverneur public
    # ------------------------------------------------------------------
    def can_call(
        self,
        agent: str,
        mission_id: str,
        reason: str = "",
    ) -> Tuple[bool, str]:
        """Verifie si un appel a un agent est autorise."""
        agent_key = agent.lower()

        # 1. Provider active
        if not self._provider_enabled(agent_key):
            return False, f"provider_{agent_key}_desactive"

        # 2. Budget global epuise
        ratio = self._usage_ratio()
        if ratio >= self._threshold("exhausted"):
            return False, "budget_global_journalier_epuise"

        # 3. Limites journalieres de l'agent
        daily_used = self._data.get("daily", {}).get(agent_key, 0)
        daily_limit = self._daily_limit(agent_key)
        if daily_limit > 0 and daily_used >= daily_limit:
            return False, f"budget_{agent_key}_journalier_atteint"

        # 4. Limites par mission
        mission = self._data.setdefault("missions", {}).setdefault(mission_id, {})
        mission_used = mission.get(agent_key, 0)
        mission_limit = self._mission_limit(agent_key)
        if mission_limit > 0 and mission_used >= mission_limit:
            return False, f"budget_{agent_key}_mission_atteint"

        # 5. Limite totale par mission
        mission_total = sum(v for k, v in mission.items() if k != "errors")
        if mission_total >= int(self.policy.get("max_total_ai_calls_per_mission", 8)):
            return False, "budget_total_mission_atteint"

        # 6. Seuils progressifs
        if ratio >= self._threshold("kimi_only") and agent_key != "kimi":
            return False, "seuil_kimi_only"
        if ratio >= self._threshold("block_non_essential") and agent_key not in ("kimi",):
            return False, "seuil_block_non_essential"
        if ratio >= self._threshold("log_only"):
            logger.info("Seuil 50%% atteint: appel %s journalise mais autorise", agent_key)

        return True, ""

    def record_call(
        self,
        agent: str,
        mission_id: str,
        reason: str = "",
        context_size: int = 0,
        duration_ms: Optional[int] = None,
        success: bool = True,
        result_summary: str = "",
    ) -> None:
        """Enregistre un appel dans le budget et le ledger."""
        agent_key = agent.lower()
        daily = self._data.setdefault("daily", {})
        mission = self._data.setdefault("missions", {}).setdefault(mission_id, {})

        before_daily = daily.get(agent_key, 0)
        before_mission = mission.get(agent_key, 0)

        daily[agent_key] = before_daily + 1
        mission[agent_key] = before_mission + 1

        monthly = self._data.setdefault("monthly", {})
        monthly[agent_key] = monthly.get(agent_key, 0) + 1

        self._save_budget()
        self._append_ledger(
            agent=agent_key,
            mission_id=mission_id,
            reason=reason,
            context_size=context_size,
            duration_ms=duration_ms,
            success=success,
            result_summary=result_summary,
            counters_before={"daily": before_daily, "mission": before_mission},
            counters_after={"daily": before_daily + 1, "mission": before_mission + 1},
        )

    def same_error_count(self, mission_id: str, error_signature: str) -> int:
        errors = (
            self._data.setdefault("missions", {})
            .setdefault(mission_id, {})
            .setdefault("errors", {})
        )
        return errors.get(error_signature, 0)

    def record_error(self, mission_id: str, error_signature: str) -> None:
        errors = (
            self._data.setdefault("missions", {})
            .setdefault(mission_id, {})
            .setdefault("errors", {})
        )
        errors[error_signature] = errors.get(error_signature, 0) + 1
        self._save_budget()

    def status(self) -> Dict[str, Any]:
        ratio = self._usage_ratio()
        thresholds = self.policy.get("thresholds", {})
        return {
            "date": self._today,
            "month": self._this_month,
            "daily": self._data.get("daily", {}),
            "monthly": self._data.get("monthly", {}),
            "missions": self._data.get("missions", {}),
            "total_today": self._total_today(),
            "max_total_per_day": int(self.policy.get("max_total_ai_calls_per_day", 6)),
            "usage_ratio": ratio,
            "thresholds": thresholds,
            "governor_state": self._governor_state(ratio, thresholds),
        }

    def _governor_state(self, ratio: float, thresholds: Dict[str, float]) -> str:
        if ratio >= float(thresholds.get("exhausted", 1.0)):
            return "exhausted"
        if ratio >= float(thresholds.get("kimi_only", 0.90)):
            return "kimi_only"
        if ratio >= float(thresholds.get("block_non_essential", 0.75)):
            return "block_non_essential"
        if ratio >= float(thresholds.get("log_only", 0.50)):
            return "log_only"
        return "normal"

    # ------------------------------------------------------------------
    # Ledger
    # ------------------------------------------------------------------
    def _append_ledger(self, **entry: Any) -> None:
        entry["timestamp"] = datetime.now(timezone.utc).isoformat()
        entries: List[Dict[str, Any]] = []
        if self.ledger_file.exists():
            try:
                with open(self.ledger_file, "r", encoding="utf-8") as f:
                    entries = json.load(f)
            except Exception:
                entries = []
        entries.append(entry)
        max_entries = int(self.policy.get("ledger", {}).get("max_entries", 10000))
        if len(entries) > max_entries:
            entries = entries[-max_entries:]
        try:
            with open(self.ledger_file, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning("Impossible d'ecrire le ledger: %s", e)

    def ledger(self) -> List[Dict[str, Any]]:
        if not self.ledger_file.exists():
            return []
        try:
            with open(self.ledger_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []


# Compatibilite ascendante : Budget est un alias de BudgetGovernor.
Budget = BudgetGovernor
