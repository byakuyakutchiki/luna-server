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

# Fonction helper : ajoute une variable seulement si elle est definie et non vide
add_var() {
  local name="$1"
  local val="${!name}"
  if [[ -n "$val" ]]; then
    update_vars+=("${name}=${val}")
  fi
}

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
add_var "GUARDIAN_SMS_ENABLED"
add_var "GUARDIAN_CALL_ENABLED"
# Twilio — SMS et appels vocaux (conciergerie + Guardian)
add_var "TWILIO_ACCOUNT_SID"
add_var "TWILIO_AUTH_TOKEN"
add_var "TWILIO_API_KEY"
add_var "TWILIO_API_SECRET"
add_var "TWILIO_PHONE_NUMBER"
add_var "TWILIO_SMS_FROM"
add_var "TWILIO_WHATSAPP_NUMBER"
# Email — SendGrid (distribution dossier Iris, conciergerie email)
add_var "SENDGRID_API_KEY"
add_var "LUNA_EMAIL_FROM"
add_var "LUNA_EMAIL_SENDER_NAME"
# Mode test fondateur : si "true", les emails/SMS sont simulés (aucun envoi réel)
add_var "FOUNDATION_TEST_MODE"

# Joindre avec des virgules
vars_string=$(IFS=,; echo "${update_vars[*]}")

IMAGE="europe-west1-docker.pkg.dev/${PROJECT}/cloud-run-source-deploy/${SERVICE}:$(date +%Y%m%d-%H%M%S)"

echo "Deploiement $SERVICE -> $REGION..."
echo "Image : $IMAGE"
echo "Variables mises a jour : ${vars_string}"

# Build local via Dockerfile (evite le builder Buildpacks de Cloud Run qui echoue)
docker build -t "$IMAGE" "$(dirname "$0")"
docker push "$IMAGE"

gcloud run deploy "$SERVICE" \
  --image="$IMAGE" \
  --region="$REGION" \
  --project="$PROJECT" \
  --update-env-vars="$vars_string" \
  "$@"
