"""Service local de stockage des missions Luna.

Remplace le nœud n8n "Data Table" indisponible dans cette installation.
Expose une API HTTP minimale utilisée par les workflows n8n.
"""

import json
import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, g, jsonify, request

logger = logging.getLogger(__name__)

app = Flask(__name__)

DB_PATH_ENV = "LUNA_MISSIONS_DB"
DEFAULT_DB_NAME = "data/luna_missions.db"


def get_db_path() -> str:
    project_path = Path(__file__).resolve().parents[2]
    db_path = os.getenv(DB_PATH_ENV)
    if not db_path:
        db_path = str(project_path / DEFAULT_DB_NAME)
    return db_path


@contextmanager
def get_db():
    db_path = get_db_path()
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS luna_missions (
                mission_id TEXT PRIMARY KEY,
                task_id TEXT,
                status TEXT NOT NULL DEFAULT 'queued',
                current_role TEXT,
                next_role TEXT,
                iteration INTEGER NOT NULL DEFAULT 0,
                max_iterations INTEGER NOT NULL DEFAULT 3,
                approval_required INTEGER NOT NULL DEFAULT 0,
                budget_allowed INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT,
                created_at TEXT,
                mission_context_json TEXT,
                runner_id TEXT,
                result_json TEXT
            )
            """
        )
        conn.commit()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    d["approval_required"] = bool(d.get("approval_required", 0))
    d["budget_allowed"] = bool(d.get("budget_allowed", 1))
    return d


def sanitize_mission(row: Dict[str, Any]) -> Dict[str, Any]:
    """Ne retourne que les champs attendus par le superviseur."""
    fields = [
        "mission_id",
        "task_id",
        "status",
        "current_role",
        "next_role",
        "iteration",
        "max_iterations",
        "approval_required",
        "budget_allowed",
        "updated_at",
        "mission_context_json",
    ]
    result = {k: row.get(k) for k in fields}
    # Extrait objective/description depuis le contexte JSON pour le routeur
    ctx = row.get("mission_context_json") or "{}"
    if isinstance(ctx, str):
        try:
            ctx_obj = json.loads(ctx)
        except Exception:
            ctx_obj = {}
    else:
        ctx_obj = ctx or {}
    result["objective"] = ctx_obj.get("objective", "")
    result["description"] = ctx_obj.get("description", result["objective"])
    return result


@app.before_request
def _ensure_db():
    init_db()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "luna-mission-store"})


@app.route("/mission/<mission_id>", methods=["GET"])
def get_mission(mission_id: str):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM luna_missions WHERE mission_id = ?", (mission_id,)
        ).fetchone()
    if not row:
        return jsonify({"status": "error", "error": "mission_not_found"}), 404
    return jsonify({"status": "ok", "mission": row_to_dict(row)})


@app.route("/create", methods=["POST"])
def create_mission():
    body = request.get_json(force=True, silent=True) or {}
    mission_id = str(body.get("mission_id", "")).strip()
    if not mission_id:
        return jsonify({"status": "error", "error": "missing_mission_id"}), 400

    now = now_iso()
    mission_context = body.get("mission_context_json")
    if isinstance(mission_context, dict):
        mission_context = json.dumps(mission_context, ensure_ascii=False)

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO luna_missions (
                mission_id, task_id, status, current_role, next_role,
                iteration, max_iterations, approval_required, budget_allowed,
                updated_at, created_at, mission_context_json, runner_id, result_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(mission_id) DO UPDATE SET
                task_id=excluded.task_id,
                status=excluded.status,
                current_role=excluded.current_role,
                next_role=excluded.next_role,
                iteration=excluded.iteration,
                max_iterations=excluded.max_iterations,
                approval_required=excluded.approval_required,
                budget_allowed=excluded.budget_allowed,
                updated_at=excluded.updated_at,
                mission_context_json=excluded.mission_context_json,
                runner_id=excluded.runner_id,
                result_json=excluded.result_json
            """,
            (
                mission_id,
                body.get("task_id", mission_id),
                body.get("status", "queued"),
                body.get("current_role", "operator"),
                body.get("next_role", "operator"),
                int(body.get("iteration", 0)),
                int(body.get("max_iterations", 3)),
                1 if body.get("approval_required", False) else 0,
                1 if body.get("budget_allowed", True) else 0,
                now,
                now,
                mission_context,
                body.get("runner_id"),
                None,
            ),
        )
        conn.commit()

    logger.info("Mission upsert: %s", mission_id)
    return jsonify({"status": "queued", "mission_id": mission_id})


@app.route("/next-job", methods=["POST"])
def next_job():
    body = request.get_json(force=True, silent=True) or {}
    runner_id = str(body.get("runner_id", "")).strip()
    current_job_id_raw = body.get("current_job_id")
    current_job_id = None
    if current_job_id_raw is not None and str(current_job_id_raw).strip().lower() not in ("", "none", "null"):
        current_job_id = str(current_job_id_raw).strip()
    now = now_iso()

    with get_db() as conn:
        # Si le runner a déjà un job assigned, le reprendre
        if current_job_id:
            row = conn.execute(
                "SELECT * FROM luna_missions WHERE mission_id = ? AND runner_id = ?",
                (current_job_id, runner_id),
            ).fetchone()
            if row:
                return jsonify({
                    "status": "assigned",
                    "mission": sanitize_mission(row_to_dict(row)),
                })

        # Si le runner a déjà une mission assigned sans current_job_id, la reprendre
        if runner_id:
            row = conn.execute(
                "SELECT * FROM luna_missions WHERE status = 'assigned' AND runner_id = ?",
                (runner_id,),
            ).fetchone()
            if row:
                return jsonify({
                    "status": "assigned",
                    "mission": sanitize_mission(row_to_dict(row)),
                })

        # Sinon prendre le prochain job queued, par updated_at le plus ancien
        row = conn.execute(
            "SELECT * FROM luna_missions WHERE status = 'queued' "
            "ORDER BY updated_at ASC, created_at ASC LIMIT 1"
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE luna_missions SET status = 'assigned', runner_id = ?, updated_at = ? "
                "WHERE mission_id = ?",
                (runner_id, now, row["mission_id"]),
            )
            conn.commit()
            updated = conn.execute(
                "SELECT * FROM luna_missions WHERE mission_id = ?", (row["mission_id"],)
            ).fetchone()
            logger.info("Mission assigned: %s -> runner %s", row["mission_id"], runner_id)
            return jsonify({
                "status": "assigned",
                "mission": sanitize_mission(row_to_dict(updated)),
            })

    return jsonify({"status": "idle"})


@app.route("/report", methods=["POST"])
def report():
    body = request.get_json(force=True, silent=True) or {}
    mission_id = str(body.get("mission_id", "")).strip()
    if not mission_id:
        return jsonify({"status": "error", "error": "missing_mission_id"}), 400

    now = now_iso()
    new_status = str(body.get("status", "queued")).strip()
    iteration = body.get("iteration")
    next_role = body.get("next_role")
    result_json = json.dumps(body, ensure_ascii=False)

    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM luna_missions WHERE mission_id = ?", (mission_id,)
        ).fetchone()
        if not row:
            return jsonify({"status": "error", "error": "mission_not_found"}), 404

        set_parts = ["status = ?, result_json = ?, updated_at = ?"]
        params: List[Any] = [new_status, result_json, now]

        if iteration is not None:
            set_parts.append("iteration = ?")
            params.append(int(iteration))
        if next_role is not None:
            set_parts.append("next_role = ?")
            params.append(next_role)

        params.append(mission_id)
        conn.execute(
            f"UPDATE luna_missions SET {', '.join(set_parts)} WHERE mission_id = ?",
            params,
        )
        conn.commit()

    logger.info("Mission report: %s -> %s", mission_id, new_status)
    return jsonify({"status": "ok", "mission_id": mission_id})


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    init_db()
    host = os.getenv("LUNA_MISSION_STORE_HOST", "127.0.0.1")
    port = int(os.getenv("LUNA_MISSION_STORE_PORT", "9876"))
    app.run(host=host, port=port, threaded=True)


if __name__ == "__main__":
    main()
