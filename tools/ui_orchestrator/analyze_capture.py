"""Analyse d’une capture d’écran Windows vers une décision d’approbation.

Mode V0 : aucun clic réel. L’analyseur peut utiliser Tesseract (pytesseract)
s’il est disponible, sinon il retourne un résultat prudent demandant une
validation humaine.
"""

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from approval_detector import ApprovalDetector, ApprovalDecision
from approval_vision import ApprovalVision, OcrWord


class OcrBackend:
    """Backend OCR optionnel basé sur pytesseract/Tesseract."""

    @classmethod
    def is_available(cls) -> bool:
        try:
            import pytesseract  # noqa: F401
        except Exception:
            return False
        return shutil.which("tesseract") is not None

    @classmethod
    def extract_words(cls, image_path: str) -> List[OcrWord]:
        """Extrait les mots d’une image sous forme de liste d’OcrWord."""
        if not cls.is_available():
            return []

        import pytesseract
        from PIL import Image

        img = Image.open(image_path)
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

        words: List[OcrWord] = []
        n = len(data["text"])
        for i in range(n):
            text = data["text"][i].strip()
            conf = int(data.get("conf", [0] * n)[i])
            if not text or conf <= 0:
                continue
            bbox = {
                "x": int(data["left"][i]),
                "y": int(data["top"][i]),
                "width": int(data["width"][i]),
                "height": int(data["height"][i]),
            }
            words.append(OcrWord.from_dict({"text": text, "bbox": bbox, "confidence": conf}))
        return words


@dataclass
class CaptureAnalysis:
    mission_id: str
    image_path: str
    ocr_available: bool
    word_count: int
    approval_detected: bool
    prompt_text: str
    action_text: str
    buttons: List[str]
    would_approve: Optional[bool]
    requires_human: Optional[bool]
    risk_level: Optional[str]
    reason: str
    final_status: str
    decision_reason: Optional[str] = None
    target_button: Optional[str] = None
    simulate: bool = True
    real_click: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "image_path": self.image_path,
            "ocr_available": self.ocr_available,
            "word_count": self.word_count,
            "approval_detected": self.approval_detected,
            "prompt_text": self.prompt_text,
            "action_text": self.action_text,
            "buttons": self.buttons,
            "would_approve": self.would_approve,
            "requires_human": self.requires_human,
            "risk_level": self.risk_level,
            "reason": self.reason,
            "final_status": self.final_status,
            "decision_reason": self.decision_reason,
            "target_button": self.target_button,
            "simulate": self.simulate,
            "real_click": self.real_click,
        }


class CaptureAnalyzer:
    """Analyse une capture et en déduit une décision d’approbation simulée."""

    def __init__(self, policy, detector: Optional[ApprovalDetector] = None):
        from policy import Policy

        if isinstance(policy, Policy):
            self.detector = detector or ApprovalDetector(policy)
        else:
            self.detector = detector or ApprovalDetector(policy)

    def analyze(
        self,
        image_path: str,
        mission_id: str,
        source: str = "codex",
        window_role: str = "codex",
    ) -> CaptureAnalysis:
        path = Path(image_path)
        if not path.exists():
            return CaptureAnalysis(
                mission_id=mission_id,
                image_path=str(image_path),
                ocr_available=False,
                word_count=0,
                approval_detected=False,
                prompt_text="",
                action_text="",
                buttons=[],
                would_approve=None,
                requires_human=True,
                risk_level="unknown",
                reason="Fichier capture introuvable",
                final_status="HUMAN_REVIEW_REQUIRED",
            )

        ocr_available = OcrBackend.is_available()
        words: List[OcrWord] = []
        if ocr_available:
            try:
                words = OcrBackend.extract_words(str(path))
            except Exception as exc:
                ocr_available = False
                reason = f"OCR indisponible ou en échec : {exc}"
                return CaptureAnalysis(
                    mission_id=mission_id,
                    image_path=str(path),
                    ocr_available=False,
                    word_count=0,
                    approval_detected=False,
                    prompt_text="",
                    action_text="",
                    buttons=[],
                    would_approve=None,
                    requires_human=True,
                    risk_level="unknown",
                    reason=reason,
                    final_status="OCR_UNAVAILABLE_HUMAN_REVIEW",
                )

        vision = ApprovalVision(ocr_words=words)
        vision_result = vision.detect(source=source, window_role=window_role)

        decision: Optional[ApprovalDecision] = None
        if vision_result.approval_detected:
            decision = self.detector.detect(vision_result.to_approval_request())

        if not ocr_available:
            final_status = "OCR_UNAVAILABLE_HUMAN_REVIEW"
            reason = "OCR indisponible : validation humaine requise"
        elif not vision_result.approval_detected:
            final_status = "NO_APPROVAL_UI"
            reason = vision_result.reason or "Aucune UI d’approbation détectée"
        elif decision and decision.would_approve:
            final_status = "WOULD_APPROVE"
            reason = decision.reason
        else:
            final_status = "HUMAN_REVIEW_REQUIRED"
            reason = decision.reason if decision else "Contexte d’approbation non sûr"

        return CaptureAnalysis(
            mission_id=mission_id,
            image_path=str(path),
            ocr_available=ocr_available,
            word_count=len(words),
            approval_detected=vision_result.approval_detected,
            prompt_text=vision_result.prompt_text,
            action_text=vision_result.action_text,
            buttons=[b.button_type for b in vision_result.detected_buttons],
            would_approve=decision.would_approve if decision else None,
            requires_human=decision.requires_human if decision else True,
            risk_level=decision.risk_level if decision else "unknown",
            reason=reason,
            final_status=final_status,
            decision_reason=decision.reason if decision else None,
            target_button=decision.target_button if decision else None,
        )

    def analyze_from_text(
        self,
        text: str,
        mission_id: str,
        source: str = "kimi",
        window_role: str = "terminal",
    ) -> CaptureAnalysis:
        """Analyse directement un texte simulé (utile pour les tests)."""
        vision = ApprovalVision.from_text(text)
        vision_result = vision.detect(source=source, window_role=window_role)

        decision: Optional[ApprovalDecision] = None
        if vision_result.approval_detected:
            decision = self.detector.detect(vision_result.to_approval_request())

        if not vision_result.approval_detected:
            final_status = "NO_APPROVAL_UI"
            reason = vision_result.reason or "Aucune UI d’approbation détectée"
        elif decision and decision.would_approve:
            final_status = "WOULD_APPROVE"
            reason = decision.reason
        else:
            final_status = "HUMAN_REVIEW_REQUIRED"
            reason = decision.reason if decision else "Contexte d’approbation non sûr"

        return CaptureAnalysis(
            mission_id=mission_id,
            image_path="",
            ocr_available=True,
            word_count=len(text.split()),
            approval_detected=vision_result.approval_detected,
            prompt_text=vision_result.prompt_text,
            action_text=vision_result.action_text,
            buttons=[b.button_type for b in vision_result.detected_buttons],
            would_approve=decision.would_approve if decision else None,
            requires_human=decision.requires_human if decision else True,
            risk_level=decision.risk_level if decision else "unknown",
            reason=reason,
            final_status=final_status,
            decision_reason=decision.reason if decision else None,
            target_button=decision.target_button if decision else None,
        )
