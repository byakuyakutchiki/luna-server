"""Détection visuelle simulée des demandes d’approbation.

Mode simulation V0/V1 : aucune capture d’écran réelle ni clic n’est effectué
sous Linux. Ce module accepte des données OCR structurées (texte + bounding
boxes) et en déduit :
- le texte de la demande (prompt) ;
- l’action demandée ;
- les boutons disponibles (Approve once, Approve for session, Reject, etc.) ;
- une `ApprovalRequest` prête à être passée à `ApprovalDetector`.

Un script PowerShell Windows (`windows_capture_probe.ps1`) est fourni pour
produire de vraies captures + OCR côté Windows, sans jamais cliquer ni changer
le focus.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from approval_detector import ApprovalRequest


@dataclass
class BoundingBox:
    x: int
    y: int
    width: int
    height: int


@dataclass
class OcrWord:
    """Mot ou ligne issu d’un OCR, avec texte et bounding box optionnelle."""

    text: str
    bbox: Optional[BoundingBox] = None
    confidence: Optional[float] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OcrWord":
        bbox = None
        raw_bbox = data.get("bbox")
        if raw_bbox:
            bbox = BoundingBox(
                x=int(raw_bbox.get("x", 0)),
                y=int(raw_bbox.get("y", 0)),
                width=int(raw_bbox.get("width", 0)),
                height=int(raw_bbox.get("height", 0)),
            )
        return cls(
            text=str(data.get("text", "")),
            bbox=bbox,
            confidence=data.get("confidence"),
        )


@dataclass
class DetectedButton:
    label: str
    button_type: str
    bbox: Optional[BoundingBox] = None


@dataclass
class VisionResult:
    approval_detected: bool
    prompt_text: str
    action_text: str
    detected_buttons: List[DetectedButton] = field(default_factory=list)
    source: str = "unknown"
    window_role: str = "unknown"
    reason: str = ""

    def to_approval_request(self) -> ApprovalRequest:
        return ApprovalRequest(
            source=self.source,
            window_role=self.window_role,
            prompt_text=self.prompt_text,
            action_text=self.action_text,
            buttons=[b.label for b in self.detected_buttons],
        )


class ApprovalVision:
    """Analyse une capture/ocr d’écran pour détecter une demande d’approbation."""

    APPROVE_ONCE_RE = re.compile(r"(?i)\bapprove\s*once\b|approuver\s*une\s*fois")
    APPROVE_SESSION_RE = re.compile(
        r"(?i)\bapprove\s*for\s*session\b|approuver\s*pour\s*la\s*session"
    )
    REJECT_RE = re.compile(r"(?i)\breject\b|refuser|annuler")
    GENERIC_APPROVE_RE = re.compile(r"(?i)\bapprove\b|approuver")

    ACTION_PROMPTS_RE = re.compile(
        r"(?i)(run\s*this\s*command\?|write\s*file\?|"
        r"exécuter\s*cette\s*commande\?|écrire\s*le\s*fichier\?)"
    )

    def __init__(self, ocr_words: Optional[List[OcrWord]] = None):
        self.ocr_words = list(ocr_words or [])

    @classmethod
    def from_text(cls, text: str) -> "ApprovalVision":
        """Construit une vision à partir d’un texte brut (simulation)."""
        words = [OcrWord(text=line.strip()) for line in text.splitlines() if line.strip()]
        return cls(ocr_words=words)

    @classmethod
    def from_ocr_json(cls, data: List[Dict[str, Any]]) -> "ApprovalVision":
        words = [OcrWord.from_dict(item) for item in data]
        return cls(ocr_words=words)

    def _full_text(self) -> str:
        return "\n".join(w.text for w in self.ocr_words)

    @staticmethod
    def _detect_button_type(label: str) -> Optional[str]:
        lowered = label.lower()
        if re.search(r"approve\s*once|une\s*fois", lowered):
            return "approve_once"
        if re.search(r"approve\s*for\s*session|pour\s*la\s*session", lowered):
            return "approve_session"
        if re.search(r"reject|refuser|annuler", lowered):
            return "reject"
        if re.search(r"approve|approuver", lowered):
            return "approve_generic"
        return None

    def detect_buttons(self) -> List[DetectedButton]:
        """Détecte les boutons d’approbation dans le texte OCR.

        Une même ligne OCR peut contenir plusieurs boutons séparés par des
        espaces multiples ou des tabulations (cas fréquent sur une capture UI).
        """
        buttons: List[DetectedButton] = []
        for word in self.ocr_words:
            # Sépare plusieurs boutons sur une même ligne
            candidates = re.split(r"\s{2,}|\t+", word.text.strip())
            for candidate in candidates:
                candidate = candidate.strip()
                if not candidate:
                    continue
                btype = self._detect_button_type(candidate)
                if btype:
                    buttons.append(
                        DetectedButton(
                            label=candidate,
                            button_type=btype,
                            bbox=word.bbox,
                        )
                    )
        return buttons

    def _extract_prompt_text(self, full_text: str) -> str:
        match = self.ACTION_PROMPTS_RE.search(full_text)
        if match:
            return match.group(1)
        return ""

    @staticmethod
    def _is_meaningful_action(candidate: str) -> bool:
        """Filtre les faux positifs OCR (chiffres isolés, fragments trop courts)."""
        if len(candidate) < 3:
            return False
        if not any(c.isalpha() for c in candidate):
            return False
        return True

    def _extract_action_text(self, full_text: str) -> str:
        """Extrait l’action demandée du texte OCR.

        Heuristiques (ordre de priorité) :
        1. ligne juste après un prompt "Run this command?" / "Write file?" ;
        2. ligne après un prompt $ ou > ;
        3. première ligne non vide qui n’est pas un bouton ni un prompt.
        """
        lines = [line.strip() for line in full_text.splitlines() if line.strip()]

        # 1. Ligne suivant un prompt connu
        for i, line in enumerate(lines):
            if self.ACTION_PROMPTS_RE.search(line) and i + 1 < len(lines):
                candidate = lines[i + 1]
                if not self._detect_button_type(candidate) and self._is_meaningful_action(candidate):
                    return candidate

        # 2. Ligne de terminal $ / >
        for line in lines:
            m = re.match(r"^[^\w]*[\$\>\#]\s*(.+)$", line)
            if m:
                candidate = m.group(1).strip()
                if self._is_meaningful_action(candidate):
                    return candidate

        # 3. Première ligne qui n’est ni bouton ni prompt et qui a du sens
        for line in lines:
            if self._detect_button_type(line):
                continue
            if self.ACTION_PROMPTS_RE.search(line):
                continue
            if self._is_meaningful_action(line):
                return line

        return ""

    def detect(
        self,
        source: str = "unknown",
        window_role: str = "unknown",
    ) -> VisionResult:
        full_text = self._full_text()
        prompt_text = self._extract_prompt_text(full_text)
        detected_buttons = self.detect_buttons()
        action_text = self._extract_action_text(full_text)

        # Une UI d’approbation crédible nécessite au moins un bouton ET un
        # contexte (prompt, action explicite, ou bouton explicite comme
        # "Approve once" / "Reject"). Sinon c’est probablement un faux positif
        # (mot isolé "approve" dans une conversation).
        explicit_button_types = {"approve_once", "approve_session", "reject"}
        has_explicit_button = any(
            b.button_type in explicit_button_types for b in detected_buttons
        )
        # On exige un prompt d’approbation ou un bouton explicite. L’action
        # seule ne suffit pas, car l’OCR peut extraire du code/texte voisin.
        has_clear_context = bool(prompt_text) or has_explicit_button
        approval_detected = bool(detected_buttons) and has_clear_context

        reason_parts: List[str] = []
        if not detected_buttons:
            reason_parts.append("Aucun bouton d’approbation détecté")
        elif detected_buttons and not has_clear_context:
            reason_parts.append(
                "Boutons trouvés mais sans contexte d’approbation clair"
            )
        elif approval_detected and not action_text:
            reason_parts.append("Texte d’action illisible")
        elif approval_detected and action_text:
            button_types = {b.button_type for b in detected_buttons}
            reason_parts.append(
                f"Boutons détectés : {', '.join(sorted(button_types))}"
            )

        return VisionResult(
            approval_detected=approval_detected,
            prompt_text=prompt_text,
            action_text=action_text,
            detected_buttons=detected_buttons,
            source=source,
            window_role=window_role,
            reason="; ".join(reason_parts),
        )
