#!/bin/bash
# Reconnexion automatique ADB Wi-Fi pour Luna.
# Attend que le téléphone 192.168.1.62:5555 soit joignable et le connecte.
set -e

DEVICE="192.168.1.62:5555"
MAX_ATTEMPTS=60
ATTEMPT=0

# S'assurer que le daemon ADB est démarré
adb start-server >/dev/null 2>&1

# Attendre que le téléphone réponde sur le port ADB
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if adb connect "$DEVICE" 2>&1 | grep -q "connected to\|already connected"; then
        echo "ADB connecté à $DEVICE"
        adb devices -l
        exit 0
    fi
    ATTEMPT=$((ATTEMPT + 1))
    sleep 5
done

echo "Échec de connexion ADB à $DEVICE après $MAX_ATTEMPTS tentatives" >&2
exit 1
