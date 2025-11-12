#!/bin/bash
set -e

echo "Building Audio Summary with PyInstaller..."
echo "=========================================="
echo ""

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist
echo "✓ Cleaned"
echo ""

# Build the app
echo "Building with PyInstaller..."
uv run pyinstaller \
    --name="Audio Summary" \
    --windowed \
    --icon=assets/icon.icns \
    --osx-bundle-identifier=com.audiosummary.app \
    --target-arch=arm64 \
    --noconfirm \
    --clean \
    --log-level=INFO \
    --runtime-hook=pyi_rth_qt6.py \
    --add-data="qt.conf:." \
    --add-data="download_parakeet.py:." \
    --hidden-import=audio_summary_app \
    --hidden-import=audio_summary_app.gui \
    --hidden-import=audio_summary_app.gui.app \
    --hidden-import=audio_summary_app.gui.meeting_browser \
    --hidden-import=audio_summary_app.gui.settings_window \
    --hidden-import=audio_summary_app.gui.first_run_wizard \
    --hidden-import=audio_summary_app.gui.recording_controller \
    --hidden-import=mlx \
    --hidden-import=mlx_whisper \
    --hidden-import=parakeet_mlx \
    --collect-all=mlx_whisper \
    --collect-all=parakeet_mlx \
    --collect-all=mlx \
    --copy-metadata=PyQt6 \
    --exclude-module=matplotlib \
    --exclude-module=IPython \
    --exclude-module=jupyter \
    --exclude-module=torch \
    --exclude-module=tensorflow \
    --hidden-import=scipy \
    --hidden-import=scipy.signal \
    --collect-all=scipy \
    launch_gui.py

echo ""

# Customize Info.plist
echo "Customizing Info.plist..."
/usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" \
    "dist/Audio Summary.app/Contents/Info.plist" 2>/dev/null || \
/usr/libexec/PlistBuddy -c "Set :LSUIElement true" \
    "dist/Audio Summary.app/Contents/Info.plist"

/usr/libexec/PlistBuddy -c "Add :LSMinimumSystemVersion string 11.0" \
    "dist/Audio Summary.app/Contents/Info.plist" 2>/dev/null || \
/usr/libexec/PlistBuddy -c "Set :LSMinimumSystemVersion 11.0" \
    "dist/Audio Summary.app/Contents/Info.plist"

/usr/libexec/PlistBuddy -c "Add :NSMicrophoneUsageDescription string 'Audio Summary needs microphone access to record and transcribe meetings.'" \
    "dist/Audio Summary.app/Contents/Info.plist" 2>/dev/null || \
/usr/libexec/PlistBuddy -c "Set :NSMicrophoneUsageDescription 'Audio Summary needs microphone access to record and transcribe meetings.'" \
    "dist/Audio Summary.app/Contents/Info.plist"

/usr/libexec/PlistBuddy -c "Add :NSAppleEventsUsageDescription string 'Audio Summary may interact with other apps.'" \
    "dist/Audio Summary.app/Contents/Info.plist" 2>/dev/null || \
/usr/libexec/PlistBuddy -c "Set :NSAppleEventsUsageDescription 'Audio Summary may interact with other apps.'" \
    "dist/Audio Summary.app/Contents/Info.plist"

echo "✓ Info.plist updated"
echo ""

# Check if build succeeded
if [ -d "dist/Audio Summary.app" ]; then
    echo "✓ Build successful!"
    echo ""
    echo "App location: dist/Audio Summary.app"
    echo ""

    # Create distribution ZIP with proper symlink preservation
    echo "Creating distribution package..."
    cd dist
    # Use ditto to create a proper macOS archive that preserves symlinks
    VERSION=$(sed -n 's/^version = \"\(.*\)\"/\1/p' ../pyproject.toml | head -n1)
    ditto -c -k --sequesterRsrc --keepParent "Audio Summary.app" "AudioSummary-${VERSION}.zip"
    cd ..
    echo "✓ Distribution package created: dist/AudioSummary-${VERSION}.zip"
    echo ""

    echo "To test the app:"
    echo "  open 'dist/Audio Summary.app'"
    echo ""
else
    echo "✗ Build failed!"
    exit 1
fi
