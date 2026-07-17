"""Tests unitaires de l'audit de connectivité des agents.

Ne consomme aucun appel IA.
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from luna_supervisor.agent_connectivity import (
    _check_tcp_connectivity,
    _mask_secret,
    run_audit,
)


def test_mask_secret():
    assert _mask_secret("sk-1234567890abcdef") == "...cdef"
    assert _mask_secret("short") == "***"
    assert _mask_secret("") == ""
    print("TEST OK: masquage des secrets")


def test_check_tcp_connectivity_ok():
    ok, detail = _check_tcp_connectivity("api.deepseek.com", 443, timeout=15)
    assert ok, f"DeepSeek doit etre accessible, recu: {detail}"
    assert "SSL OK" in detail
    print("TEST OK: connectivite TCP/SSL DeepSeek")


def test_check_tcp_connectivity_ko():
    ok, detail = _check_tcp_connectivity("invalid.invalid", 443, timeout=5)
    assert not ok
    print("TEST OK: hôte invalide detecte")


def test_run_audit_structure():
    # Isole les variables d'environnement pour ce test
    old_environ = dict(os.environ)
    for key in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "RUNNER_ID"):
        os.environ.pop(key, None)

    os.environ["DEEPSEEK_API_KEY"] = "ds-test-key"
    os.environ["OPENAI_API_KEY"] = "oa-test-key"
    os.environ["RUNNER_ID"] = "test-runner"

    try:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_audit(str(Path(tmp)))

            assert "timestamp" in result
            assert "kimi" in result
            assert "deepseek" in result
            assert "openai" in result
            assert "network" in result
            assert "routing_fallback" in result
            assert result["runner_id"] == "test-runner"
            assert result["deepseek"]["api_key_configured"] is True
            assert result["openai"]["api_key_configured"] is True
            assert result["deepseek"]["api_key_suffix"] == "...-key"
            print("TEST OK: structure du rapport d'audit")
    finally:
        os.environ.clear()
        os.environ.update(old_environ)


if __name__ == "__main__":
    tests = [
        test_mask_secret,
        test_check_tcp_connectivity_ok,
        test_check_tcp_connectivity_ko,
        test_run_audit_structure,
    ]
    failed = []
    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"TEST {t.__name__} FAILED: {e}")
            failed.append(t.__name__)
    if failed:
        print(f"\n{len(failed)} test(s) echoue(s): {failed}")
        sys.exit(1)
    print("\nTous les tests de connectivite sont OK.")
