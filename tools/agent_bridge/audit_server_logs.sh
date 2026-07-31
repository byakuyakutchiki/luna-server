#!/bin/bash
# audit_server_logs.sh — Logs serveur Luna en lecture seulement
# Usage: ./audit_server_logs.sh [output_dir]
# Ne redémarre aucun service.

set -euo pipefail

OUT_DIR="${1:-/home/ludo/luna-server/docs/AGENT_EXCHANGE/reports_codex}"
TIMESTAMP=$(date -u +"%Y%m%d-%H%M%S")
REPORT_FILE="$OUT_DIR/server-logs-audit-${TIMESTAMP}.txt"
MAX_LINES=500
TIMEOUT_SEC=30

mkdir -p "$OUT_DIR"

{
    echo "=== Server Logs Audit Report ==="
    echo "timestamp: $(date -Iseconds)"
    echo ""

    echo "=== systemd luna service ==="
    timeout "$TIMEOUT_SEC" systemctl status luna --no-pager 2>&1 | head -n "$MAX_LINES" || echo "[service not found or timeout]"
    echo ""

    echo "=== journalctl luna (last 200 lines) ==="
    timeout "$TIMEOUT_SEC" journalctl -u luna --no-pager -n 200 2>&1 | tail -n "$MAX_LINES" || echo "[no journal or timeout]"
    echo ""

    echo "=== Processes luna ==="
    timeout "$TIMEOUT_SEC" ps aux | grep -iE "luna|python|gunicorn|uvicorn" | grep -v grep | head -n 50 || echo "[none]"
    echo ""

    echo "=== Listening ports ==="
    timeout "$TIMEOUT_SEC" ss -lntp 2>&1 | head -n 50 || echo "[timeout/error]"
    echo ""

    echo "=== Health check ==="
    timeout "$TIMEOUT_SEC" curl -s -o /dev/null -w "%{http_code}" http://localhost:8888/api/admin/health 2>&1 || echo "[unreachable]"
    echo ""

} > "$REPORT_FILE"

# Sanitize secrets
sed -i -E 's/(api[_-]?key|token|password|secret|credential)["'\''[:space:]]*[:=]["'\''[:space:]]*[^"'\''[:space:]]+/\1=***REDACTED***/gi' "$REPORT_FILE" 2>/dev/null || true

echo "Report written: $REPORT_FILE"
