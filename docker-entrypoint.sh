#!/bin/bash
set -e

echo "================================================"
echo "  YAWatch Luna - Demarrage"
echo "================================================"

if [ "$ENVIRONMENT" = "cloudrun" ]; then
    # --- Cloud Run: pas de SSL, Redis externe ---
    echo "[Luna] Mode: CLOUD RUN"
    echo "[Luna] SSL: desactive (gere par Google)"
    echo "[Luna] Redis: ${REDIS_URL:-NON CONFIGURE}"
    export LUNA_PORT="${PORT:-8080}"
else
    # --- Local/Docker: Redis local + SSL auto-signe ---
    echo "[Luna] Mode: LOCAL/DOCKER"
    export REDIS_URL="${REDIS_URL:-redis://redis:6379/0}"

    CERT_FILE="${SSL_CERTFILE:-/app/certs/cert.pem}"
    KEY_FILE="${SSL_KEYFILE:-/app/certs/key.pem}"
    export SSL_CERTFILE="$CERT_FILE"
    export SSL_KEYFILE="$KEY_FILE"

    if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
        echo "[Luna] Generation certificats SSL auto-signes..."
        openssl req -x509 -newkey rsa:4096 \
            -keyout "$KEY_FILE" -out "$CERT_FILE" \
            -days 365 -nodes \
            -subj "/CN=localhost/O=YAWatch-Luna" 2>/dev/null
        echo "[Luna] Certificats SSL generes"
    fi
fi

# Stripe auto-setup si cle presente mais prix absents
if [ -n "$STRIPE_API_KEY" ] && [ -z "$STRIPE_PRICE_ESSENTIEL" ]; then
    echo "[Luna] Configuration automatique des produits Stripe..."
    python /app/utils/stripe_setup.py --env /app/.env 2>/dev/null || \
        echo "[Luna] Stripe auto-setup: ignore (optionnel)"
fi

# Validation informative
if [ -f /app/utils/validate_keys.py ]; then
    echo ""
    echo "[Luna] Validation de la configuration..."
    python /app/utils/validate_keys.py --skip-api 2>/dev/null || true
    echo ""
fi

echo "[Luna] Demarrage du serveur Luna..."
exec python /app/luna_web.py
