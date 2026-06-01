#!/bin/bash
# phone_snapshot.sh — Capture de preuves téléphone pour le banc de test Luna
# Usage : ./tools/agents/phone_snapshot.sh
# Dépendance : adb installé et téléphone autorisé (adb devices → "device")
# ⚠️  Ne lance aucune action sensible : observe uniquement

set -e

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
SNAP_DIR="$REPO_ROOT/docs/AGENTS_COLLABORATION/phone_tests/$(date +%Y-%m-%d_%H-%M)"

echo "=== Luna Phone Snapshot ==="
echo "Dossier : $SNAP_DIR"

# Vérification ADB
STATUS=$(adb devices 2>/dev/null | grep -v "List of devices" | grep -v "^$" | awk '{print $2}' | head -1)
if [ "$STATUS" != "device" ]; then
  echo "❌ Téléphone non connecté ou non autorisé. Statut : ${STATUS:-absent}"
  echo "   → Branche le téléphone, active le débogage USB, accepte la popup ADB."
  exit 1
fi
echo "✅ Téléphone connecté"

mkdir -p "$SNAP_DIR"

# 1. ADB devices
adb devices > "$SNAP_DIR/adb_devices.txt" 2>&1
echo "✅ adb_devices.txt"

# 2. Screenshot
adb exec-out screencap -p > "$SNAP_DIR/screen.png" 2>&1
SIZE=$(wc -c < "$SNAP_DIR/screen.png")
if [ "$SIZE" -gt 10000 ]; then
  echo "✅ screen.png ($SIZE bytes)"
else
  echo "⚠️  screen.png trop petit ($SIZE bytes) — possible échec"
fi

# 3. Logcat court (300 dernières lignes)
adb logcat -d -v time 2>/dev/null | tail -300 > "$SNAP_DIR/logcat_tail.txt"
LINES=$(wc -l < "$SNAP_DIR/logcat_tail.txt")
echo "✅ logcat_tail.txt ($LINES lignes)"

# 4. Logcat filtré Luna/WebView uniquement
adb logcat -d -v time 2>/dev/null | grep -iE "fr\.yawatch|luna|WebViewFactory|chromium|SpeechReco|getUserMedia|AudioRecord|speech|visio|microphone" > "$SNAP_DIR/logcat_luna.txt" 2>/dev/null || true
echo "✅ logcat_luna.txt ($(wc -l < "$SNAP_DIR/logcat_luna.txt") lignes filtrées)"

# 5. App info
{
  echo "=== Package Luna ==="
  adb shell pm list packages 2>/dev/null | grep -iE "luna|yawatch"
  echo ""
  echo "=== Device ==="
  echo "Manufacturer: $(adb shell getprop ro.product.manufacturer 2>/dev/null)"
  echo "Model: $(adb shell getprop ro.product.model 2>/dev/null)"
  echo "Android: $(adb shell getprop ro.build.version.release 2>/dev/null)"
  echo "SDK: $(adb shell getprop ro.build.version.sdk 2>/dev/null)"
  echo ""
  echo "=== Luna APK ==="
  adb shell dumpsys package fr.yawatch.luna 2>/dev/null | grep -E "versionName|versionCode|firstInstall|lastUpdate|dataDir" | head -10
  echo ""
  echo "=== Chrome/WebView ==="
  adb shell dumpsys package com.android.chrome 2>/dev/null | grep -E "versionName|versionCode" | head -3
  adb shell dumpsys package com.google.android.webview 2>/dev/null | grep -E "versionName|versionCode" | head -3
} > "$SNAP_DIR/app_info.txt" 2>/dev/null
echo "✅ app_info.txt"

echo ""
echo "=== Résumé ==="
ls -lh "$SNAP_DIR/"
echo ""
echo "Pour pousser sur GitHub :"
echo "  git add docs/AGENTS_COLLABORATION/phone_tests/"
echo "  git commit -m 'test(017): snapshot téléphone $(date +%Y-%m-%d_%H-%M)'"
echo "  git push origin main"
