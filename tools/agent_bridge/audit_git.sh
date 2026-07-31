#!/bin/bash
# audit_git.sh — État Git en lecture seulement
# Usage: ./audit_git.sh [output_dir]
# Ne modifie jamais l'état du dépôt.

set -euo pipefail

REPO="/home/ludo/luna-server"
OUT_DIR="${1:-/home/ludo/luna-server/docs/AGENT_EXCHANGE/reports_codex}"
TIMESTAMP=$(date -u +"%Y%m%d-%H%M%S")
REPORT_FILE="$OUT_DIR/git-audit-${TIMESTAMP}.txt"
MAX_LINES=500
TIMEOUT_SEC=30

mkdir -p "$OUT_DIR"

cd "$REPO" || exit 1

{
    echo "=== Git Audit Report ==="
    echo "timestamp: $(date -Iseconds)"
    echo "hostname: $(hostname)"
    echo "repo: $REPO"
    echo ""

    echo "=== Branch ==="
    timeout "$TIMEOUT_SEC" git branch --show-current 2>&1 || echo "[timeout/error]"
    echo ""

    echo "=== Status (short) ==="
    timeout "$TIMEOUT_SEC" git status --short 2>&1 | head -n "$MAX_LINES" || echo "[timeout/error]"
    echo ""

    echo "=== Log (last 30) ==="
    timeout "$TIMEOUT_SEC" git log --oneline --decorate -30 2>&1 || echo "[timeout/error]"
    echo ""

    echo "=== Diff stats ==="
    timeout "$TIMEOUT_SEC" git diff --stat 2>&1 | head -n "$MAX_LINES" || echo "[timeout/error]"
    echo ""

    echo "=== Worktrees ==="
    timeout "$TIMEOUT_SEC" git worktree list 2>&1 || echo "[timeout/error]"
    echo ""

    echo "=== Remotes ==="
    timeout "$TIMEOUT_SEC" git remote -v 2>&1 | head -n "$MAX_LINES" || echo "[timeout/error]"
    echo ""

    echo "=== Stashes ==="
    timeout "$TIMEOUT_SEC" git stash list 2>&1 || echo "[timeout/error]"
    echo ""

} > "$REPORT_FILE"

# Sanitize secrets
sed -i -E 's/(api[_-]?key|token|password|secret|credential)["'\''[:space:]]*[:=]["'\''[:space:]]*[^"'\''[:space:]]+/\1=***REDACTED***/gi' "$REPORT_FILE" 2>/dev/null || true

echo "Report written: $REPORT_FILE"
