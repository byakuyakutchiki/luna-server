"""Détection de fenêtres Windows pour luna-ui-orchestrator.

Mode simulation V0 : aucun clic, aucun changement de focus, aucune lecture
sensible. Ce module ne fait qu'observer et classifier des descripteurs de
fenêtres (titre, processus, handle, bounds).

Depuis la VM Linux, la détection réelle n'est pas disponible : le module
retourne des fenêtres simulées et laisse le script PowerShell
`windows_probe.ps1` pour l'exécution côté Windows.
"""

import json
import logging
import platform
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


logger = logging.getLogger("ui_orchestrator.window_detector")


@dataclass
class WindowInfo:
    title: str
    process_name: str
    handle: Optional[int] = None
    bounds: Optional[Dict[str, int]] = None
    matched_role: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items()}


class WindowDetector:
    """Détecte et classe les fenêtres Windows sans interagir avec elles."""

    def __init__(self, config: Dict[str, Any], shared_dir: str):
        self.config = config.get("window_patterns", {})
        self.shared_dir = Path(shared_dir)
        self._simulation_mode = config.get("orchestrator", {}).get("simulate", True)

    @staticmethod
    def _compile(pattern: str):
        if not pattern:
            return None
        try:
            return re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            logger.warning("Regex invalide '%s': %s", pattern, e)
            return None

    def _match_window(self, window: WindowInfo) -> Optional[str]:
        for role, patterns in self.config.items():
            title_pat = self._compile(patterns.get("title_regex", ""))
            proc_pat = self._compile(patterns.get("process_regex", ""))

            title_match = title_pat and title_pat.search(window.title)
            proc_match = proc_pat and proc_pat.search(window.process_name)

            if title_match or proc_match:
                return role
        return None

    def classify(self, windows: List[WindowInfo]) -> Dict[str, List[WindowInfo]]:
        result: Dict[str, List[WindowInfo]] = {role: [] for role in self.config}
        result["unknown"] = []
        for window in windows:
            role = self._match_window(window)
            window.matched_role = role or "unknown"
            result[window.matched_role].append(window)
        return result

    def _simulated_windows(self) -> List[WindowInfo]:
        """Fenêtres simulées utilisées pour les tests Linux."""
        return [
            WindowInfo(
                title="Codex - Visual Studio Code",
                process_name="Code.exe",
                handle=123456,
                bounds={"left": 0, "top": 0, "right": 1280, "bottom": 720},
            ),
            WindowInfo(
                title="ChatGPT - Google Chrome",
                process_name="chrome.exe",
                handle=123457,
                bounds={"left": 1280, "top": 0, "right": 2560, "bottom": 720},
            ),
            WindowInfo(
                title="Oracle VM VirtualBox Manager",
                process_name="VirtualBox.exe",
                handle=123458,
                bounds={"left": 100, "top": 100, "right": 900, "bottom": 600},
            ),
            WindowInfo(
                title="ludo@luna-vm: ~/luna-server",
                process_name="gnome-terminal-server",
                handle=123459,
                bounds={"left": 200, "top": 200, "right": 1000, "bottom": 700},
            ),
            WindowInfo(
                title="Innocent Calculator",
                process_name="calc.exe",
                handle=123460,
                bounds={"left": 500, "top": 500, "right": 700, "bottom": 700},
            ),
        ]

    def probe_windows(self, simulate: Optional[bool] = None) -> List[WindowInfo]:
        """Retourne la liste des fenêtres visibles.

        Sur Windows et si simulate=False, exécute `windows_probe.ps1`.
        Sur Linux ou si simulate=True, retourne des fenêtres simulées.
        """
        simulate = simulate if simulate is not None else self._simulation_mode

        if simulate or platform.system() != "Windows":
            if platform.system() != "Windows":
                logger.info(
                    "Système détecté : %s. Utilisation de fenêtres simulées. "
                    "Pour une détection réelle, exécuter windows_probe.ps1 côté Windows.",
                    platform.system(),
                )
            else:
                logger.info("Mode simulation : fenêtres simulées.")
            return self._simulated_windows()

        return self._probe_windows_real()

    def _probe_windows_real(self) -> List[WindowInfo]:
        """Exécute le script PowerShell côté Windows et parse le JSON."""
        script_path = Path(__file__).with_suffix("").parent / "windows_probe.ps1"
        if not script_path.exists():
            logger.error("Script PowerShell introuvable : %s", script_path)
            return []

        try:
            result = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script_path),
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            if result.returncode != 0:
                logger.error("windows_probe.ps1 a échoué : %s", result.stderr)
                return []
            data = json.loads(result.stdout)
            return [WindowInfo(**item) for item in data]
        except Exception as e:
            logger.exception("Erreur lors du probe Windows : %s", e)
            return []

    def write_probe_report(
        self,
        mission_id: str,
        windows: List[WindowInfo],
        matched: Dict[str, List[WindowInfo]],
    ) -> Path:
        self.shared_dir.mkdir(parents=True, exist_ok=True)
        state_dir = self.shared_dir / "state"
        state_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        path = state_dir / f"windows_probe_{mission_id}_{timestamp}.json"

        report = {
            "mission_id": mission_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "simulate": platform.system() != "Windows" or self._simulation_mode,
            "real_click": False,
            "real_focus_change": False,
            "window_count": len(windows),
            "windows": [w.to_dict() for w in windows],
            "matched_roles": {
                role: [w.to_dict() for w in wins] for role, wins in matched.items()
            },
        }
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Rapport de probe Windows écrit : %s", path)
        return path
