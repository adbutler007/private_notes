#!/bin/bash
set -euo pipefail

# Generates a macOS .icns from assets/icon.png for Audio Summary
# Requirements: macOS, sips, iconutil

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SRC_PNG="$ROOT_DIR/assets/icon.png"
if [ ! -f "$SRC_PNG" ] && [ -f "$ROOT_DIR/../assets/icon.png" ]; then
  # Fallback to repo-root assets/icon.png
  SRC_PNG="$ROOT_DIR/../assets/icon.png"
fi
ICONSET_DIR="$ROOT_DIR/assets/AudioSummary.iconset"
OUT_ICNS="$ROOT_DIR/assets/icon.icns"

if [ ! -f "$SRC_PNG" ]; then
  echo "Source PNG not found: $SRC_PNG" >&2
  exit 1
fi

rm -rf "$ICONSET_DIR"
mkdir -p "$ICONSET_DIR"

echo "Generating iconset from: $SRC_PNG"
sips -z 16 16   "$SRC_PNG" --out "$ICONSET_DIR/icon_16x16.png" >/dev/null
sips -z 32 32   "$SRC_PNG" --out "$ICONSET_DIR/icon_16x16@2x.png" >/dev/null
sips -z 32 32   "$SRC_PNG" --out "$ICONSET_DIR/icon_32x32.png" >/dev/null
sips -z 64 64   "$SRC_PNG" --out "$ICONSET_DIR/icon_32x32@2x.png" >/dev/null
sips -z 128 128 "$SRC_PNG" --out "$ICONSET_DIR/icon_128x128.png" >/dev/null
sips -z 256 256 "$SRC_PNG" --out "$ICONSET_DIR/icon_128x128@2x.png" >/dev/null
sips -z 256 256 "$SRC_PNG" --out "$ICONSET_DIR/icon_256x256.png" >/dev/null
sips -z 512 512 "$SRC_PNG" --out "$ICONSET_DIR/icon_256x256@2x.png" >/dev/null
sips -z 512 512 "$SRC_PNG" --out "$ICONSET_DIR/icon_512x512.png" >/dev/null
cp "$SRC_PNG" "$ICONSET_DIR/icon_512x512@2x.png"  # 1024x1024

echo "Creating .icns -> $OUT_ICNS"
iconutil -c icns "$ICONSET_DIR" -o "$OUT_ICNS"
echo "✓ Wrote $OUT_ICNS"
