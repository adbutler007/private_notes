#!/bin/bash
set -euo pipefail

# Code sign, notarize, and staple the app bundle for macOS Gatekeeper
# Requirements:
# - Developer ID Application certificate installed in keychain
# - Notary credentials stored via: xcrun notarytool store-credentials <PROFILE> --apple-id <id> --team-id <team> --password <app-specific-pass>
# Environment:
#   DEVELOPER_ID="Developer ID Application: Your Name (TEAMID)"
#   NOTARY_PROFILE="your-notarytool-profile-name"

THIS_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$THIS_DIR/.." && pwd)"
APP_PATH="$ROOT_DIR/dist/Audio Summary.app"
ENTITLEMENTS="$ROOT_DIR/macos/entitlements.plist"
ZIP_PATH="$ROOT_DIR/dist/AudioSummary-$(awk -F '"' '/^version =/{print $2; exit}' "$ROOT_DIR/pyproject.toml").zip"

if [ ! -d "$APP_PATH" ]; then
  echo "App not found: $APP_PATH" >&2
  exit 1
fi

DEVELOPER_ID=${DEVELOPER_ID:-}
NOTARY_PROFILE=${NOTARY_PROFILE:-}
if [ -z "$DEVELOPER_ID" ]; then
  echo "DEVELOPER_ID is not set. Export DEVELOPER_ID=\"Developer ID Application: Full Name (TEAMID)\" and re-run." >&2
  exit 2
fi
if [ -z "$NOTARY_PROFILE" ]; then
  echo "NOTARY_PROFILE is not set. Export NOTARY_PROFILE=<notarytool-profile> and re-run." >&2
  exit 2
fi

echo "Signing nested binaries and frameworks..."
# Sign inner dylibs, .so, and executables first (compatible with macOS bash 3.2)
find "$APP_PATH" \( -name "*.dylib" -o -name "*.so" -o -path "*/Contents/MacOS/*" \) -type f -print0 \
| while IFS= read -r -d '' f; do
  echo "  codesign: $f"
  codesign --force --options runtime --timestamp \
    --entitlements "$ENTITLEMENTS" \
    --sign "$DEVELOPER_ID" "$f" || exit 1
done

# Sign embedded frameworks (sign the bundle directories)
find "$APP_PATH" -type d -name "*.framework" -print0 \
| while IFS= read -r -d '' fw; do
  echo "  codesign framework: $fw"
  codesign --force --options runtime --timestamp \
    --entitlements "$ENTITLEMENTS" \
    --sign "$DEVELOPER_ID" "$fw" || exit 1
done

echo "Signing the .app bundle..."
codesign --force --options runtime --timestamp \
  --entitlements "$ENTITLEMENTS" \
  --sign "$DEVELOPER_ID" "$APP_PATH"

echo "Verifying code signature..."
codesign --verify --deep --strict --verbose=2 "$APP_PATH"
spctl --assess --type exec -vv "$APP_PATH" || true

echo "Creating zip for notarization: $ZIP_PATH"
ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$ZIP_PATH"

echo "Submitting to Apple Notary Service..."
xcrun notarytool submit "$ZIP_PATH" --keychain-profile "$NOTARY_PROFILE" --wait

echo "Stapling notarization ticket..."
xcrun stapler staple "$APP_PATH"

echo "Verifying stapled app..."
spctl --assess --type exec -vv "$APP_PATH"
codesign --verify --deep --strict --verbose=2 "$APP_PATH"

echo "✓ App signed, notarized, and stapled"
