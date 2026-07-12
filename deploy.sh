#!/bin/bash
# Deploy Luna Beta sur Cloud Run
# Usage: ./deploy.sh
set -e

REGION="europe-west1"
SERVICE="luna-beta"
PROJECT="crypto-parser-475411-k4"

# Charger les vars critiques depuis .env local (source de vérité)
source "$(dirname "$0")/.env" 2>/dev/null || true

# Construire la liste des env vars a mettre a jour
# On n'INCLUT PAS les variables vides pour eviter d'ecraser les valeurs existantes sur Cloud Run
update_vars=()
update_vars+=("ENVIRONMENT=cloudrun")
update_vars+=("CORTEX_ENABLED=false")   # SMS auto désactivé — évite vidage crédit Twilio

# Détection d'urgence vocale Iris : ACTIVE par défaut, en mode OBSERVATION (dry-run).
# Pour passer en RÉEL : definir VOICE_EMERGENCY_DRY_RUN=false dans .env.
: "${VOICE_EMERGENCY_ENABLED:=true}"
: "${VOICE_EMERGENCY_DRY_RUN:=true}"

# Fonction helper : ajoute une variable seulement si elle est definie et non vide
add_var() {
  local name="$1"
  local val="${!name}"
  if [[ -n "$val" ]]; then
    update_vars+=("${name}=${val}")
  fi
}

add_var "JWT_SECRET_KEY"
add_var "PV_SIGNED"
add_var "PV_SIGNATURE_HASH"
add_var "OPENAI_API_KEY"
add_var "ADMIN_NUMBER"
add_var "VOICE_EMERGENCY_ENABLED"
add_var "VOICE_EMERGENCY_DRY_RUN"
add_var "TWILIO_ACCOUNT_SID"
add_var "TWILIO_AUTH_TOKEN"
add_var "TWILIO_SMS_FROM"
add_var "TWILIO_PHONE_NUMBER"
add_var "VOICE_CALLBACK_URL"
add_var "PROPRIO_PASSWORD"
add_var "PROPRIO_EMAIL"
add_var "REDIS_URL"
add_var "SIMLI_API_KEY"
add_var "SIMLI_FACE_ID"
add_var "CARTESIA_API_KEY"
add_var "ELEVENLABS_API_KEY"
add_var "LUNA_MODE"
add_var "SENTRY_DSN"
add_var "OPENAI_VOICE_NAME"
add_var "OPENAI_REALTIME_MODEL"

# Joindre avec des virgules
vars_string=$(IFS=,; echo "${update_vars[*]}")

echo "Deploiement $SERVICE -> $REGION..."
echo "Variables mises a jour : ${vars_string}"
gcloud run deploy "$SERVICE" \
  --source=. \
  --region="$REGION" \
  --project="$PROJECT" \
  --update-env-vars="$vars_string" \
  "$@"
