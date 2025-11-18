#!/usr/bin/env bash
# build_app.sh
# Build Audio Summary menu-bar app for distribution
# Per spec §7 Phase 4 - Hardening & packaging

set -e  # Exit on error

VERSION="${1:-0.2.0}"  # Default to 0.2.0 if not specified
APP_NAME="Audio Summary"
BUNDLE_ID="com.audiosummary.gui"
BUILD_DIR=".build"
DIST_DIR="dist"

echo "=== Building Audio Summary GUI v${VERSION} ==="

# 1. Clean previous builds
echo "1. Cleaning previous builds..."
rm -rf "$BUILD_DIR" "$DIST_DIR"
mkdir -p "$DIST_DIR"

# 2. Build release binary
echo "2. Building release binary..."
swift build -c release

# 3. Create app bundle structure
echo "3. Creating app bundle..."
APP_BUNDLE="$DIST_DIR/${APP_NAME}.app"
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"

# 4. Copy binary
echo "4. Copying binary..."
cp "$BUILD_DIR/release/AudioSummaryGUI" "$APP_BUNDLE/Contents/MacOS/${APP_NAME}"

# 5. Create Info.plist
echo "5. Creating Info.plist..."
cat > "$APP_BUNDLE/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>${APP_NAME}</string>
    <key>CFBundleIdentifier</key>
    <string>${BUNDLE_ID}</string>
    <key>CFBundleName</key>
    <string>${APP_NAME}</string>
    <key>CFBundleDisplayName</key>
    <string>${APP_NAME}</string>
    <key>CFBundleVersion</key>
    <string>${VERSION}</string>
    <key>CFBundleShortVersionString</key>
    <string>${VERSION}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>CFBundleSupportedPlatforms</key>
    <array>
        <string>MacOSX</string>
    </array>
    <key>LSMinimumSystemVersion</key>
    <string>13.0</string>
    <key>NSScreenCaptureDescription</key>
    <string>Audio Summary needs screen recording permission to capture audio from Zoom/Teams calls for transcription and summarization. All audio is processed locally on your device.</string>
    <key>NSMicrophoneUsageDescription</key>
    <string>Audio Summary can use your microphone as a fallback when screen capture is unavailable.</string>
    <key>NSUserNotificationUsageDescription</key>
    <string>Audio Summary sends notifications when summaries are ready.</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>DTPlatformName</key>
    <string>macosx</string>
    <key>DTSDKName</key>
    <string>macosx</string>
</dict>
</plist>
EOF

# 6. Create PkgInfo
echo "6. Creating PkgInfo..."
echo -n "APPL????" > "$APP_BUNDLE/Contents/PkgInfo"

# 7. Set executable permissions
echo "7. Setting permissions..."
chmod +x "$APP_BUNDLE/Contents/MacOS/${APP_NAME}"

echo ""
echo "=== Build Complete ==="
echo "App bundle: $APP_BUNDLE"
echo "Version: $VERSION"
echo ""
echo "To test the app:"
echo "  open \"$APP_BUNDLE\""
echo ""
echo "To sign and notarize:"
echo "  ./sign_and_notarize.sh $VERSION"
echo ""
