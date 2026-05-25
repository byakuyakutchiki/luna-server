#!/bin/bash
# Deploy Luna Beta sur Cloud Run
# Usage: ./deploy.sh
set -e

REGION="europe-west1"
SERVICE="luna-beta"
PROJECT="crypto-parser-475411-k4"

# Charger les vars critiques depuis .env local (source de vérité)
source "$(dirname "$0")/.env" 2>/dev/null || true

echo "Déploiement $SERVICE → $REGION..."
gcloud run deploy "$SERVICE" \
  --source=. \
  --region="$REGION" \
  --project="$PROJECT" \
  --update-env-vars="PROPRIO_PASSWORD=${PROPRIO_PASSWORD},PROPRIO_EMAIL=${PROPRIO_EMAIL},REDIS_URL=${REDIS_URL},SIMLI_API_KEY=${SIMLI_API_KEY},SIMLI_FACE_ID=${SIMLI_FACE_ID},CARTESIA_API_KEY=${CARTESIA_API_KEY},ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY},LUNA_MODE=${LUNA_MODE},SENTRY_DSN=${SENTRY_DSN},ENVIRONMENT=cloudrun,OPENAI_VOICE_NAME=${OPENAI_VOICE_NAME:-coral},OPENAI_REALTIME_MODEL=${OPENAI_REALTIME_MODEL:-gpt-4o-realtime-preview-2024-12-17}" \
  "$@"
