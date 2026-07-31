#!/usr/bin/env python3
"""Tests unitaires de la politique d'approbation."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from policy import Policy


def make_policy() -> Policy:
    return Policy(
        allowed_actions=["git status", "git diff", "git log", "pytest"],
        forbidden_patterns=["git reset --hard", "git clean -fd", "push main", "deploy production", "real_sms", "real_call"],
        require_human_for=["sudo", "rm -rf", "git push", "adb install"],
    )


def test_allowed():
    p = make_policy()
    assert p.evaluate("git status").allowed is True
    assert p.evaluate("git diff").allowed is True
    assert p.evaluate("pytest").allowed is True
    print("TEST OK: actions autorisées")


def test_forbidden():
    p = make_policy()
    assert p.evaluate("git reset --hard").allowed is False
    assert p.evaluate("git clean -fd").allowed is False
    assert p.evaluate("push main").allowed is False
    assert p.evaluate("deploy production").allowed is False
    assert p.evaluate("real_sms").allowed is False
    assert p.evaluate("real_call").allowed is False
    print("TEST OK: actions interdites")


def test_require_human():
    p = make_policy()
    d = p.evaluate("sudo apt update")
    assert d.allowed is False and d.requires_human is True
    d = p.evaluate("git push origin main")
    assert d.allowed is False and d.requires_human is True
    print("TEST OK: validation humaine requise")


def test_unknown_action():
    p = make_policy()
    d = p.evaluate("some random command")
    assert d.allowed is False and d.requires_human is True
    print("TEST OK: action inconnue bloquée")


def test_secret_detection():
    p = make_policy()
    d = p.evaluate("export OPENAI_API_KEY=sk-12345678901234567890abcdef")
    assert d.allowed is False and d.requires_human is True
    print("TEST OK: secret détecté")


if __name__ == "__main__":
    test_allowed()
    test_forbidden()
    test_require_human()
    test_unknown_action()
    test_secret_detection()
    print("\nTous les tests policy sont OK.")
