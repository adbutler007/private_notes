#!/bin/bash
set -euo pipefail

# Re-zip, submit for notarization using Apple ID profile, poll, staple when accepted.
# Usage: NOTARY_PROFILE=audio-summary-notary ./resubmit_notary.sh [timeout_seconds]

PROFILE=${NOTARY_PROFILE:-audio-summary-notary}
TIMEOUT=${1:-1200} # default 20 minutes

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_PATH="$ROOT_DIR/dist/Audio Summary.app"
ZIP_PATH="$ROOT_DIR/dist/AudioSummary-$(awk -F '"' '/^version =/{print $2; exit}' "$ROOT_DIR/pyproject.toml").zip"

if [ ! -d "$APP_PATH" ]; then
  echo "App not found: $APP_PATH" >&2
  exit 2
fi

echo "Repacking $APP_PATH -> $ZIP_PATH"
rm -f "$ZIP_PATH"
ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$ZIP_PATH"

echo "Submitting to Apple Notary Service with profile: $PROFILE (timeout ${TIMEOUT}s)"
SUBMIT_OUT=$(xcrun notarytool submit "$ZIP_PATH" --keychain-profile "$PROFILE" --progress 2>&1 || true)
echo "$SUBMIT_OUT" | sed -n '1,50p'

SUB_ID=$(printf "%s" "$SUBMIT_OUT" | awk '/^  id: /{print $2; exit}')
if [ -z "$SUB_ID" ]; then
  echo "Could not parse submission ID; aborting." >&2
  exit 3
fi
echo "Submission id: $SUB_ID"

START=$(date +%s)
while true; do
  INFO_OUT=$(xcrun notarytool info "$SUB_ID" --keychain-profile "$PROFILE" 2>&1 || true)
  STATUS=$(printf "%s" "$INFO_OUT" | awk '/^  status: /{print $2; exit}')
  echo "Status: ${STATUS:-unknown}"
  if [ "$STATUS" = "Accepted" ]; then
    echo "Accepted. Stapling..."
    xcrun stapler staple "$APP_PATH"
    echo "Verifying Gatekeeper acceptance..."
    spctl --assess --type exec -vv "$APP_PATH" || true
    codesign --verify --deep --strict --verbose=2 "$APP_PATH"
    echo "Rebuilding zip after stapling..."
    rm -f "$ZIP_PATH"
    ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$ZIP_PATH"
    SHA=$(shasum -a 256 "$ZIP_PATH" | awk '{print $1}')
    echo "New SHA256: $SHA"
    exit 0
  fi
  NOW=$(date +%s)
  ELAPSED=$((NOW-START))
  if [ $ELAPSED -ge $TIMEOUT ]; then
    echo "Timeout (${TIMEOUT}s) reached. Current status: ${STATUS:-unknown}."
    echo "You can continue polling with:"
    echo "  xcrun notarytool info $SUB_ID --keychain-profile $PROFILE"
    exit 0
  fi
  sleep 30
done

