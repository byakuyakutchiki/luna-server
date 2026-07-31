"""Gestion de l'échange de messages via dossier partagé.

Mode simulation V0 : aucun clic, aucun envoi réel.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class ExchangeManager:
    """Gère les dossiers inbox/outbox/state/logs et l'écriture de messages."""

    def __init__(self, shared_dir: str):
        self.shared_dir = Path(shared_dir)
        self.inbox_dir = self.shared_dir / "inbox"
        self.outbox_dir = self.shared_dir / "outbox"
        self.state_dir = self.shared_dir / "state"
        self.logs_dir = self.shared_dir / "logs"
        self.screenshots_dir = self.shared_dir / "screenshots"
        self.clipboard_dir = self.shared_dir / "clipboard"
        self.config_dir = self.shared_dir / "config"

    def ensure_directories(self) -> None:
        for directory in (
            self.inbox_dir,
            self.outbox_dir,
            self.state_dir,
            self.logs_dir,
            self.screenshots_dir,
            self.clipboard_dir,
            self.config_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def stop_file_exists(self) -> bool:
        return (self.shared_dir / "STOP").exists()

    def write_state(self, state: Dict[str, Any]) -> Path:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        path = self.state_dir / "current_state.json"
        path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def write_message(
        self,
        box: str,
        from_agent: str,
        to_agent: str,
        mission_id: str,
        payload: Dict[str, Any],
    ) -> Path:
        target_dir = self.inbox_dir if box == "inbox" else self.outbox_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        filename = f"{box}/{from_agent}_to_{to_agent}_{mission_id}_{timestamp}.json"
        path = target_dir / f"{from_agent}_to_{to_agent}_{mission_id}_{timestamp}.json"
        envelope = {
            "mission_id": mission_id,
            "from_agent": from_agent,
            "to_agent": to_agent,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "simulate": True,
            "payload": payload,
        }
        path.write_text(json.dumps(envelope, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def list_messages(self, box: str) -> List[Path]:
        target_dir = self.inbox_dir if box == "inbox" else self.outbox_dir
        if not target_dir.exists():
            return []
        return sorted(target_dir.glob("*.json"))

    def write_log(self, mission_id: str, entry: Dict[str, Any]) -> Path:
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        log_file = self.logs_dir / f"orchestrator_{date_str}.jsonl"
        line = json.dumps(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "mission_id": mission_id,
                **entry,
            },
            ensure_ascii=False,
        )
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        return log_file

    def write_simulation_report(self, mission_id: str, report: Dict[str, Any]) -> Path:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        path = self.state_dir / f"simulation_report_{mission_id}.json"
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return path
