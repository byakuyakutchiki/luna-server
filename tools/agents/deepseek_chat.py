#!/usr/bin/env python3
"""Terminal DeepSeek interactif pour audit code Luna.

NOUVEAU — Gestion Git automatique :
- Se place dans REPO_ROOT au démarrage
- git pull automatique au démarrage
- Détection auto des fichiers modifiés après chaque réponse
- Commandes /status, /pull, /commit pour livrer sur GitHub
"""

import os
import sys
import json
import subprocess
import urllib.request
import urllib.error
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

LIVRAISON OBLIGATOIRE :
- Quand tu produis un rapport, crée le fichier dans docs/AGENTS_COLLABORATION/agents/DEEPSEEK_*.md
- Après avoir créé/modifié des fichiers, utilise la commande /commit "message" pour livrer sur GitHub.
- Si tu ne fais pas /commit, tes résultats ne sont PAS sur GitHub et Ludovic ne les voit pas.
- Exemple : /commit "TASK-017-DEEPSEEK: audit UI mobile — cause CSS trouvée"

Tu peux : lire le repo, analyser le code, proposer des patchs niveau 0/1, répondre à Ludovic."""


def _run_git(cmd: list, cwd: Path = REPO_ROOT) -> tuple:
    """Exécute une commande git et retourne (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd)] + cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return -1, "", str(e)


def git_pull() -> str:
    """Fait un git pull et retourne un résumé."""
    rc, out, err = _run_git(["pull", "--ff-only"])
    if rc == 0:
        return f"✅ Git pull OK : {out[:80]}" if out else "✅ Git pull OK (déjà à jour)"
    return f"⚠️ Git pull échoue : {err[:120]}"


def git_status_short() -> str:
    """Retourne le git status --short."""
    rc, out, _ = _run_git(["status", "--short"])
    return out if rc == 0 else ""


def git_commit_push(message: str) -> str:
    """Add, commit, push. Retourne le résultat."""
    rc1, _, err1 = _run_git(["add", "-A"])
    if rc1 != 0:
        return f"❌ git add échoue : {err1}"
    rc2, out2, err2 = _run_git(["commit", "-m", message])
    if rc2 != 0:
        return f"❌ git commit échoue : {err2}"
    rc3, out3, err3 = _run_git(["push", "origin", "HEAD"])
    if rc3 != 0:
        return f"❌ git push échoue : {err3}"
    return f"✅ Livré sur GitHub : {out3[:80]}"


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


def check_and_commit():
    """Vérifie si des fichiers sont modifiés et propose de committer."""
    status = git_status_short()
    if not status:
        return
    print()
    print("─" * 50)
    print("📁 Fichiers modifiés/créés détectés :")
    for line in status.splitlines()[:15]:
        print(f"   {line}")
    if len(status.splitlines()) > 15:
        print(f"   ... et {len(status.splitlines()) - 15} autres")
    print()
    try:
        ans = input("💾 Committer et push sur GitHub ? [o/N] ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print("⏭️  Commit annulé.")
        return
    if ans in ("o", "oui", "y", "yes"):
        msg = input("📝 Message de commit : ").strip()
        if not msg:
            msg = "DEEPSEEK: mise à jour automatique"
        result = git_commit_push(msg)
        print(result)
    else:
        print("⏭️  Commit annulé. Utilise /commit plus tard.")
    print("─" * 50)


def handle_command(cmd: str, api_key: str, messages: list) -> bool:
    """Gère les commandes spéciales. Retourne True si c'est une commande traitée."""
    parts = cmd.split(None, 1)
    if not parts:
        return False
    keyword = parts[0].lower()

    if keyword == "/status":
        status = git_status_short()
        if status:
            print("📁 Fichiers modifiés :")
            print(status)
        else:
            print("✅ Aucun fichier modifié.")
        return True

    if keyword == "/pull":
        print(git_pull())
        return True

    if keyword == "/commit":
        msg = parts[1] if len(parts) > 1 else "DEEPSEEK: mise à jour"
        print(git_commit_push(msg))
        return True

    if keyword in ("/help", "/aide"):
        print("""
Commandes disponibles :
  /status        → Voir les fichiers modifiés
  /pull          → git pull (synchroniser avec GitHub)
  /commit "msg"  → git add + commit + push
  /help          → Cette aide
  exit / quit / q → Quitter
""")
        return True

    return False


def main():
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        print("Clé API manquante. Lance d'abord :")
        print('  export DEEPSEEK_API_KEY="sk-..."')
        sys.exit(1)

    # Se placer dans le repo
    os.chdir(REPO_ROOT)
    print(f"📂 Repo : {REPO_ROOT}")

    # Git pull au démarrage
    print(git_pull())

    context = load_context()
    system_content = SYSTEM_PROMPT
    if context:
        system_content += f"\n\n--- Contexte Luna chargé automatiquement ---\n{context}"

    messages = [{"role": "system", "content": system_content}]

    print("=" * 60)
    print("  Terminal DeepSeek — Agent audit code Luna")
    print("  Tape '/help' pour les commandes, 'exit' pour quitter.")
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
            print("Au revoir.")
            break

        # Commandes spéciales
        if handle_command(user_input, api_key, messages):
            continue

        messages.append({"role": "user", "content": user_input})
        print("DeepSeek > ...", end="\r", flush=True)

        reply = call_deepseek(api_key, messages)
        print(f"DeepSeek > {reply}\n")
        messages.append({"role": "assistant", "content": reply})

        # Détection auto des fichiers modifiés
        check_and_commit()


if __name__ == "__main__":
    main()
