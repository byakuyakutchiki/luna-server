#!/usr/bin/env python3
"""Tests unitaires de la machine à états."""

import os
import sys

# Ajoute le répertoire parent au path pour importer les modules de l'orchestrateur.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from state_machine import StateMachine, StateMachineError


def test_initial_state():
    sm = StateMachine()
    assert sm.state == "WAITING_FOR_KIMI"
    assert not sm.is_terminal()
    print("TEST OK: état initial WAITING_FOR_KIMI")


def test_valid_transition():
    sm = StateMachine()
    sm.transition("kimi_ready", "KIMI_RESPONSE_READY")
    assert sm.state == "KIMI_RESPONSE_READY"
    print("TEST OK: transition valide")


def test_terminal_state_blocks_transition():
    sm = StateMachine()
    sm.transition("validate", "MISSION_VALIDATED")
    assert sm.is_terminal()
    try:
        sm.transition("bad", "KIMI_RESPONSE_READY")
        raise AssertionError("La transition aurait dû être bloquée")
    except StateMachineError:
        print("TEST OK: état terminal bloque les transitions")


def test_invalid_state():
    try:
        StateMachine(initial_state="UNKNOWN")
        raise AssertionError("État invalide aurait dû être rejeté")
    except StateMachineError:
        print("TEST OK: état invalide rejeté")


def test_history():
    sm = StateMachine()
    sm.transition("a", "KIMI_RESPONSE_READY")
    sm.transition("b", "MISSION_VALIDATED")
    assert len(sm.history()) == 2
    assert sm.history()[0].state_from == "WAITING_FOR_KIMI"
    print("TEST OK: historique des transitions")


if __name__ == "__main__":
    test_initial_state()
    test_valid_transition()
    test_terminal_state_blocks_transition()
    test_invalid_state()
    test_history()
    print("\nTous les tests state_machine sont OK.")
