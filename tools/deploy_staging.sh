#!/bin/bash
# Déploie sur luna-staging et lance les tests automatiques.
# Claude utilise ce script pour valider avant de toucher la prod.

set -e

PROJECT="crypto-parser-475411-k4"
REGION="europe-west1"
STAGING_SERVICE="luna-staging"
PROD_SERVICE="luna-beta"
STAGING_URL="https://luna-staging-674304336025.europe-west1.run.app"

echo "══════════════════════════════════════════════"
echo "  DEPLOY STAGING → luna-staging"
echo "══════════════════════════════════════════════"

# 1. Déployer sur staging
gcloud run deploy "$STAGING_SERVICE" \
  --source . \
  --region "$REGION" \
  --project "$PROJECT" \
  --quiet \
  --set-env-vars="ENV=staging" 2>&1 | tail -5

echo ""
echo "── Tests automatiques Iris..."
sleep 5

# 2. Lancer le test harness
python tools/test_iris_ws.py --url "$STAGING_URL"
TEST_EXIT=$?

echo ""
if [ $TEST_EXIT -eq 0 ]; then
  echo "✓ STAGING VALIDÉ — prêt pour prod si souhaité"
  echo "  Pour déployer en prod : gcloud run deploy $PROD_SERVICE --source . --region $REGION --project $PROJECT --quiet"
else
  echo "✗ TESTS ÉCHOUÉS — NE PAS DÉPLOYER EN PROD"
  echo "  Voir les logs de session dans /tmp/iris_sessions/"
  exit 1
fi
