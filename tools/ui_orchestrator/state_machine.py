"""Machine à états minimaliste de luna-ui-orchestrator.

Mode simulation V0 : aucun clic, aucun envoi réel.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional


# États obligatoires de la V0.
VALID_STATES = {
    "WAITING_FOR_KIMI",
    "KIMI_APPROVAL_REQUIRED",
    "KIMI_RUNNING",
    "KIMI_RESPONSE_READY",
    "COPYING_KIMI_RESPONSE",
    "SWITCHING_TO_CODEX",
    "SENDING_TO_CODEX",
    "CODEX_APPROVAL_REQUIRED",
    "CODEX_RUNNING",
    "CODEX_RESPONSE_READY",
    "COPYING_CODEX_RESPONSE",
    "SWITCHING_TO_KIMI",
    "SENDING_TO_KIMI",
    "MISSION_VALIDATED",
    "READY_FOR_HUMAN_PRODUCTION_APPROVAL",
    "PAUSED",
    "ERROR",
    "HUMAN_REVIEW_REQUIRED",
}


@dataclass
class Transition:
    state_from: str
    state_to: str
    event: str
    timestamp: str
    payload: Dict[str, Any] = field(default_factory=dict)


class StateMachineError(Exception):
    pass


class StateMachine:
    """Machine à états simple avec log de transitions."""

    def __init__(
        self,
        initial_state: str = "WAITING_FOR_KIMI",
        terminal_states: Optional[List[str]] = None,
        on_transition: Optional[Callable[[Transition], None]] = None,
    ):
        if initial_state not in VALID_STATES:
            raise StateMachineError(f"État initial invalide: {initial_state}")
        self._state = initial_state
        self._terminal_states = set(terminal_states or ["MISSION_VALIDATED", "PAUSED", "ERROR", "HUMAN_REVIEW_REQUIRED"])
        self._history: List[Transition] = []
        self._on_transition = on_transition

    @property
    def state(self) -> str:
        return self._state

    def is_terminal(self) -> bool:
        return self._state in self._terminal_states

    def transition(self, event: str, state_to: str, payload: Optional[Dict[str, Any]] = None) -> Transition:
        if state_to not in VALID_STATES:
            raise StateMachineError(f"État cible invalide: {state_to}")
        if self.is_terminal():
            raise StateMachineError(f"Transition impossible depuis un état terminal: {self._state}")

        transition = Transition(
            state_from=self._state,
            state_to=state_to,
            event=event,
            timestamp=datetime.now(timezone.utc).isoformat(),
            payload=payload or {},
        )
        self._state = state_to
        self._history.append(transition)
        if self._on_transition:
            self._on_transition(transition)
        return transition

    def history(self) -> List[Transition]:
        return list(self._history)
