#!/usr/bin/env python3
"""Terminal DeepSeek interactif pour audit code Luna."""

import os
import sys
import json
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

Tu peux : lire le repo, analyser le code, proposer des patchs niveau 0/1, répondre à Ludovic."""


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
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        print("Clé API manquante. Lance d'abord :")
        print('  export DEEPSEEK_API_KEY="sk-..."')
        sys.exit(1)

    context = load_context()
    system_content = SYSTEM_PROMPT
    if context:
        system_content += f"\n\n--- Contexte Luna chargé automatiquement ---\n{context}"

    messages = [{"role": "system", "content": system_content}]

    print("=" * 60)
    print("  Terminal DeepSeek — Agent audit code Luna")
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
            print("Au revoir.")
            break

        messages.append({"role": "user", "content": user_input})
        print("DeepSeek > ...", end="\r", flush=True)

        reply = call_deepseek(api_key, messages)
        print(f"DeepSeek > {reply}\n")
        messages.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    main()
