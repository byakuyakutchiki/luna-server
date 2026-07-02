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
update_vars+=("FOUNDATION_TEST_MODE=${FOUNDATION_TEST_MODE:-false}")
update_vars+=("LUNA_TEST_MODE=${LUNA_TEST_MODE:-false}")
# Détection d'urgence vocale Iris : ACTIVE, mais en mode OBSERVATION (dry-run) pour le rollout.
# Détecte + journalise + Iris rassure, SANS envoyer de SMS/appel réel.
# Pour forcer une simulation : VOICE_EMERGENCY_DRY_RUN=true dans .env ou --update-env-vars.
update_vars+=("VOICE_EMERGENCY_ENABLED=true")
update_vars+=("VOICE_EMERGENCY_DRY_RUN=${VOICE_EMERGENCY_DRY_RUN:-false}")
update_vars+=("GUARDIAN_SMS_ENABLED=${GUARDIAN_SMS_ENABLED:-true}")
update_vars+=("GUARDIAN_CALL_ENABLED=${GUARDIAN_CALL_ENABLED:-true}")
update_vars+=("KARAOKE_DRAFTS_BUCKET=luna-karaoke-drafts-674304336025")  # brouillons karaoké (GCS)

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
# Email — Gmail OAuth (voie GRATUITE prioritaire : envoi depuis le Gmail du fondateur, inbox)
# Le redirect DOIT pointer vers la prod (pas le localhost du .env) et etre enregistre dans la Console Google.
add_var "GOOGLE_OAUTH_CLIENT_ID"
add_var "GOOGLE_OAUTH_CLIENT_SECRET"
update_vars+=("GOOGLE_OAUTH_REDIRECT_URI=https://luna-beta-674304336025.europe-west1.run.app/api/email/oauth/callback")
# Mode test fondateur : si "true", les emails/SMS sont simulés (aucun envoi réel)

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
