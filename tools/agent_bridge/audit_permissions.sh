#!/bin/bash
# audit_permissions.sh — Permissions et capacités de l'APK Luna en lecture seulement
# Usage: ./audit_permissions.sh [output_dir]

set -euo pipefail

PACKAGE="fr.yawatch.luna"
OUT_DIR="${1:-/home/ludo/luna-server/docs/AGENT_EXCHANGE/reports_codex}"
TIMESTAMP=$(date -u +"%Y%m%d-%H%M%S")
REPORT_FILE="$OUT_DIR/permissions-audit-${TIMESTAMP}.txt"
MAX_LINES=300
TIMEOUT_SEC=30

mkdir -p "$OUT_DIR"

{
    echo "=== Permissions Audit Report ==="
    echo "timestamp: $(date -Iseconds)"
    echo "package: $PACKAGE"
    echo ""

    echo "=== Runtime permissions ==="
    timeout "$TIMEOUT_SEC" adb shell dumpsys package "$PACKAGE" 2>&1 | grep -A 200 "runtime permissions" | head -n "$MAX_LINES" || echo "[adb error/timeout]"
    echo ""

    echo "=== Install permissions ==="
    timeout "$TIMEOUT_SEC" adb shell dumpsys package "$PACKAGE" 2>&1 | grep -A 100 "install permissions" | head -n "$MAX_LINES" || echo "[adb error/timeout]"
    echo ""

    echo "=== AndroidManifest.xml permissions (from repo) ==="
    if [ -f "/home/ludo/luna-server/android-app/AndroidManifest.xml" ]; then
        timeout "$TIMEOUT_SEC" grep -nE "uses-permission|permission |foregroundServiceType|exported" /home/ludo/luna-server/android-app/AndroidManifest.xml 2>&1 | head -n "$MAX_LINES" || echo "[error]"
    else
        echo "[AndroidManifest.xml not found in expected path]"
    fi
    echo ""

    echo "=== Special app access ==="
    timeout "$TIMEOUT_SEC" adb shell appops get "$PACKAGE" 2>&1 | head -n "$MAX_LINES" || echo "[adb error/timeout]"
    echo ""

} > "$REPORT_FILE"

sed -i -E 's/(api[_-]?key|token|password|secret|credential)["'\''[:space:]]*[:=]["'\''[:space:]]*[^"'\''[:space:]]+/\1=***REDACTED***/gi' "$REPORT_FILE" 2>/dev/null || true

echo "Report written: $REPORT_FILE"
