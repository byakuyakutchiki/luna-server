#!/bin/bash
# audit_android_state.sh — État Android en lecture seulement
# Usage: ./audit_android_state.sh [output_dir]
# Ne modifie jamais l'état du téléphone.

set -euo pipefail

PACKAGE="fr.yawatch.luna"
OUT_DIR="${1:-/home/ludo/luna-server/docs/AGENT_EXCHANGE/reports_codex}"
TIMESTAMP=$(date -u +"%Y%m%d-%H%M%S")
REPORT_FILE="$OUT_DIR/android-state-audit-${TIMESTAMP}.txt"
MAX_LINES=300
TIMEOUT_SEC=30

mkdir -p "$OUT_DIR"

{
    echo "=== Android State Audit Report ==="
    echo "timestamp: $(date -Iseconds)"
    echo "package: $PACKAGE"
    echo ""

    echo "=== ADB Devices ==="
    timeout "$TIMEOUT_SEC" adb devices -l 2>&1 || echo "[adb error/timeout]"
    echo ""

    echo "=== PID of $PACKAGE ==="
    timeout "$TIMEOUT_SEC" adb shell pidof "$PACKAGE" 2>&1 || echo "[not running or adb error]"
    echo ""

    echo "=== Package Dumpsys ==="
    timeout "$TIMEOUT_SEC" adb shell dumpsys package "$PACKAGE" 2>&1 | head -n "$MAX_LINES" || echo "[adb error/timeout]"
    echo ""

    echo "=== Activity Activities ==="
    timeout "$TIMEOUT_SEC" adb shell dumpsys activity activities 2>&1 | head -n "$MAX_LINES" || echo "[adb error/timeout]"
    echo ""

    echo "=== Activity Services ==="
    timeout "$TIMEOUT_SEC" adb shell dumpsys activity services "$PACKAGE" 2>&1 | head -n "$MAX_LINES" || echo "[adb error/timeout]"
    echo ""

    echo "=== Memory Info ==="
    timeout "$TIMEOUT_SEC" adb shell dumpsys meminfo "$PACKAGE" 2>&1 | head -n "$MAX_LINES" || echo "[adb error/timeout]"
    echo ""

    echo "=== Logcat (last 200 lines, no clear) ==="
    timeout "$TIMEOUT_SEC" adb logcat -d -v threadtime -t 200 2>&1 | grep -iE "yawatch|luna|guardian|AndroidRuntime|FATAL" | tail -n "$MAX_LINES" || echo "[adb error/timeout]"
    echo ""

} > "$REPORT_FILE"

# Sanitize secrets
sed -i -E 's/(api[_-]?key|token|password|secret|credential)["'\''[:space:]]*[:=]["'\''[:space:]]*[^"'\''[:space:]]+/\1=***REDACTED***/gi' "$REPORT_FILE" 2>/dev/null || true

echo "Report written: $REPORT_FILE"
