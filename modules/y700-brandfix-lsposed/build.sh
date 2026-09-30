#!/bin/bash
# Build y700-brandfix.apk — LSPosed module: spoofs Build.BRAND/MANUFACTURER to
# "OnePlus" inside heytap / ColorOS / AIUnit processes (XiaoBu brand-check fix).
#
# Requirements: JDK 11+, Android SDK (build-tools with d8/aapt2/zipalign/apksigner,
# and a platforms/android-XX/android.jar).
# Override tool paths via env: JDK_HOME, BUILD_TOOLS, ANDROID_JAR
set -e
JDK="${JDK_HOME:-/d/AI/jdk17/jdk-17.0.20+8}"
BT="${BUILD_TOOLS:-/d/AI/Android/build-tools/34.0.0}"
AJAR="${ANDROID_JAR:-/d/AI/Android/platforms/android-34/android.jar}"
cd "$(dirname "$0")"
rm -rf build out && mkdir -p build/stub build/classes build/dex out

echo "[1/6] compile API stubs (compile-time only, not packed into the APK)"
"$JDK/bin/javac" -nowarn -d build/stub $(find stub -name "*.java")

echo "[2/6] compile module source"
"$JDK/bin/javac" -source 8 -target 8 -nowarn -bootclasspath "$AJAR" -classpath build/stub -d build/classes $(find src -name "*.java")

echo "[3/6] dex"
"$JDK/bin/java" -cp "$BT/lib/d8.jar" com.android.tools.r8.D8 --min-api 29 --output build/dex $(find build/classes -name "*.class" ! -name "*\$*")

echo "[4/6] aapt2 compile res + link"
"$BT/aapt2.exe" compile --dir res -o build/res.zip
"$BT/aapt2.exe" link -o build/base.apk --manifest AndroidManifest.xml -I "$AJAR" -A assets build/res.zip --min-sdk-version 29 --target-sdk-version 34

echo "[5/6] append dex + zipalign"
python - << 'PY'
import zipfile, shutil
shutil.copy('build/base.apk', 'build/unsigned.apk')
z = zipfile.ZipFile('build/unsigned.apk', 'a', zipfile.ZIP_STORED)
z.write('build/dex/classes.dex', 'classes.dex')
z.close()
print('   dex appended')
PY
"$BT/zipalign.exe" -f 4 build/unsigned.apk build/aligned.apk

echo "[6/6] sign (self-signed debug keystore, generated on first run)"
if [ ! -f debug.keystore ]; then
  "$JDK/bin/keytool" -genkeypair -keystore debug.keystore -alias k -storepass android -keypass android -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Y700 BrandFix,O=ZCode,C=CN"
fi
"$JDK/bin/java" -jar "$BT/lib/apksigner.jar" sign --ks debug.keystore --ks-pass pass:android --key-pass pass:android --out out/y700-brandfix.apk build/aligned.apk
"$JDK/bin/java" -jar "$BT/lib/apksigner.jar" verify out/y700-brandfix.apk
ls -la out/
echo "BUILD OK"
