#!/bin/bash
# Pré-démarrage Luna : s'assurer qu'aucun autre Uvicorn n'écoute sur le port 8000.
set -e

PORT=8000
PIDS=$(ss -ltnp "sport = :$PORT" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | sort -u)

if [ -n "$PIDS" ]; then
    for pid in $PIDS; do
        # Ne pas tuer le processus systemd actuel (cas improbable au prestart)
        if [ "$pid" != "$$" ] && [ "$pid" != "$PPID" ]; then
            echo "Arrêt de l'ancien process Uvicorn PID=$pid sur le port $PORT"
            kill -TERM "$pid" 2>/dev/null || true
        fi
    done
    sleep 2
    # Force kill si encore présent
    PIDS2=$(ss -ltnp "sport = :$PORT" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | sort -u)
    for pid in $PIDS2; do
        if [ "$pid" != "$$" ] && [ "$pid" != "$PPID" ]; then
            kill -KILL "$pid" 2>/dev/null || true
        fi
    done
fi
