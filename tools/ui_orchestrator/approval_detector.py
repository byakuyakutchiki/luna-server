"""Détection et décision simulée des demandes d'approbation.

Mode simulation V0/V1 : aucun clic réel, aucun auto-approve réel.
Ce module analyse une description de demande d'approbation et décide si
l'action demandée pourrait être approuvée automatiquement dans un futur
système, ou si un humain doit valider.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from policy import ApprovalDecision as PolicyDecision
from policy import Policy


@dataclass
class ApprovalRequest:
    source: str
    window_role: str
    prompt_text: str
    action_text: str
    buttons: List[str] = field(default_factory=list)


@dataclass
class ApprovalDecision:
    approval_detected: bool
    action_text: str
    action_type: str
    risk_level: str
    would_approve: bool
    requires_human: bool
    target_button: Optional[str]
    reason: str


class ApprovalDetector:
    """Détecte une demande d'approbation et prend une décision simulée."""

    LOW_RISK_ACTION_TYPES = {"read", "test", "git_status", "git_diff", "git_log"}
    MEDIUM_RISK_ACTION_TYPES = {"git_other", "adb", "shell"}
    HIGH_RISK_ACTION_TYPES = {"deploy", "git_push", "git_reset", "git_clean", "rm", "sudo"}
    CRITICAL_RISK_ACTION_TYPES = {"secret", "real_sms", "real_call", "payment"}

    def __init__(self, policy: Policy):
        self.policy = policy

    def detect(self, request: ApprovalRequest) -> ApprovalDecision:
        action_text = (request.action_text or "").strip()
        approval_detected = bool(action_text)

        action_type = self._classify_action_type(action_text)
        policy_decision = self.policy.evaluate(action_text)
        risk_level = self._compute_risk_level(action_type, action_text, policy_decision)

        is_session_only = self._is_approve_for_session_only(request.buttons)
        is_unknown_source = request.source.lower() not in {"kimi", "codex"}
        is_unknown_window = request.window_role == "unknown"

        would_approve = False
        target_button = None
        reason_parts: List[str] = []

        if not approval_detected:
            reason_parts.append("Aucune action détectée")
        elif risk_level in ("high", "critical") or policy_decision.requires_human:
            reason_parts.append(f"Action à haut risque ou interdite : {policy_decision.reason}")
        elif action_type == "unknown":
            reason_parts.append("Type d'action inconnu")
        elif is_session_only:
            reason_parts.append("Bouton 'Approve for session' seul : validation humaine requise")
        elif is_unknown_source or is_unknown_window:
            reason_parts.append("Source ou fenêtre inconnue")
        else:
            would_approve = True
            target_button = self._find_approve_once_button(request.buttons)
            reason_parts.append("Action sûre et lecture seule")

        requires_human = not would_approve

        return ApprovalDecision(
            approval_detected=approval_detected,
            action_text=action_text,
            action_type=action_type,
            risk_level=risk_level,
            would_approve=would_approve,
            requires_human=requires_human,
            target_button=target_button,
            reason="; ".join(reason_parts),
        )

    @staticmethod
    def _classify_single_command(command: str) -> str:
        lowered = command.strip()
        if not lowered:
            return "unknown"

        # Secrets / tokens
        if re.search(r"\bsk-[a-z0-9]{20,}\b", lowered) or re.search(
            r"\b(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^\s'\"]+", lowered
        ):
            return "secret"

        # Git commands
        if lowered.startswith("git "):
            match = re.search(r"\bgit\s+(status|diff|log)\b", lowered)
            if match:
                return f"git_{match.group(1)}"
            if "push" in lowered:
                return "git_push"
            if "reset" in lowered and "--hard" in lowered:
                return "git_reset"
            if "clean" in lowered and "-fd" in lowered:
                return "git_clean"
            return "git_other"

        # ADB
        if lowered.startswith("adb "):
            return "adb"

        # Tests
        if lowered.startswith("pytest") or lowered.startswith("python3 -m pytest"):
            return "test"

        # Read-only commands
        read_prefixes = ("ls ", "find ", "head ", "tail ", "sed ", "cat ", "rg ", "grep ", "echo ")
        if lowered.startswith(read_prefixes):
            return "read"

        # Deploy / cloud
        if "deploy" in lowered or lowered.startswith("gcloud "):
            return "deploy"

        # Dangerous shell
        if "rm -rf" in lowered:
            return "rm"
        if "sudo" in lowered:
            return "sudo"

        # cd seul est considéré comme neutre/informatif
        if lowered.startswith("cd "):
            return "cd"

        return "unknown"

    @classmethod
    def _classify_action_type(cls, action_text: str) -> str:
        lowered = action_text.lower().strip()
        if not lowered:
            return "unknown"

        # Sépare les commandes composées (cd ... && git status)
        parts = re.split(r"\s*&&\s*|\s*;\s*", lowered)
        classifications = [cls._classify_single_command(part) for part in parts]

        # Ordre de priorité : plus dangereux d'abord
        priority = [
            "secret", "rm", "sudo", "deploy", "git_push", "git_reset", "git_clean",
            "adb", "git_other", "test", "git_status", "git_diff", "git_log",
            "read", "shell", "cd", "unknown",
        ]
        for risk_type in priority:
            if risk_type in classifications:
                return risk_type
        return "unknown"

    def _compute_risk_level(
        self,
        action_type: str,
        action_text: str,
        policy_decision: PolicyDecision,
    ) -> str:
        if action_type in self.CRITICAL_RISK_ACTION_TYPES:
            return "critical"
        if action_type in self.HIGH_RISK_ACTION_TYPES:
            return "high"
        if action_type in self.MEDIUM_RISK_ACTION_TYPES:
            return "medium"
        if action_type in self.LOW_RISK_ACTION_TYPES:
            return "low"
        if policy_decision.requires_human or not policy_decision.allowed:
            return "high"
        return "unknown"

    @staticmethod
    def _is_approve_for_session_only(buttons: List[str]) -> bool:
        lowered = [b.lower() for b in buttons]
        has_session = any("session" in b for b in lowered)
        has_once = any("once" in b or "approve" in b and "session" not in b for b in lowered)
        return has_session and not has_once

    @staticmethod
    def _find_approve_once_button(buttons: List[str]) -> Optional[str]:
        for button in buttons:
            lowered = button.lower()
            if "once" in lowered or ("approve" in lowered and "session" not in lowered):
                return button
        return None
