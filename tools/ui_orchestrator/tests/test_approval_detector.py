#!/usr/bin/env python3
"""Tests unitaires de l'approval detector."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from approval_detector import ApprovalDetector, ApprovalRequest
from policy import Policy


def make_detector() -> ApprovalDetector:
    policy = Policy(
        allowed_actions=[
            "git status",
            "git diff",
            "git log",
            "pytest",
            "python3 -m pytest",
        ],
        forbidden_patterns=[
            "git reset --hard",
            "git clean -fd",
            "git push origin main",
            "git push main",
            "gcloud run deploy",
            "deploy production",
            "rm -rf",
            "real_sms",
            "real_call",
        ],
        require_human_for=["sudo", "git push", "deploy", "adb install"],
    )
    return ApprovalDetector(policy)


def _req(action: str, buttons=None, source="kimi", window_role="terminal") -> ApprovalRequest:
    return ApprovalRequest(
        source=source,
        window_role=window_role,
        prompt_text="Run this command?",
        action_text=action,
        buttons=buttons or ["Approve once", "Approve for session", "Reject"],
    )


def test_git_status_approved():
    d = make_detector()
    dec = d.detect(_req("cd /home/ludo/luna-server && git status --short"))
    assert dec.would_approve is True
    assert dec.risk_level == "low"
    assert dec.target_button == "Approve once"
    print("TEST OK: git status approuvé")


def test_pytest_approved():
    d = make_detector()
    dec = d.detect(_req("pytest"))
    assert dec.would_approve is True
    assert dec.risk_level == "low"
    print("TEST OK: pytest approuvé")


def test_rg_approved():
    d = make_detector()
    dec = d.detect(_req('rg "Guardian" static/guardian.html'))
    assert dec.would_approve is True
    assert dec.action_type == "read"
    print("TEST OK: rg approuvé")


def test_git_diff_approved():
    d = make_detector()
    dec = d.detect(_req("git diff --stat"))
    assert dec.would_approve is True
    assert dec.action_type == "git_diff"
    print("TEST OK: git diff approuvé")


def test_git_push_blocked():
    d = make_detector()
    dec = d.detect(_req("git push origin main"))
    assert dec.would_approve is False
    assert dec.requires_human is True
    assert dec.risk_level == "high"
    print("TEST OK: git push bloqué")


def test_gcloud_deploy_blocked():
    d = make_detector()
    dec = d.detect(_req("gcloud run deploy luna-beta"))
    assert dec.would_approve is False
    assert dec.requires_human is True
    assert dec.action_type == "deploy"
    print("TEST OK: gcloud deploy bloqué")


def test_rm_rf_blocked():
    d = make_detector()
    dec = d.detect(_req("rm -rf /home/ludo/luna-server"))
    assert dec.would_approve is False
    assert dec.requires_human is True
    assert dec.action_type == "rm"
    print("TEST OK: rm -rf bloqué")


def test_git_reset_hard_blocked():
    d = make_detector()
    dec = d.detect(_req("git reset --hard"))
    assert dec.would_approve is False
    assert dec.requires_human is True
    assert dec.action_type == "git_reset"
    print("TEST OK: git reset --hard bloqué")


def test_git_clean_fd_blocked():
    d = make_detector()
    dec = d.detect(_req("git clean -fd"))
    assert dec.would_approve is False
    assert dec.requires_human is True
    assert dec.action_type == "git_clean"
    print("TEST OK: git clean -fd bloqué")


def test_adb_human_review():
    d = make_detector()
    dec = d.detect(_req("adb shell input tap 100 200"))
    assert dec.would_approve is False
    assert dec.requires_human is True
    assert dec.action_type == "adb"
    print("TEST OK: adb review humain")


def test_empty_action_human():
    d = make_detector()
    dec = d.detect(_req(""))
    assert dec.would_approve is False
    assert dec.requires_human is True
    print("TEST OK: action vide review humain")


def test_unknown_window_human():
    d = make_detector()
    dec = d.detect(_req("git status --short", window_role="unknown"))
    assert dec.would_approve is False
    assert dec.requires_human is True
    print("TEST OK: fenêtre unknown review humain")


def test_session_only_button_human():
    d = make_detector()
    dec = d.detect(_req("git status --short", buttons=["Approve for session", "Reject"]))
    assert dec.would_approve is False
    assert dec.requires_human is True
    assert "Approve for session" in dec.reason
    print("TEST OK: Approve for session seul review humain")


def test_secret_blocked():
    d = make_detector()
    dec = d.detect(_req("export OPENAI_API_KEY=sk-12345678901234567890abcdef"))
    assert dec.would_approve is False
    assert dec.requires_human is True
    assert dec.action_type == "secret"
    print("TEST OK: secret bloqué")


if __name__ == "__main__":
    test_git_status_approved()
    test_pytest_approved()
    test_rg_approved()
    test_git_diff_approved()
    test_git_push_blocked()
    test_gcloud_deploy_blocked()
    test_rm_rf_blocked()
    test_git_reset_hard_blocked()
    test_git_clean_fd_blocked()
    test_adb_human_review()
    test_empty_action_human()
    test_unknown_window_human()
    test_session_only_button_human()
    test_secret_blocked()
    print("\nTous les tests approval_detector sont OK.")
