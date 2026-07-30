"""Tests du dispatch de la CLI luna-mission.

Vérifie que les commandes de lecture/status/health/list ne créent jamais de
mission, tandis que l'usage raccourci `luna-mission "texte libre"` et
`luna-workday "phrase"` continuent à créer des missions.
"""

import re
import sqlite3
import subprocess
import sys
from pathlib import Path

PROJECT_PATH = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_PATH / "data" / "luna_missions.db"


def _count_missions() -> int:
    if not DB_PATH.exists():
        return 0
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    try:
        row = conn.execute("SELECT COUNT(*) FROM luna_missions").fetchone()
        return row[0] if row else 0
    finally:
        conn.close()


def _delete_mission(mission_id: str):
    if not DB_PATH.exists():
        return
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    try:
        conn.execute("DELETE FROM luna_missions WHERE mission_id = ?", (mission_id,))
        conn.commit()
    finally:
        conn.close()


def _run_luna_mission(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["luna-mission", *args],
        cwd=PROJECT_PATH,
        capture_output=True,
        text=True,
        check=False,
    )


def _run_luna_workday(prompt: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["luna-workday", prompt],
        cwd=PROJECT_PATH,
        capture_output=True,
        text=True,
        check=False,
    )


def _extract_mission_id(text: str) -> str:
    m = re.search(r"mission_id=(\S+)", text)
    if not m:
        raise AssertionError(f"mission_id introuvable dans la sortie:\n{text}")
    return m.group(1)


def test_health_does_not_create_mission():
    before = _count_missions()
    result = _run_luna_mission("health")
    after = _count_missions()
    assert result.returncode == 0, f"health a échoué:\n{result.stderr}"
    assert after == before, f"health a créé {after - before} mission(s)"
    print("TEST OK: luna-mission health ne crée pas de mission")


def test_status_does_not_create_mission():
    before = _count_missions()
    result = _run_luna_mission("status")
    after = _count_missions()
    assert result.returncode == 0, f"status a échoué:\n{result.stderr}"
    assert after == before, f"status a créé {after - before} mission(s)"
    print("TEST OK: luna-mission status ne crée pas de mission")


def test_list_does_not_create_mission():
    before = _count_missions()
    result = _run_luna_mission("list")
    after = _count_missions()
    assert result.returncode == 0, f"list a échoué:\n{result.stderr}"
    assert after == before, f"list a créé {after - before} mission(s)"
    print("TEST OK: luna-mission list ne crée pas de mission")


def test_free_text_creates_mission():
    before = _count_missions()
    result = _run_luna_mission("vraie mission texte libre TEST-CLI-NATURAL")
    after = _count_missions()
    try:
        assert result.returncode == 0, f"create texte libre a échoué:\n{result.stderr}"
        assert after == before + 1, f"create texte libre devait créer 1 mission, créé {after - before}"
        mission_id = _extract_mission_id(result.stdout)
        assert mission_id.startswith("PROMPT-"), f"ID inattendu: {mission_id}"
        print(f"TEST OK: luna-mission 'texte libre' crée une mission ({mission_id})")
    finally:
        # Nettoyage : suppression de la mission de test
        if result.returncode == 0:
            mission_id = _extract_mission_id(result.stdout)
            _delete_mission(mission_id)


def test_luna_workday_creates_mission():
    before = _count_missions()
    result = _run_luna_workday(
        "Rends l’APK YAWatch/Luna plus livrable production aujourd’hui. "
        "Vérifie Guardian, SOS vocal, contacts, GPS, UI mobile. "
        "Corrige uniquement les P0/P1 safe, teste, commit localement, "
        "bloque push/deploy/SMS/appels, et produis un rapport final. "
        "TEST-CLI-WORKDAY."
    )
    after = _count_missions()
    try:
        assert result.returncode == 0, f"luna-workday a échoué:\n{result.stderr}"
        assert after == before + 1, f"luna-workday devait créer 1 mission, créé {after - before}"
        mission_id = _extract_mission_id(result.stdout)
        assert mission_id.startswith("WORKDAY-"), f"ID inattendu: {mission_id}"
        print(f"TEST OK: luna-workday crée une mission ({mission_id})")
    finally:
        if result.returncode == 0:
            mission_id = _extract_mission_id(result.stdout)
            _delete_mission(mission_id)


if __name__ == "__main__":
    test_health_does_not_create_mission()
    test_status_does_not_create_mission()
    test_list_does_not_create_mission()
    test_free_text_creates_mission()
    test_luna_workday_creates_mission()
    print("\nTous les tests CLI mission sont OK")
