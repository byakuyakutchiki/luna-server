#!/bin/bash
# audit_guardian_logs.sh — Logs Guardian (logcat filtré) en lecture seulement
# Usage: ./audit_guardian_logs.sh [output_dir]
# Ne vide jamais logcat.

set -euo pipefail

PACKAGE="fr.yawatch.luna"
OUT_DIR="${1:-/home/ludo/luna-server/docs/AGENT_EXCHANGE/reports_codex}"
TIMESTAMP=$(date -u +"%Y%m%d-%H%M%S")
REPORT_FILE="$OUT_DIR/guardian-logs-audit-${TIMESTAMP}.txt"
MAX_LINES=500
TIMEOUT_SEC=30

mkdir -p "$OUT_DIR"

{
    echo "=== Guardian Logs Audit Report ==="
    echo "timestamp: $(date -Iseconds)"
    echo "package: $PACKAGE"
    echo ""

    echo "=== ADB Devices ==="
    timeout "$TIMEOUT_SEC" adb devices -l 2>&1 || echo "[adb error/timeout]"
    echo ""

    echo "=== Guardian logcat (last 300 lines) ==="
    timeout "$TIMEOUT_SEC" adb logcat -d -v threadtime -t 300 --pid="$(adb shell pidof "$PACKAGE" 2>/dev/null || echo 0)" 2>&1 | head -n "$MAX_LINES" || echo "[adb error/timeout]"
    echo ""

    echo "=== Filtered Guardian/Luna logcat (last 400 lines) ==="
    timeout "$TIMEOUT_SEC" adb logcat -d -v threadtime -t 400 2>&1 | grep -iE "Guardian|yawatch|luna|LunaApp|RealTime" | tail -n "$MAX_LINES" || echo "[adb error/timeout]"
    echo ""

    echo "=== System errors / crashes ==="
    timeout "$TIMEOUT_SEC" adb logcat -d -v threadtime -t 200 2>&1 | grep -iE "FATAL|AndroidRuntime|crash|ANR" | tail -n 100 || echo "[adb error/timeout]"
    echo ""

} > "$REPORT_FILE"

# Sanitize secrets
sed -i -E 's/(api[_-]?key|token|password|secret|credential)["'\''[:space:]]*[:=]["'\''[:space:]]*[^"'\''[:space:]]+/\1=***REDACTED***/gi' "$REPORT_FILE" 2>/dev/null || true

echo "Report written: $REPORT_FILE"
