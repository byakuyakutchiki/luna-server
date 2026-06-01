#!/usr/bin/env bash
# Wrapper DeepSeek — Lance le terminal avec le bon CWD et vérifie la clé API.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [ -z "${DEEPSEEK_API_KEY:-}" ]; then
    echo "❌ Clé API manquante. Lance d'abord :"
    echo '   export DEEPSEEK_API_KEY="sk-..."'
    exit 1
fi

cd "$REPO_ROOT"
echo "📂 DeepSeek runner — Repo : $REPO_ROOT"
echo "🔑 Clé API OK"
echo ""

exec python3 tools/agents/deepseek_chat.py
