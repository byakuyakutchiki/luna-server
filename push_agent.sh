#!/bin/bash
# Usage: ./push_agent.sh "chemin/du/fichier.md" "message de commit"
# Exemple: ./push_agent.sh docs/AGENTS_COLLABORATION/agents/DEEPSEEK_ARCHI_015.md "agent: deepseek archi visio 015"

set -e

FILE="$1"
MSG="${2:-agent: mise a jour}"

if [ -z "$FILE" ]; then
  echo "Usage: $0 <fichier> [message]"
  exit 1
fi

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

echo "[push_agent] Sync main..."
git checkout main
git pull origin main --rebase

echo "[push_agent] Ajout : $FILE"
git add "$FILE"

echo "[push_agent] Commit : $MSG"
git commit -m "$MSG" || echo "[push_agent] Rien a committer"

echo "[push_agent] Push..."
git push origin main

echo "[push_agent] OK — hash: $(git log --oneline -1)"
