#!/bin/bash
# sanitize_report.sh — Supprime les secrets potentiels d'un rapport
# Usage: ./sanitize_report.sh <input_file> [output_file]

set -euo pipefail

INPUT="${1:-}"
OUTPUT="${2:-$INPUT.sanitized}"

if [ -z "$INPUT" ] || [ ! -f "$INPUT" ]; then
    echo "Usage: $0 <input_file> [output_file]"
    exit 1
fi

cp "$INPUT" "$OUTPUT"

# Patterns de secrets courants
sed -i -E '
    s/(api[_-]?key|apikey|api-key)["'\''[:space:]]*[:=]["'\''[:space:]]*[^"'\''[:space:]]+/\1=***REDACTED***/gi;
    s/(auth[_-]?token|access[_-]?token|refresh[_-]?token|bearer)["'\''[:space:]]*[:=]["'\''[:space:]]*[^"'\''[:space:]]+/\1=***REDACTED***/gi;
    s/(password|passwd|pwd|secret|credential)["'\''[:space:]]*[:=]["'\''[:space:]]*[^"'\''[:space:]]+/\1=***REDACTED***/gi;
    s/(sk-[a-zA-Z0-9]{20,})/***OPENAI_KEY_REDACTED***/g;
    s/([0-9a-f]{32,})/***HEX_REDACTED***/gi;
    s/([A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)/***JWT_REDACTED***/g;
' "$OUTPUT" 2>/dev/null || true

echo "Sanitized report: $OUTPUT"
