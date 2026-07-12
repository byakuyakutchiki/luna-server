#!/bin/bash
# Wrapper de lancement Luna pour systemd.
# Charge .env proprement (ignore commentaires inline incompatibles avec systemd).
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_TMP="$(mktemp /tmp/luna-env.XXXXXX)"
trap 'rm -f "$ENV_TMP"' EXIT

# Charger .env de manière fiable sans exposer les secrets dans les logs
"$SCRIPT_DIR/luna-load-env.py" "$ENV_TMP"
# shellcheck source=/dev/null
source "$ENV_TMP"
rm -f "$ENV_TMP"

exec /usr/bin/python3 -m uvicorn luna_web:app --host 0.0.0.0 --port 8000
