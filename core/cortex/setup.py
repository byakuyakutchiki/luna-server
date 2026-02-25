"""
CORTEX SETUP — Premier lancement.

Lance avec:
  cd serveur/
  python3 -m core.cortex.setup            # interactif
  python3 -m core.cortex.setup --show     # non-interactif (affiche QR seulement)
"""

import os
import sys
from pathlib import Path

# Ajouter le chemin du serveur
_server_dir = str(Path(__file__).parent.parent.parent)
if _server_dir not in sys.path:
    sys.path.insert(0, _server_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(_server_dir, ".env"))

from core.cortex.auth import CortexAuth


def main():
    # Mode non-interactif si --show ou stdin non dispo
    show_only = "--show" in sys.argv or not sys.stdin.isatty()

    print()
    print("=" * 56)
    print("  LUNA CORTEX — SETUP SECURITE")
    print("  Premiere configuration de l'authentification")
    print("=" * 56)
    print()

    auth = CortexAuth()

    # 1. TOTP
    print("1. GOOGLE AUTHENTICATOR (TOTP)")
    print("   Scannez ce QR code avec Google Authenticator")
    print("   ou Authy sur votre telephone:")
    print()
    print(auth.get_totp_qr_text())
    print()
    print(f"   Secret (saisie manuelle): {auth._totp_secret}")
    print(f"   Code actuel (pour test): {auth.get_current_totp()}")
    print()

    if not show_only:
        # Test TOTP interactif
        try:
            test = input("   Entrez le code TOTP pour verifier: ").strip()
            if test:
                if auth.verify_totp(test):
                    print("   CODE CORRECT — TOTP configure!")
                else:
                    print("   Code incorrect. Reverifiez le QR code.")
                    print("   (le setup continue quand meme)")
        except EOFError:
            pass
    else:
        print("   (Mode affichage — scannez le QR code ci-dessus)")
    print()

    # 2. API Key
    print("2. CLE API (pour luna-ctl depuis votre VM)")
    new_key = auth.get_new_api_key()
    if new_key:
        print(f"   VOTRE CLE API: {new_key}")
        print()
        print("   IMPORTANT: Notez cette cle, elle ne sera PLUS affichee!")
        print()
        print("   Pour l'utiliser depuis votre VM:")
        print(f"     echo '{new_key}' > ~/.luna-ctl.key")
        print("     chmod 600 ~/.luna-ctl.key")
        print("     luna-ctl status")
    else:
        print("   Cle deja generee. Pour regenerer:")
        print("     luna-ctl rekey")
    print()

    # 3. Telegram
    print("3. TELEGRAM BOT")
    bot_token = os.getenv("ALERT_TELEGRAM_BOT_TOKEN", "")
    if bot_token:
        print(f"   Bot token: {bot_token[:10]}...{bot_token[-5:]}")
        print()
        print("   Pour vous associer:")
        print("   a) Ouvrez Telegram et cherchez votre bot")
        print("   b) Envoyez /start")
        print("   c) Envoyez /pair <code_totp>")
        print("   d) Le bot confirmera votre enregistrement")
    else:
        print("   Pas de bot token configure.")
        print("   Pour en creer un:")
        print("   a) Ouvrez Telegram et cherchez @BotFather")
        print("   b) Envoyez /newbot et suivez les instructions")
        print("   c) Copiez le token dans .env:")
        print("      ALERT_TELEGRAM_BOT_TOKEN=votre_token")
    print()

    # 4. SMS
    print("4. COMMANDES SMS D'URGENCE")
    print("   Configurez dans .env:")
    print("     CORTEX_ENABLED=true")
    print("     FOUNDER_PHONE=+33658477952")
    print()
    print("   Pour vous authentifier par SMS:")
    print("     LUNA AUTH <code_totp_6_chiffres>")
    print("   Puis envoyez vos commandes:")
    print("     LUNA STATUS")
    print("     LUNA BAN 185.x.x.x")
    print("     etc.")
    print()

    # Resume
    print("=" * 56)
    print("  RESUME SECURITE")
    print("=" * 56)
    print()
    print("  Depuis ton TELEPHONE:")
    print("    Telegram: /status, /ban, /lock, /maintenance...")
    print("    SMS: comment va le serveur, bloque 1.2.3.4...")
    print("    TOTP pour les actions sensibles")
    print()
    print("  Depuis ta VM (SSH):")
    print("    luna-ctl status")
    print("    luna-ctl ban 185.x.x.x")
    print("    luna-ctl lock \"maintenance\"")
    print()
    print("  TOUTES LES COMMANDES (43):")
    print("  LECTURE: status, health, threats, clients, quota,")
    print("    banned, logs, errors, cortex, digest, ping,")
    print("    uptime, redis, config, version, sessions,")
    print("    processes, network, disk, whitelist")
    print("  ECRITURE: ban, unban, kill, revive, backup,")
    print("    maintenance, announce, msg, whitelist_add,")
    print("    whitelist_del, quota_set, quota_reset, purge,")
    print("    ratelimit")
    print("  CRITIQUE: lock, unlock, shield, restart, stop,")
    print("    rekey, wipe")
    print()
    print("  Le serveur te RECONNAIT par:")
    print("    Telegram: ton user_id (infalsifiable)")
    print("    SMS: ton numero + TOTP (double verif)")
    print("    CLI: cle API + TOTP pour actions sensibles")
    print()
    print("  Meme sans Claude, meme a 3h du mat, tu controles tout.")
    print()
    print("=" * 56)


if __name__ == "__main__":
    main()
