#!/bin/bash
# audit_guardian_service.sh — État du service Guardian en lecture seulement
# Usage: ./audit_guardian_service.sh [output_dir]

set -euo pipefail

PACKAGE="fr.yawatch.luna"
OUT_DIR="${1:-/home/ludo/luna-server/docs/AGENT_EXCHANGE/reports_codex}"
TIMESTAMP=$(date -u +"%Y%m%d-%H%M%S")
REPORT_FILE="$OUT_DIR/guardian-service-audit-${TIMESTAMP}.txt"
MAX_LINES=300
TIMEOUT_SEC=30

mkdir -p "$OUT_DIR"

{
    echo "=== Guardian Service Audit Report ==="
    echo "timestamp: $(date -Iseconds)"
    echo "package: $PACKAGE"
    echo ""

    echo "=== PID ==="
    timeout "$TIMEOUT_SEC" adb shell pidof "$PACKAGE" 2>&1 || echo "[not running]"
    echo ""

    echo "=== Running services for package ==="
    timeout "$TIMEOUT_SEC" adb shell dumpsys activity services "$PACKAGE" 2>&1 | head -n "$MAX_LINES" || echo "[adb error/timeout]"
    echo ""

    echo "=== Service process details ==="
    PID=$(adb shell pidof "$PACKAGE" 2>/dev/null || echo "")
    if [ -n "$PID" ]; then
        timeout "$TIMEOUT_SEC" adb shell ps -p "$PID" -o PID,PPID,NAME,CPU,MEM 2>&1 || echo "[ps error]"
    else
        echo "[no PID available]"
    fi
    echo ""

    echo "=== Guardian logcat (last 200 lines) ==="
    timeout "$TIMEOUT_SEC" adb logcat -d -v threadtime -t 200 2>&1 | grep -iE "Guardian|GuardianService|LunaApp|yawatch" | tail -n "$MAX_LINES" || echo "[adb error/timeout]"
    echo ""

} > "$REPORT_FILE"

sed -i -E 's/(api[_-]?key|token|password|secret|credential)["'\''[:space:]]*[:=]["'\''[:space:]]*[^"'\''[:space:]]+/\1=***REDACTED***/gi' "$REPORT_FILE" 2>/dev/null || true

echo "Report written: $REPORT_FILE"
