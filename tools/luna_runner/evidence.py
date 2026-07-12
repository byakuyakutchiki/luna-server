"""Gestion des dossiers de preuves pour chaque exécution."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List


class EvidenceCollector:
    def __init__(self, runs_dir: Path, mission_id: str):
        self.mission_id = mission_id
        self.run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self.base = Path(runs_dir) / mission_id / self.run_id
        self.base.mkdir(parents=True, exist_ok=True)
        self.log_path = self.base / "runner.log"
        self._log("INFO", f"Evidence directory: {self.base}")

    def path(self, name: str) -> Path:
        return self.base / name

    def _log(self, level: str, message: str) -> None:
        ts = datetime.utcnow().isoformat()
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {level}: {message}\n")

    def info(self, message: str) -> None:
        self._log("INFO", message)

    def error(self, message: str) -> None:
        self._log("ERROR", message)

    def write(self, filename: str, content: str) -> Path:
        target = self.base / filename
        target.write_text(content, encoding="utf-8")
        self.info(f"Wrote {filename} ({len(content)} chars)")
        return target

    def write_json(self, filename: str, data: Dict) -> Path:
        target = self.base / filename
        target.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        self.info(f"Wrote {filename}")
        return target

    def write_bytes(self, filename: str, content: bytes) -> Path:
        target = self.base / filename
        target.write_bytes(content)
        self.info(f"Wrote {filename} ({len(content)} bytes)")
        return target

    @staticmethod
    def extract_errors(logcat: str) -> str:
        """Extrait les lignes d'erreur et d'exception d'un logcat."""
        error_patterns = [
            r"E\s+.*",
            r"FATAL.*",
            r"Exception.*",
            r"Error:.*",
            r"CRASH.*",
        ]
        lines = logcat.splitlines()
        errors = []
        for line in lines:
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in error_patterns):
                errors.append(line)
        return "\n".join(errors[:500])

    @staticmethod
    def sanitize(text: str) -> str:
        """Redige les secrets avant archivage."""
        # API keys OpenAI-like
        text = re.sub(r"sk-[a-zA-Z0-9]{20,}", "***OPENAI_KEY_REDACTED***", text)
        # JWT
        text = re.sub(
            r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
            "***JWT_REDACTED***",
            text,
        )
        # Hex longs
        text = re.sub(r"[0-9a-fA-F]{64,}", "***HEX_REDACTED***", text)
        # Mots de passe/cles generiques
        text = re.sub(
            r"(api[_-]?key|token|password|secret|credential|private_key)\s*[:=]\s*[^\s\"']+",
            r"\1=***REDACTED***",
            text,
            flags=re.IGNORECASE,
        )
        return text
