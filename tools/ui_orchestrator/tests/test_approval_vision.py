#!/usr/bin/env python3
"""Tests unitaires de la détection visuelle/simulée des approbations."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from approval_detector import ApprovalDetector
from approval_vision import ApprovalVision
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
            "rm -rf",
            "real_sms",
            "real_call",
        ],
        require_human_for=["sudo", "git push", "deploy", "adb install"],
    )
    return ApprovalDetector(policy)


def _screen(text: str, source: str = "kimi", window_role: str = "terminal"):
    vision = ApprovalVision.from_text(text)
    return vision.detect(source=source, window_role=window_role)


def test_approve_once_detected():
    text = """Run this command?
git status --short
Approve once   Approve for session   Reject"""
    result = _screen(text)
    assert result.approval_detected is True
    assert any(b.button_type == "approve_once" for b in result.detected_buttons)
    assert result.action_text == "git status --short"

    detector = make_detector()
    decision = detector.detect(result.to_approval_request())
    assert decision.would_approve is True
    assert decision.requires_human is False
    assert decision.target_button == "Approve once"
    print("TEST OK: Approve once détecté et approuvé")


def test_session_button_human_review():
    text = """Run this command?
git status --short
Approve for session   Reject"""
    result = _screen(text)
    assert result.approval_detected is True
    assert any(b.button_type == "approve_session" for b in result.detected_buttons)

    detector = make_detector()
    decision = detector.detect(result.to_approval_request())
    assert decision.would_approve is False
    assert decision.requires_human is True
    assert "Approve for session" in decision.reason
    print("TEST OK: Approve for session détecté et bloqué pour humain")


def test_reject_detected():
    text = """Write file?
tools/ui_orchestrator/approval_vision.py
Approve once   Reject"""
    result = _screen(text)
    assert result.approval_detected is True
    assert any(b.button_type == "reject" for b in result.detected_buttons)
    assert "approval_vision.py" in result.action_text
    print("TEST OK: Reject détecté")


def test_no_button_no_approval():
    text = """Summary of changes
git diff --stat
No action required."""
    result = _screen(text)
    assert result.approval_detected is False
    assert len(result.detected_buttons) == 0
    print("TEST OK: Aucun bouton → pas d’approbation détectée")


def test_unreadable_action_human_review():
    text = """Run this command?
Approve once   Reject"""
    result = _screen(text)
    assert result.approval_detected is True
    assert result.action_text == ""

    detector = make_detector()
    decision = detector.detect(result.to_approval_request())
    assert decision.would_approve is False
    assert decision.requires_human is True
    print("TEST OK: action illisible → review humain")


def test_ocr_json_input():
    data = [
        {"text": "Run this command?", "bbox": {"x": 10, "y": 10, "width": 120, "height": 20}},
        {"text": "pytest", "bbox": {"x": 10, "y": 40, "width": 50, "height": 20}},
        {"text": "Approve once", "bbox": {"x": 10, "y": 70, "width": 80, "height": 25}},
    ]
    vision = ApprovalVision.from_ocr_json(data)
    result = vision.detect(source="codex", window_role="codex")
    assert result.approval_detected is True
    assert result.action_text == "pytest"
    assert result.detected_buttons[0].bbox is not None
    assert result.detected_buttons[0].bbox.x == 10
    print("TEST OK: entrée OCR JSON structurée")


if __name__ == "__main__":
    test_approve_once_detected()
    test_session_button_human_review()
    test_reject_detected()
    test_no_button_no_approval()
    test_unreadable_action_human_review()
    test_ocr_json_input()
    print("\nTous les tests approval_vision sont OK.")
