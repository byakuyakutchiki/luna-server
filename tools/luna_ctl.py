#!/usr/bin/env python3
"""
LUNA-CTL — Outil de pilotage Luna depuis ta VM.

Tu te connectes en SSH a ta VM, et tu tapes:

  luna-ctl status              → Etat du serveur
  luna-ctl health              → Sante systeme
  luna-ctl threats             → Rapport securite
  luna-ctl clients             → Liste clients
  luna-ctl quota 3             → Quota client #3
  luna-ctl ban 185.220.101.34  → Bannir une IP
  luna-ctl unban 185.x.x.x    → Debannir
  luna-ctl banned              → IPs bannies
  luna-ctl lock "raison"       → Lockdown (TOTP requis)
  luna-ctl unlock              → Deverrouiller (TOTP requis)
  luna-ctl shield on|off       → Mode bouclier
  luna-ctl kill 5              → Suspendre client
  luna-ctl revive 5            → Reactiver client
  luna-ctl backup              → Backup Redis
  luna-ctl logs                → Derniers evenements
  luna-ctl errors              → Dernieres erreurs
  luna-ctl digest              → Forcer un digest
  luna-ctl cortex              → Status du cerveau IA
  luna-ctl setup               → Afficher QR TOTP + API key
  luna-ctl rekey               → Regenerer la cle API

Authentification: cle API dans ~/.luna-ctl.key
ou variable LUNA_CTL_KEY

Si le serveur Luna tourne en local (meme VM):
  luna-ctl --local status

Si le serveur Luna est distant:
  luna-ctl --server https://luna.example.com:8888 status
"""

import argparse
import json
import os
import sys
from pathlib import Path
from getpass import getpass

# Ajouter le chemin du serveur pour import direct en mode local
_SERVER_DIR = Path(__file__).parent.parent
if str(_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(_SERVER_DIR))


def load_api_key() -> str:
    """Charge la cle API depuis le fichier ou l'env."""
    # 1. Variable d'environnement
    key = os.getenv("LUNA_CTL_KEY", "")
    if key:
        return key
    # 2. Fichier ~/.luna-ctl.key
    key_file = Path.home() / ".luna-ctl.key"
    if key_file.exists():
        return key_file.read_text().strip()
    # 3. Fichier local
    local_key = Path(__file__).parent.parent / "data" / "cortex_api.key"
    if local_key.exists():
        try:
            data = json.loads(local_key.read_text())
            # On ne peut pas lire la cle depuis le hash
            # Il faut que l'utilisateur ait sauvegarde la cle
            print("Cle API trouvee dans data/ mais non lisible (hashee).")
            print("Utilisez: luna-ctl setup pour voir la cle.")
        except Exception:
            pass
    return ""


def cmd_local(args):
    """Execute en mode local (meme machine que le serveur Luna)."""
    try:
        from core.cortex.auth import CortexAuth
        auth = CortexAuth()

        if args.command == "setup":
            print(auth.get_setup_info())
            return

        if args.command == "rekey":
            new_key = auth.regenerate_api_key()
            print(f"Nouvelle cle API: {new_key}")
            print()
            print(f"Sauvegardez dans ~/.luna-ctl.key :")
            print(f"  echo '{new_key}' > ~/.luna-ctl.key")
            print(f"  chmod 600 ~/.luna-ctl.key")
            return

        # Pour les autres commandes, utiliser le Cortex directement
        from core.cortex.config import CortexConfig
        from core.cortex.brain import LunaCortex

        config = CortexConfig.from_env()
        cortex = LunaCortex(config)
        emergency = cortex.emergency

        # Construire la commande SMS equivalente
        cmd = args.command.upper()
        cmd_args = " ".join(args.args) if args.args else ""
        sms_body = f"LUNA {cmd} {cmd_args}".strip()

        # Les commandes WRITE/CRITICAL necessitent TOTP
        from core.cortex.auth import COMMAND_LEVELS, LEVEL_WRITE, LEVEL_CRITICAL
        level = COMMAND_LEVELS.get(cmd, "read")
        if level in (LEVEL_WRITE, LEVEL_CRITICAL):
            code = input("Code TOTP (Google Authenticator): ").strip()
            if not auth.verify_totp(code):
                print("Code TOTP incorrect.")
                sys.exit(1)
            print("TOTP OK.")

        # Simuler l'auth
        phone_key = "local_cli"
        emergency._sessions[phone_key] = {
            "auth": True,
            "time": __import__("time").time(),
            "role": "founder",
        }

        import asyncio
        response = asyncio.run(
            emergency.handle_incoming_sms(phone_key, sms_body))
        if response:
            print(response)
        else:
            print("Commande executee.")

    except ImportError as e:
        print(f"Erreur import: {e}")
        print("Assurez-vous d'etre dans le repertoire du serveur Luna.")
        sys.exit(1)


def cmd_remote(args, server_url: str, api_key: str):
    """Execute en mode distant (API HTTPS)."""
    import urllib.request
    import urllib.error
    import ssl

    # Ignorer les certificats auto-signes
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    cmd = args.command
    cmd_args = " ".join(args.args) if args.args else ""

    # Mapper les commandes vers les endpoints API
    endpoint_map = {
        "status": ("GET", "/api/cortex/status"),
        "threats": ("GET", "/api/cortex/threats"),
        "signals": ("GET", "/api/cortex/signals"),
        "cortex": ("GET", "/api/cortex/status"),
        "digest": ("POST", "/api/cortex/digest"),
    }

    if cmd == "ban" and cmd_args:
        method, path = "POST", f"/api/cortex/ban/{cmd_args.split()[0]}"
    elif cmd == "unban" and cmd_args:
        method, path = "DELETE", f"/api/cortex/ban/{cmd_args.split()[0]}"
    elif cmd == "lock":
        method, path = "POST", "/api/cortex/mode/lockdown"
    elif cmd == "unlock":
        method, path = "POST", "/api/cortex/mode/normal"
    elif cmd == "shield":
        mode = "shield" if "on" in cmd_args.lower() else "normal"
        method, path = "POST", f"/api/cortex/mode/{mode}"
    elif cmd in endpoint_map:
        method, path = endpoint_map[cmd]
    else:
        print(f"Commande '{cmd}' non supportee en mode distant.")
        print("Utilisez --local pour les commandes avancees.")
        sys.exit(1)

    url = f"{server_url.rstrip('/')}{path}"

    # Preparer la requete
    body = None
    if method == "POST" and cmd_args:
        body = json.dumps({"reason": cmd_args}).encode()

    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("X-Cortex-Key", api_key)
    req.add_header("Content-Type", "application/json")

    try:
        resp = urllib.request.urlopen(req, context=ctx)
        data = json.loads(resp.read())
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except urllib.error.HTTPError as e:
        print(f"Erreur HTTP {e.code}: {e.read().decode()[:500]}")
        sys.exit(1)
    except Exception as e:
        print(f"Erreur connexion: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Luna-CTL — Pilotage Luna depuis ta VM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  luna-ctl status                 # Status du serveur (local)
  luna-ctl ban 185.220.101.34     # Bannir une IP
  luna-ctl lock "maintenance"     # Lockdown (TOTP requis)
  luna-ctl setup                  # Afficher QR TOTP + cle API
  luna-ctl --server https://luna.example.com:8888 status  # Distant
        """,
    )
    parser.add_argument("command", help="Commande a executer")
    parser.add_argument("args", nargs="*", help="Arguments de la commande")
    parser.add_argument(
        "--local", action="store_true", default=True,
        help="Mode local (defaut, meme machine)")
    parser.add_argument(
        "--server", type=str, default="",
        help="URL du serveur Luna distant (ex: https://luna.example.com:8888)")
    parser.add_argument(
        "--key", type=str, default="",
        help="Cle API Cortex (ou LUNA_CTL_KEY env)")

    args = parser.parse_args()

    if args.server:
        api_key = args.key or load_api_key()
        if not api_key:
            print("Cle API requise pour le mode distant.")
            print("  --key <cle> ou LUNA_CTL_KEY=<cle>")
            print("  ou sauvez dans ~/.luna-ctl.key")
            sys.exit(1)
        cmd_remote(args, args.server, api_key)
    else:
        cmd_local(args)


if __name__ == "__main__":
    main()
