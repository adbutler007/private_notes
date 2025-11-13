#!/bin/bash
set -euo pipefail

# Usage:
#   ./setup_notary_api.sh ISSUER_ID KEY_ID /path/to/AuthKey_KEYID.p8 [profile]
# or provide env vars ISSUER_ID, KEY_ID, KEY_PATH, PROFILE

ISSUER_ID=${1:-${ISSUER_ID:-}}
KEY_ID=${2:-${KEY_ID:-}}
KEY_PATH=${3:-${KEY_PATH:-}}
PROFILE=${4:-${PROFILE:-audio-summary-notary-api}}

if [ -z "${ISSUER_ID}" ] || [ -z "${KEY_ID}" ] || [ -z "${KEY_PATH}" ]; then
  echo "Provide ISSUER_ID, KEY_ID and KEY_PATH (to .p8)." >&2
  echo "Example: ./setup_notary_api.sh 12345678-ABCD-... ABCDEFGHIJ ~/.appstoreconnect/AuthKey_ABCDEFGHIJ.p8" >&2
  exit 2
fi

if [ ! -f "$KEY_PATH" ]; then
  echo "Key file not found: $KEY_PATH" >&2
  exit 2
fi

echo "Storing notarytool credentials in keychain profile: $PROFILE"
xcrun notarytool store-credentials "$PROFILE" \
  --issuer "$ISSUER_ID" \
  --key-id "$KEY_ID" \
  --key "$KEY_PATH"

echo "✓ Stored. Use NOTARY_PROFILE=$PROFILE in builds."

