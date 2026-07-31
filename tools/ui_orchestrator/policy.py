"""Politique d'approbation de luna-ui-orchestrator.

Mode simulation V0 : aucun clic, aucun envoi réel.
"""

import re
from dataclasses import dataclass
from typing import List


@dataclass
class ApprovalDecision:
    allowed: bool
    reason: str
    requires_human: bool


class Policy:
    """Décide si une action est autorisée, interdite ou nécessite un humain."""

    def __init__(
        self,
        allowed_actions: List[str],
        forbidden_patterns: List[str],
        require_human_for: List[str],
    ):
        self.allowed_actions = [a.lower().strip() for a in allowed_actions]
        self.forbidden_patterns = [p.lower().strip() for p in forbidden_patterns]
        self.require_human_for = [p.lower().strip() for p in require_human_for]

    @classmethod
    def from_config(cls, config: dict) -> "Policy":
        policy_cfg = config.get("policy", {})
        return cls(
            allowed_actions=policy_cfg.get("allowed_actions", []),
            forbidden_patterns=policy_cfg.get("forbidden_patterns", []),
            require_human_for=policy_cfg.get("require_human_for", []),
        )

    def evaluate(self, action: str) -> ApprovalDecision:
        normalized = action.lower().strip()

        # 1. Secrets / API keys (heuristique simple)
        if self._looks_like_secret(normalized):
            return ApprovalDecision(
                allowed=False,
                reason="Secret/API key détecté : action refusée",
                requires_human=True,
            )

        # 2. Patterns interdits
        for pattern in self.forbidden_patterns:
            if pattern in normalized:
                return ApprovalDecision(
                    allowed=False,
                    reason=f"Pattern interdit détecté : {pattern}",
                    requires_human=True,
                )

        # 3. Actions nécessitant un humain
        for pattern in self.require_human_for:
            if pattern in normalized:
                return ApprovalDecision(
                    allowed=False,
                    reason=f"Validation humaine requise pour : {pattern}",
                    requires_human=True,
                )

        # 4. Actions explicitement autorisées
        if normalized in self.allowed_actions:
            return ApprovalDecision(
                allowed=True,
                reason="Action dans la liste blanche",
                requires_human=False,
            )

        # 5. Commandes composées ou simples en lecture seule
        readonly_prefixes = (
            "cd", "ls ", "find ", "head ", "tail ", "cat ", "rg ", "grep ", "echo ",
            "git status", "git diff", "git log",
            "pytest", "python3 -m pytest",
        )
        parts = [p.strip() for p in re.split(r"\s*&&\s*|\s*;\s*", normalized) if p.strip()]
        if all(
            part in self.allowed_actions or any(part.startswith(prefix) for prefix in readonly_prefixes)
            for part in parts
        ):
            return ApprovalDecision(
                allowed=True,
                reason="Commande(s) en lecture seule détectée(s)",
                requires_human=False,
            )

        # 6. Par défaut : inconnu → demander un humain
        return ApprovalDecision(
            allowed=False,
            reason="Action non reconnue, validation humaine requise",
            requires_human=True,
        )

    @staticmethod
    def _looks_like_secret(action: str) -> bool:
        """Heuristique basique pour détecter des secrets dans l'action."""
        secret_patterns = [
            r"\bsk-[a-z0-9]{20,}\b",
            r"\b[a-z0-9_-]*(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^\s'\"]+",
        ]
        for pat in secret_patterns:
            if re.search(pat, action, re.IGNORECASE):
                return True
        return False
