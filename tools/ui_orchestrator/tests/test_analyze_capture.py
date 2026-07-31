#!/usr/bin/env python3
"""Tests de l’analyseur de capture vers décision d’approbation."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from analyze_capture import CaptureAnalyzer
from policy import Policy


REAL_CAPTURE = "/media/windows/Users/saint/Documents/Codex/AGENT_SHARED/ui_orchestrator/screenshots/capture_REAL-CAPTURE-FIX-001_20260731-201410.png"


def make_analyzer() -> CaptureAnalyzer:
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
            "rm -rf",
            "real_sms",
            "real_call",
        ],
        require_human_for=["sudo", "git push", "deploy", "adb install"],
    )
    return CaptureAnalyzer(policy)


def test_capture_without_approval():
    a = make_analyzer()
    analysis = a.analyze(
        image_path=REAL_CAPTURE,
        mission_id="TEST-NO-APPROVAL",
        source="codex",
        window_role="codex",
    )
    assert analysis.ocr_available is True
    assert analysis.word_count > 0
    assert analysis.approval_detected is False
    assert analysis.final_status == "NO_APPROVAL_UI"
    assert analysis.requires_human is True
    print("TEST OK: capture réelle sans UI d’approbation")


def test_approve_once_fixture():
    a = make_analyzer()
    text = """Run this command?
cd /home/ludo/luna-server && git status --short
Approve once   Approve for session   Reject"""
    analysis = a.analyze_from_text(
        text=text,
        mission_id="TEST-APPROVE-ONCE",
    )
    assert analysis.approval_detected is True
    assert "approve_once" in analysis.buttons
    assert analysis.final_status == "WOULD_APPROVE"
    assert analysis.would_approve is True
    assert analysis.requires_human is False
    print("TEST OK: fixture Approve once -> would_approve")


def test_session_fixture():
    a = make_analyzer()
    text = """Run this command?
git status --short
Approve for session   Reject"""
    analysis = a.analyze_from_text(
        text=text,
        mission_id="TEST-SESSION",
    )
    assert analysis.approval_detected is True
    assert "approve_session" in analysis.buttons
    assert analysis.final_status == "HUMAN_REVIEW_REQUIRED"
    assert analysis.would_approve is False
    assert analysis.requires_human is True
    print("TEST OK: fixture Approve for session -> human review")


def test_git_push_fixture():
    a = make_analyzer()
    text = """Run this command?
git push origin main
Approve once   Reject"""
    analysis = a.analyze_from_text(
        text=text,
        mission_id="TEST-GIT-PUSH",
    )
    assert analysis.approval_detected is True
    assert analysis.final_status == "HUMAN_REVIEW_REQUIRED"
    assert analysis.would_approve is False
    assert analysis.requires_human is True
    assert analysis.risk_level == "high"
    print("TEST OK: fixture git push -> blocked/human")


def test_ocr_failure_prudent():
    a = make_analyzer()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("not an image")
        tmp_path = f.name
    try:
        analysis = a.analyze(
            image_path=tmp_path,
            mission_id="TEST-OCR-FAIL",
        )
        assert analysis.ocr_available is False
        assert analysis.final_status == "OCR_UNAVAILABLE_HUMAN_REVIEW"
        assert analysis.requires_human is True
        print("TEST OK: OCR en échec -> résultat prudent")
    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    test_capture_without_approval()
    test_approve_once_fixture()
    test_session_fixture()
    test_git_push_fixture()
    test_ocr_failure_prudent()
    print("\nTous les tests analyze_capture sont OK.")
