#!/usr/bin/env bash
# sign_and_notarize.sh
# Code sign and notarize Audio Summary app
# Per spec §7 Phase 4 - Code signing and notarization

set -e  # Exit on error

VERSION="${1:-0.2.0}"
APP_NAME="Audio Summary"
DIST_DIR="dist"
APP_BUNDLE="$DIST_DIR/${APP_NAME}.app"
ZIP_FILE="$DIST_DIR/AudioSummary-${VERSION}.zip"

# Configuration
DEVELOPER_ID="${AUDIO_SUMMARY_DEVELOPER_ID:-Developer ID Application}"
NOTARY_PROFILE="${AUDIO_SUMMARY_NOTARY_PROFILE:-audio-summary-notary}"

echo "=== Signing and Notarizing Audio Summary v${VERSION} ==="
echo "Developer ID: $DEVELOPER_ID"
echo "Notary Profile: $NOTARY_PROFILE"
echo ""

# Check that app exists
if [ ! -d "$APP_BUNDLE" ]; then
    echo "ERROR: App bundle not found at $APP_BUNDLE"
    echo "Run ./build_app.sh first"
    exit 1
fi

# 1. Code sign the app
echo "1. Code signing..."
codesign --force --deep --sign "$DEVELOPER_ID" \
    --options runtime \
    --entitlements "AudioSummaryGUI.entitlements" \
    "$APP_BUNDLE"

echo "   Verifying signature..."
codesign --verify --verbose "$APP_BUNDLE"

# 2. Create ZIP for notarization
echo ""
echo "2. Creating ZIP archive..."
rm -f "$ZIP_FILE"
ditto -c -k --keepParent "$APP_BUNDLE" "$ZIP_FILE"

echo "   ZIP created: $ZIP_FILE"
echo "   Size: $(du -h "$ZIP_FILE" | cut -f1)"

# 3. Submit for notarization
echo ""
echo "3. Submitting to Apple for notarization..."
echo "   (This may take 5-15 minutes)"

xcrun notarytool submit "$ZIP_FILE" \
    --keychain-profile "$NOTARY_PROFILE" \
    --wait

# Check notarization status
SUBMISSION_ID=$(xcrun notarytool history \
    --keychain-profile "$NOTARY_PROFILE" \
    | head -2 | tail -1 | awk '{print $4}')

echo ""
echo "4. Checking notarization status..."
xcrun notarytool info "$SUBMISSION_ID" \
    --keychain-profile "$NOTARY_PROFILE"

# 5. Staple notarization ticket
echo ""
echo "5. Stapling notarization ticket..."
xcrun stapler staple "$APP_BUNDLE"

echo ""
echo "6. Creating final ZIP..."
rm -f "$ZIP_FILE"
ditto -c -k --keepParent "$APP_BUNDLE" "$ZIP_FILE"

# 7. Calculate SHA256
echo ""
echo "7. Calculating SHA256..."
SHA256=$(shasum -a 256 "$ZIP_FILE" | awk '{print $1}')

echo ""
echo "=== Signing and Notarization Complete ==="
echo "Signed app: $APP_BUNDLE"
echo "Distribution ZIP: $ZIP_FILE"
echo "SHA256: $SHA256"
echo ""
echo "Next steps:"
echo "1. Test the app:"
echo "   open \"$APP_BUNDLE\""
echo ""
echo "2. Update Homebrew cask with new version and SHA256"
echo ""
