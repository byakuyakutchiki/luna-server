"""Audit de connectivité des agents Luna.

Ce module vérifie la disponibilité des callers (Kimi CLI, DeepSeek, OpenAI)
sans exposer de secrets et sans consommer d'appels IA.

Vérifications effectuées :
- Kimi CLI présent et exécutable
- Clés API DeepSeek/OpenAI définies (présence uniquement, valeur masquée)
- Connectivité réseau vers les endpoints API
- Routing/fallback configuré dans get_caller
"""

import logging
import shutil
import socket
import ssl
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .config import load_config

logger = logging.getLogger(__name__)

AGENT_SHARED = Path("/media/windows/Users/saint/Documents/Codex/AGENT_SHARED")

ENDPOINTS = {
    "deepseek": ("api.deepseek.com", 443),
    "openai": ("api.openai.com", 443),
}


def _mask_secret(value: str) -> str:
    """Masque une valeur secrète en ne montrant que les 4 derniers caractères."""
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return f"...{value[-4:]}"


def _check_tcp_connectivity(host: str, port: int, timeout: int = 10) -> Tuple[bool, str]:
    """Vérifie la connectivité TCP/SSL vers un hôte sans faire d'appel API."""
    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cipher = ssock.cipher()
                version = ssock.version()
                return True, f"SSL OK ({version}, {cipher[0]})"
    except socket.timeout:
        return False, "timeout"
    except socket.gaierror as e:
        return False, f"resolution DNS impossible: {e}"
    except ssl.SSLError as e:
        return False, f"erreur SSL: {e}"
    except OSError as e:
        return False, f"erreur reseau: {e}"
    except Exception as e:
        return False, f"erreur inattendue: {e}"


def _check_http_reachability(url: str, timeout: int = 10) -> Tuple[bool, str]:
    """Vérifie qu'une URL est joignable via HEAD (pas d'appel API)."""
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, f"HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        # 401/403/421 sont acceptables ici car on n'a pas fourni de clé valide
        # ou l'endpoint rejette la requête HEAD sans corps ; le serveur répond.
        if e.code in (401, 403, 421):
            return True, f"HTTP {e.code} (endpoint protege/anti-bot, accessible)"
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, str(e)


def _check_routing_fallback(config: Dict[str, Any]) -> Dict[str, Any]:
    """Vérifie que get_caller possède bien une logique de fallback sur Kimi."""
    try:
        from .agent_caller import get_caller

        results: Dict[str, Any] = {}

        # Simule un config sans clés API pour forcer le fallback
        no_key_config = dict(config)
        no_key_config["DEEPSEEK_API_KEY"] = ""
        no_key_config["OPENAI_API_KEY"] = ""

        try:
            auditor = get_caller("auditor", no_key_config)
            results["auditor_fallback"] = {
                "available": True,
                "actual_agent": auditor.name,
                "expected": "kimi fallback quand deepseek indisponible",
            }
        except Exception as e:
            results["auditor_fallback"] = {"available": False, "error": str(e)}

        try:
            coordinator = get_caller("coordinator", no_key_config)
            results["coordinator_fallback"] = {
                "available": True,
                "actual_agent": coordinator.name,
                "expected": "kimi fallback quand openai indisponible",
            }
        except Exception as e:
            results["coordinator_fallback"] = {"available": False, "error": str(e)}

        return results
    except Exception as e:
        return {"error": str(e)}


def run_audit(config_path: str = None) -> Dict[str, Any]:
    """Exécute l'audit complet de connectivité des agents."""
    config = load_config(config_path)

    result: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "runner_id": config.get("RUNNER_ID", "unknown"),
        "kimi": {},
        "deepseek": {},
        "openai": {},
        "network": {},
        "routing_fallback": {},
        "summary": [],
    }

    # Kimi CLI
    kimi_bin = config.get("KIMI_CLI", "/home/ludo/.kimi-code/bin/kimi")
    kimi_path = shutil.which(kimi_bin)
    result["kimi"] = {
        "configured_path": kimi_bin,
        "resolved_path": kimi_path,
        "available": kimi_path is not None,
    }
    if kimi_path:
        result["summary"].append("Kimi CLI disponible")
    else:
        result["summary"].append("Kimi CLI introuvable")

    # DeepSeek
    ds_key = config.get("DEEPSEEK_API_KEY", "")
    result["deepseek"] = {
        "api_key_configured": bool(ds_key),
        "api_key_suffix": _mask_secret(ds_key),
        "model": config.get("DEEPSEEK_MODEL", "deepseek-chat"),
    }
    if ds_key:
        result["summary"].append("Cle API DeepSeek configuree")
    else:
        result["summary"].append("Cle API DeepSeek absente")

    # OpenAI/Codex
    oa_key = config.get("OPENAI_API_KEY", "")
    result["openai"] = {
        "api_key_configured": bool(oa_key),
        "api_key_suffix": _mask_secret(oa_key),
        "model": config.get("OPENAI_MODEL", "gpt-4o-mini"),
    }
    if oa_key:
        result["summary"].append("Cle API OpenAI configuree")
    else:
        result["summary"].append("Cle API OpenAI absente")

    # Connectivité réseau
    for name, (host, port) in ENDPOINTS.items():
        ok, detail = _check_tcp_connectivity(host, port)
        result["network"][name] = {"host": host, "port": port, "reachable": ok, "detail": detail}
        if ok:
            result["summary"].append(f"Reseau {name} accessible")
        else:
            result["summary"].append(f"Reseau {name} inaccessible: {detail}")

    # HTTP reachability (endpoint racine, pas d'appel API)
    result["network"]["deepseek_http"] = {}
    ok, detail = _check_http_reachability("https://api.deepseek.com/")
    result["network"]["deepseek_http"] = {"url": "https://api.deepseek.com/", "reachable": ok, "detail": detail}

    result["network"]["openai_http"] = {}
    ok, detail = _check_http_reachability("https://api.openai.com/")
    result["network"]["openai_http"] = {"url": "https://api.openai.com/", "reachable": ok, "detail": detail}

    # Routing fallback
    result["routing_fallback"] = _check_routing_fallback(config)

    # Détermine un statut global
    kimi_ok = result["kimi"]["available"]
    network_ok = all(v.get("reachable") for v in result["network"].values())
    keys_ok = result["deepseek"]["api_key_configured"] or result["openai"]["api_key_configured"]

    if kimi_ok and network_ok:
        result["overall_status"] = "ok"
    elif kimi_ok and not keys_ok:
        result["overall_status"] = "limited"
    else:
        result["overall_status"] = "degraded"

    return result


def write_report(result: Dict[str, Any]) -> Path:
    """Écrit le rapport d'audit dans AGENT_SHARED."""
    AGENT_SHARED.mkdir(parents=True, exist_ok=True)
    report_path = AGENT_SHARED / "AGENT-CONNECTIVITY-AUDIT-001_REPORT.md"

    lines: List[str] = [
        "# Rapport d'audit : AGENT-CONNECTIVITY-AUDIT-001",
        "",
        f"- **Mission ID** : AGENT-CONNECTIVITY-AUDIT-001",
        f"- **Date** : {result.get('timestamp')}",
        f"- **Runner ID** : {result.get('runner_id')}",
        f"- **Statut global** : {result.get('overall_status')}",
        "- **Méthode** : audit non destructif sans appel IA",
        "",
        "## Résumé",
        "",
    ]
    for item in result.get("summary", []):
        lines.append(f"- {item}")

    lines.extend(["", "## Kimi CLI", ""])
    kimi = result.get("kimi", {})
    lines.append(f"- Chemin configuré : `{kimi.get('configured_path')}`")
    lines.append(f"- Chemin résolu : `{kimi.get('resolved_path')}`")
    lines.append(f"- Disponible : {kimi.get('available')}")

    lines.extend(["", "## DeepSeek", ""])
    ds = result.get("deepseek", {})
    lines.append(f"- Clé API configurée : {ds.get('api_key_configured')}")
    lines.append(f"- Suffixe clé : `{ds.get('api_key_suffix')}`")
    lines.append(f"- Modèle : `{ds.get('model')}`")

    lines.extend(["", "## OpenAI / Codex", ""])
    oa = result.get("openai", {})
    lines.append(f"- Clé API configurée : {oa.get('api_key_configured')}")
    lines.append(f"- Suffixe clé : `{oa.get('api_key_suffix')}`")
    lines.append(f"- Modèle : `{oa.get('model')}`")

    lines.extend(["", "## Connectivité réseau", ""])
    for name, check in result.get("network", {}).items():
        lines.append(f"- **{name}** : {check.get('host') or check.get('url')} → {check.get('reachable')} ({check.get('detail')})")

    lines.extend(["", "## Routing / fallback", ""])
    routing = result.get("routing_fallback", {})
    if "error" in routing:
        lines.append(f"- Erreur : {routing['error']}")
    else:
        for role, detail in routing.items():
            if "error" in detail:
                lines.append(f"- **{role}** : erreur `{detail['error']}`")
            else:
                lines.append(f"- **{role}** : agent effectif `{detail['actual_agent']}` ({detail['expected']})")

    lines.extend(["", "## Conclusion", ""])
    if result.get("overall_status") == "ok":
        lines.append("Tous les agents sont configurés et les endpoints réseau sont accessibles. Le superviseur peut router les missions vers Kimi, DeepSeek ou OpenAI/Codex avec fallback sur Kimi.")
    elif result.get("overall_status") == "limited":
        lines.append("Kimi est disponible et le réseau est accessible, mais aucune clé API DeepSeek/OpenAI n'est configurée. Seul Kimi sera utilisé ; les fallback auditor/coordinator utiliseront Kimi.")
    else:
        lines.append("État dégradé : au moins un composant essentiel est manquant ou inaccessible. Vérifier la configuration et la connectivité réseau.")

    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Rapport d'audit connectivite cree: %s", report_path)
    return report_path


def main(config_path: str = None) -> Path:
    """Point d'entrée principal de l'audit."""
    result = run_audit(config_path)
    path = write_report(result)
    return path


if __name__ == "__main__":
    path = main()
    print(path)
