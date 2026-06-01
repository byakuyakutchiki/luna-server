#!/usr/bin/env python3
"""Terminal DeepSeek interactif pour audit code Luna — avec livraison GitHub auto."""

import os
import sys
import json
import urllib.request
import urllib.error
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = REPO_ROOT / "docs" / "AGENTS_COLLABORATION"
API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

CONTEXT_FILES = [
    ("OBJECTIFS_ACTIFS.md", "Objectifs actifs"),
    ("QUEUE.md", "Queue des tâches"),
    ("REGLES_DE_COORDINATION.md", "Règles de coordination"),
    ("TABLEAU_DE_BORD.md", "Tableau de bord"),
    ("ETAT_ACTUEL.md", "État actuel"),
]

SYSTEM_PROMPT = """Tu es DeepSeek, agent technique d'audit code Luna.
Tu n'es pas Claude, pas Kimi, pas Codex.

Rôle : audit technique, risques code, faisabilité, propositions précises.

Règles absolues :
- Réponses courtes, concrètes, orientées application.
- Ne jamais proposer de régression graphique.
- Ne jamais modifier la production.
- Ne jamais déclencher SMS, email, appel, paiement, réservation réels.
- Ne jamais modifier secrets, Cloud, base de données, données utilisateur.
- Si changement majeur (niveau 2+) : demander validation Ludovic avant tout.
- Si aucune tâche ouverte : proposer le prochain test bouton/workflow utile.
- Niveaux : 0=audit/doc, 1=petite correction faible risque, 2+=validation Ludovic obligatoire.
- DeepSeek = niveau 0 uniquement (audit, avis, documentation, tests non destructifs).

Tu peux : lire le repo, analyser le code, proposer des patchs niveau 0/1, répondre à Ludovic.

LIVRAISON OBLIGATOIRE :
- Si tu modifies un fichier (code, doc, config), tu DOIS committer et pousser sur GitHub.
- Utilise la commande /commit "description du changement" pour livrer.
- Vérifie ton statut avec /status avant de quitter.
- Si ce n'est pas sur GitHub, ce n'est pas livré."""


def git_status() -> str:
    """Retourne le statut git court."""
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip()
    except Exception as e:
        return f"[erreur git status] {e}"


def git_commit(msg: str) -> str:
    """Commit et push les changements."""
    try:
        # Staging auto
        r = subprocess.run(["git", "add", "-A"], cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            return f"[git add échec] {r.stderr.strip()}"

        # Commit
        r = subprocess.run(["git", "commit", "-m", msg], cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            err = r.stderr.strip()
            if "nothing to commit" in err.lower() or "nothing added" in err.lower():
                return "[git commit] Rien à committer (working tree clean)."
            return f"[git commit échec] {err}"

        # Push
        r = subprocess.run(["git", "push"], cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return f"[git push échec] {r.stderr.strip()}"

        return f"✅ Livré sur GitHub : {msg}"
    except Exception as e:
        return f"[erreur git] {e}"


def git_pull() -> str:
    """Pull la dernière version."""
    try:
        r = subprocess.run(["git", "pull"], cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30)
        return r.stdout.strip() if r.returncode == 0 else f"[git pull échec] {r.stderr.strip()}"
    except Exception as e:
        return f"[erreur git pull] {e}"


def load_context() -> str:
    """Charge le contexte court depuis les fichiers de collaboration."""
    parts = []
    for filename, label in CONTEXT_FILES:
        path = DOCS_DIR / filename
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8").strip()
        if filename == "ETAT_ACTUEL.md":
            lines = content.splitlines()
            content = "\n".join(lines[:40])
        parts.append(f"=== {label} ({filename}) ===\n{content}")
    if not parts:
        return ""
    return "\n\n".join(parts)


def call_deepseek(api_key: str, messages: list) -> str:
    """Appelle l'API DeepSeek et retourne la réponse texte."""
    payload = json.dumps({
        "model": MODEL,
        "messages": messages,
        "max_tokens": 1024,
        "temperature": 0.3,
    }).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return f"[Erreur API {e.code}] {body}"
    except urllib.error.URLError as e:
        return f"[Erreur réseau] {e.reason}"


def main():
    # FIX CWD : se placer dans le repo pour que les fichiers créés soient au bon endroit
    os.chdir(str(REPO_ROOT))

    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        print("Clé API manquante. Lance d'abord :")
        print('  export DEEPSEEK_API_KEY="sk-..."')
        sys.exit(1)

    # Pull auto au démarrage
    print("[Git] Synchronisation...")
    print(git_pull())
    print()

    context = load_context()
    system_content = SYSTEM_PROMPT
    if context:
        system_content += f"\n\n--- Contexte Luna chargé automatiquement ---\n{context}"

    messages = [{"role": "system", "content": system_content}]

    print("=" * 60)
    print("  Terminal DeepSeek — Agent audit code Luna")
    print("  Commandes spéciales : /status  /commit \"msg\"  /pull  /help")
    print("  Tape 'exit' ou Ctrl+C pour quitter.")
    print("=" * 60)
    print()

    while True:
        try:
            user_input = input("Ludovic > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAu revoir.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            # Alert si fichiers non commités
            gs = git_status()
            if gs:
                print(f"\n⚠️  Fichiers non commités :\n{gs}")
                print("Utilise /commit \"msg\" pour livrer avant de quitter.\n")
            print("Au revoir.")
            break

        # Commandes spéciales
        if user_input.startswith("/status"):
            gs = git_status()
            print("DeepSeek > Statut git :")
            print(gs if gs else "(working tree clean)")
            print()
            continue

        if user_input.startswith("/commit"):
            parts = user_input.split(" ", 1)
            msg = parts[1].strip().strip('"') if len(parts) > 1 else "Update from DeepSeek"
            result = git_commit(msg)
            print(f"DeepSeek > {result}\n")
            continue

        if user_input.startswith("/pull"):
            result = git_pull()
            print(f"DeepSeek > {result}\n")
            continue

        if user_input.startswith("/help"):
            print("DeepSeek > Commandes disponibles :")
            print("  /status          — voir les fichiers modifiés")
            print("  /commit \"msg\"   — commit + push sur GitHub")
            print("  /pull            — récupérer les dernières modifications")
            print("  /help            — cette aide")
            print("  exit / quit / q  — quitter\n")
            continue

        messages.append({"role": "user", "content": user_input})
        print("DeepSeek > ...", end="\r", flush=True)

        reply = call_deepseek(api_key, messages)
        print(f"DeepSeek > {reply}\n")
        messages.append({"role": "assistant", "content": reply})

        # Détection auto : si fichiers créés/modifiés, alerter
        gs = git_status()
        if gs:
            print(f"⚠️  [Auto-détection] Fichiers non commités détectés. Utilise /commit pour livrer.\n")


if __name__ == "__main__":
    main()
