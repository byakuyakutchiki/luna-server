#!/bin/bash
# GitHub Polling Script — Auto-pull + merge Codex commits + deploy
# Usage: ./tools/agents/github_poller.sh
# Runs forever, polling every 5 minutes

REPO_DIR="/home/ludo/PROJETS/IA_WATCH/PROPRIO/serveur"
LOG_FILE="/home/ludo/PROJETS/IA_WATCH/PROPRIO/serveur/tools/agents/poller.log"
DEPLOY_SAFE=1  # Set to 0 if unsafe commits detected

mkdir -p "$(dirname "$LOG_FILE")"

echo "=== GitHub Poller started at $(date -Iseconds) ===" >> "$LOG_FILE"
echo "Repo: $REPO_DIR" >> "$LOG_FILE"
echo "Interval: 300s (5 min)" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

while true; do
    cd "$REPO_DIR" || { echo "ERROR: cannot cd to $REPO_DIR" >> "$LOG_FILE"; sleep 300; continue; }

    # Fetch remote
    git fetch origin main >> "$LOG_FILE" 2>&1

    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse origin/main)

    if [ "$LOCAL" = "$REMOTE" ]; then
        echo "$(date '+%H:%M:%S') — Pas de nouveau commit" >> "$LOG_FILE"
    else
        echo "$(date '+%H:%M:%S') — NOUVEAUX COMMITS detectes : $LOCAL -> $REMOTE" >> "$LOG_FILE"

        # Show new commits
        echo "Commits entrants :" >> "$LOG_FILE"
        git log --oneline "$LOCAL..$REMOTE" >> "$LOG_FILE"

        # Detect Codex commits
        CODEX_COMMITS=$(git log --oneline "$LOCAL..$REMOTE" | grep -i codex || true)
        if [ -n "$CODEX_COMMITS" ]; then
            echo "COMMITS CODEX DETECTES :" >> "$LOG_FILE"
            echo "$CODEX_COMMITS" >> "$LOG_FILE"
        fi

        # Detect unsafe keywords (sensitive actions)
        UNSAFE=$(git log --oneline "$LOCAL..$REMOTE" | grep -iE "twilio|sms|email|appel|paiement|reservation|suppression|delete|secret|password|cle|api_key" || true)
        if [ -n "$UNSAFE" ]; then
            echo "ALERTE — mots-cles sensibles detectes, deploiement BLOQUE :" >> "$LOG_FILE"
            echo "$UNSAFE" >> "$LOG_FILE"
            DEPLOY_SAFE=0
        else
            DEPLOY_SAFE=1
        fi

        # Pull / merge
        git merge --no-edit origin/main >> "$LOG_FILE" 2>&1
        MERGE_STATUS=$?

        if [ $MERGE_STATUS -eq 0 ]; then
            echo "$(date '+%H:%M:%S') — Merge OK ($(git rev-parse --short HEAD))" >> "$LOG_FILE"

            # Deploy if safe
            if [ "$DEPLOY_SAFE" -eq 1 ]; then
                echo "$(date '+%H:%M:%S') — Deploiement Cloud Run lance..." >> "$LOG_FILE"
                gcloud run deploy luna-beta \
                    --source . \
                    --region europe-west1 \
                    --project crypto-parser-475411-k4 \
                    --quiet >> "$LOG_FILE" 2>&1
                DEPLOY_STATUS=$?
                if [ $DEPLOY_STATUS -eq 0 ]; then
                    echo "$(date '+%H:%M:%S') — Deploiement OK" >> "$LOG_FILE"
                else
                    echo "$(date '+%H:%M:%S') — ERREUR deploiement (code $DEPLOY_STATUS)" >> "$LOG_FILE"
                fi
            else
                echo "$(date '+%H:%M:%S') — Deploiement SKIP (commits sensibles detectes)" >> "$LOG_FILE"
            fi
        else
            echo "$(date '+%H:%M:%S') — ERREUR merge (code $MERGE_STATUS)" >> "$LOG_FILE"
        fi

        echo "---" >> "$LOG_FILE"
    fi

    sleep 300
done
