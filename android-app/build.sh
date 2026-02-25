#!/bin/bash
# Build Luna Proprio APK
# Usage: ./build.sh
set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
SDK_ROOT="${ANDROID_HOME:-$HOME/Android/Sdk}"
BUILD_TOOLS="$SDK_ROOT/build-tools/35.0.1"
PLATFORM="$SDK_ROOT/platforms/android-35/android.jar"
AAPT2="$BUILD_TOOLS/aapt2"

echo "=== Build Luna Proprio APK ==="

# Clean
rm -rf "$APP_DIR/build"
mkdir -p "$APP_DIR/build/gen" "$APP_DIR/build/obj" "$APP_DIR/build/apk"

# 1. Compile resources
echo "[1/6] Compile resources..."
"$AAPT2" compile --dir "$APP_DIR/res" -o "$APP_DIR/build/compiled_res.zip"

# 2. Link resources + generate R.java
echo "[2/6] Link resources..."
"$AAPT2" link \
    -o "$APP_DIR/build/apk/base.apk" \
    -I "$PLATFORM" \
    --manifest "$APP_DIR/AndroidManifest.xml" \
    --java "$APP_DIR/build/gen" \
    "$APP_DIR/build/compiled_res.zip" \
    --auto-add-overlay

# 3. Compile Java
echo "[3/6] Compile Java..."
find "$APP_DIR/java" "$APP_DIR/build/gen" -name "*.java" > "$APP_DIR/build/sources.txt"
javac \
    -source 11 -target 11 \
    -classpath "$PLATFORM" \
    -d "$APP_DIR/build/obj" \
    @"$APP_DIR/build/sources.txt" 2>&1

# 4. Create DEX
echo "[4/6] Create DEX..."
"$BUILD_TOOLS/d8" \
    --lib "$PLATFORM" \
    --output "$APP_DIR/build" \
    $(find "$APP_DIR/build/obj" -name "*.class")

# 5. Add DEX to APK
echo "[5/6] Package APK..."
cd "$APP_DIR/build"
cp apk/base.apk luna-unsigned.apk
# Add classes.dex into the APK
zip -j luna-unsigned.apk classes.dex

# Align
zipalign -f 4 luna-unsigned.apk luna-aligned.apk

# 6. Sign
echo "[6/6] Sign APK..."
KEYSTORE="$APP_DIR/luna.keystore"
if [ ! -f "$KEYSTORE" ]; then
    keytool -genkeypair \
        -keystore "$KEYSTORE" \
        -alias luna \
        -keyalg RSA -keysize 2048 \
        -validity 10000 \
        -storepass luna2026 \
        -keypass luna2026 \
        -dname "CN=Luna YAWatch, OU=Proprio, O=YAWatch, L=Paris, ST=IDF, C=FR"
fi

apksigner sign \
    --ks "$KEYSTORE" \
    --ks-key-alias luna \
    --ks-pass pass:luna2026 \
    --key-pass pass:luna2026 \
    --out luna-proprio.apk \
    luna-aligned.apk

# Copy to static for download
cp luna-proprio.apk "$APP_DIR/../static/luna-proprio.apk"

echo ""
echo "=== APK cree avec succes ==="
echo "  Fichier: $APP_DIR/build/luna-proprio.apk"
echo "  Download: /static/luna-proprio.apk"
ls -lh luna-proprio.apk
