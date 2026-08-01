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
mkdir -p "$APP_DIR/build/gen" "$APP_DIR/build/obj" "$APP_DIR/build/apk" "$APP_DIR/build/libs"

# Optional Android AAR dependencies for isolated POCs. If android-app/libs/*.aar is absent, build stays legacy.
OPTIONAL_CLASSES=""
OPTIONAL_CLASS_JARS=""
OPTIONAL_JNI_DIRS=""
if compgen -G "$APP_DIR/libs/*.aar" > /dev/null; then
    for aar in "$APP_DIR"/libs/*.aar; do
        [ -f "$aar" ] || continue
        name="$(basename "$aar" .aar)"
        out="$APP_DIR/build/aar-$name"
        echo "[opt] AAR detected: $aar"
        mkdir -p "$out"
        (cd "$out" && jar xf "$aar")
        if [ -f "$out/classes.jar" ]; then
            OPTIONAL_CLASSES="$OPTIONAL_CLASSES:$out/classes.jar"
            OPTIONAL_CLASS_JARS="$OPTIONAL_CLASS_JARS $out/classes.jar"
        fi
        if [ -d "$out/jni" ]; then
            OPTIONAL_JNI_DIRS="$OPTIONAL_JNI_DIRS $out/jni"
        fi
    done
fi

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
JAVAC_CP="$PLATFORM$OPTIONAL_CLASSES"
javac \
    -source 11 -target 11 \
    -classpath "$JAVAC_CP" \
    -d "$APP_DIR/build/obj" \
    @"$APP_DIR/build/sources.txt" 2>&1

# 4. Create DEX
echo "[4/6] Create DEX..."
D8_INPUTS=$(find "$APP_DIR/build/obj" -name "*.class")
if [ -n "$OPTIONAL_CLASS_JARS" ]; then D8_INPUTS="$D8_INPUTS $OPTIONAL_CLASS_JARS"; fi
"$BUILD_TOOLS/d8" \
    --lib "$PLATFORM" \
    --output "$APP_DIR/build" \
    $D8_INPUTS

# 5. Add DEX to APK
echo "[5/6] Package APK..."
cd "$APP_DIR/build"
cp apk/base.apk luna-unsigned.apk
# Add classes.dex into the APK
zip -j luna-unsigned.apk classes.dex
if [ -n "$OPTIONAL_JNI_DIRS" ]; then
    echo "[opt] Packaging optional native libraries..."
    for jni_dir in $OPTIONAL_JNI_DIRS; do
        (cd "$jni_dir" && find . -type f -name "*.so" -print | while read so; do
            abi="$(dirname "$so" | sed 's#^./##')"
            mkdir -p "$APP_DIR/build/apk_libs/lib/$abi"
            cp "$so" "$APP_DIR/build/apk_libs/lib/$abi/"
        done)
    done
    (cd "$APP_DIR/build/apk_libs" && zip -r "$APP_DIR/build/luna-unsigned.apk" lib >/dev/null)
fi

# Align
zipalign -f 4 luna-unsigned.apk luna-aligned.apk

# 6. Sign
echo "[6/6] Sign APK..."
KEYSTORE="$APP_DIR/luna.keystore"
KEYSTORE_PASS="${KEYSTORE_PASS:?KEYSTORE_PASS non defini — lancez: export KEYSTORE_PASS=<motdepasse>}"

if [ ! -f "$KEYSTORE" ]; then
    keytool -genkeypair \
        -keystore "$KEYSTORE" \
        -alias luna \
        -keyalg RSA -keysize 2048 \
        -validity 10000 \
        -storepass "$KEYSTORE_PASS" \
        -keypass "$KEYSTORE_PASS" \
        -dname "CN=Luna YAWatch, OU=Proprio, O=YAWatch, L=Paris, ST=IDF, C=FR"
fi

apksigner sign \
    --ks "$KEYSTORE" \
    --ks-key-alias luna \
    --ks-pass "pass:$KEYSTORE_PASS" \
    --key-pass "pass:$KEYSTORE_PASS" \
    --out luna-proprio.apk \
    luna-aligned.apk

# Copy to static for download
cp luna-proprio.apk "$APP_DIR/../static/luna-proprio.apk"

echo ""
echo "=== APK cree avec succes ==="
echo "  Fichier: $APP_DIR/build/luna-proprio.apk"
echo "  Download: /static/luna-proprio.apk"
ls -lh luna-proprio.apk
