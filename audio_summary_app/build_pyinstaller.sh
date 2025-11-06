#!/bin/bash
set -e

echo "Building Private Notes with PyInstaller..."
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
    --name="Private Notes" \
    --windowed \
    --icon=assets/icon.icns \
    --osx-bundle-identifier=com.privatenotes.app \
    --target-arch=arm64 \
    --noconfirm \
    --clean \
    --log-level=INFO \
    --runtime-hook=pyi_rth_qt6.py \
    --hidden-import=audio_summary_app \
    --hidden-import=audio_summary_app.gui \
    --hidden-import=audio_summary_app.gui.app \
    --hidden-import=audio_summary_app.gui.meeting_browser \
    --hidden-import=audio_summary_app.gui.settings_window \
    --hidden-import=audio_summary_app.gui.first_run_wizard \
    --hidden-import=audio_summary_app.gui.recording_controller \
    --hidden-import=mlx \
    --hidden-import=mlx_whisper \
    --collect-all=mlx_whisper \
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
    "dist/Private Notes.app/Contents/Info.plist" 2>/dev/null || \
/usr/libexec/PlistBuddy -c "Set :LSUIElement true" \
    "dist/Private Notes.app/Contents/Info.plist"

/usr/libexec/PlistBuddy -c "Add :LSMinimumSystemVersion string 11.0" \
    "dist/Private Notes.app/Contents/Info.plist" 2>/dev/null || \
/usr/libexec/PlistBuddy -c "Set :LSMinimumSystemVersion 11.0" \
    "dist/Private Notes.app/Contents/Info.plist"

/usr/libexec/PlistBuddy -c "Add :NSMicrophoneUsageDescription string 'Private Notes needs microphone access to record and transcribe meetings.'" \
    "dist/Private Notes.app/Contents/Info.plist" 2>/dev/null || \
/usr/libexec/PlistBuddy -c "Set :NSMicrophoneUsageDescription 'Private Notes needs microphone access to record and transcribe meetings.'" \
    "dist/Private Notes.app/Contents/Info.plist"

/usr/libexec/PlistBuddy -c "Add :NSAppleEventsUsageDescription string 'Private Notes may interact with other apps.'" \
    "dist/Private Notes.app/Contents/Info.plist" 2>/dev/null || \
/usr/libexec/PlistBuddy -c "Set :NSAppleEventsUsageDescription 'Private Notes may interact with other apps.'" \
    "dist/Private Notes.app/Contents/Info.plist"

echo "✓ Info.plist updated"
echo ""

# Check if build succeeded
if [ -d "dist/Private Notes.app" ]; then
    echo "✓ Build successful!"
    echo ""
    echo "App location: dist/Private Notes.app"
    echo ""
    echo "To test the app:"
    echo "  open 'dist/Private Notes.app'"
    echo ""
    echo "To create distribution package:"
    echo "  cd dist && zip -r PrivateNotes-0.1.0.zip 'Private Notes.app'"
    echo ""
else
    echo "✗ Build failed!"
    exit 1
fi
