#!/usr/bin/env bash
# build_app.sh
# Build Audio Summary menu-bar app for distribution
# Per spec §7 Phase 4 - Hardening & packaging

set -e  # Exit on error

VERSION="${1:-0.2.1}"  # Default to 0.2.1 if not specified
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

# 7. Bundle Python engine
echo "7. Bundling Python engine..."
RESOURCES_DIR="$APP_BUNDLE/Contents/Resources"
ENGINE_DIR="$RESOURCES_DIR/engine"
mkdir -p "$ENGINE_DIR"

# Copy Python source code
echo "   Copying Python source..."
cp -r ../src "$ENGINE_DIR/"
cp ../pyproject.toml "$ENGINE_DIR/"
cp ../uv.lock "$ENGINE_DIR/" 2>/dev/null || true
cp ../README.md "$ENGINE_DIR/" 2>/dev/null || echo "Audio Summary Engine" > "$ENGINE_DIR/README.md"

# Create a minimal startup script
cat > "$ENGINE_DIR/start_engine.sh" <<'ENGINESCRIPT'
#!/bin/bash
# Start the Audio Summary engine server
set -e

# Get the directory where this script lives
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Find uv in common locations
UV_PATH=""
for path in /opt/homebrew/bin/uv /usr/local/bin/uv ~/.local/bin/uv; do
    if [ -x "$path" ]; then
        UV_PATH="$path"
        break
    fi
done

if [ -z "$UV_PATH" ]; then
    echo "Error: uv not found. Please install: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Create venv if it doesn't exist and install dependencies
cd "$SCRIPT_DIR"
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment and installing dependencies..."
    "$UV_PATH" venv
    "$UV_PATH" pip install --python .venv/bin/python \
        "sounddevice>=0.4.6" \
        "numpy>=1.24.0" \
        "mlx-whisper>=0.1.0" \
        "parakeet-mlx>=0.1.0" \
        "ollama>=0.1.0" \
        "python-dateutil>=2.8.2" \
        "pydantic>=2.0.0" \
        "PyQt6>=6.6.0" \
        "psutil>=5.9.0" \
        "fastapi>=0.100.0" \
        "uvicorn[standard]>=0.23.0"
fi

# Run the engine
export PYTHONPATH="$SCRIPT_DIR/src:$PYTHONPATH"
exec .venv/bin/python -m audio_summary_app.engine.server
ENGINESCRIPT

chmod +x "$ENGINE_DIR/start_engine.sh"

# 8. Set executable permissions
echo "8. Setting permissions..."
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
