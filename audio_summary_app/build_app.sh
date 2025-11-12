#!/bin/bash
# Build script for Audio Summary macOS app

set -e  # Exit on error

echo "Building Audio Summary.app..."
echo "=============================="
echo ""

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist
echo "✓ Cleaned"
echo ""

# Install py2app if needed
echo "Checking py2app..."
uv pip install py2app >/dev/null 2>&1 || echo "py2app already installed"
echo ""

# Build the app
echo "Building with py2app..."
uv run python setup.py py2app
echo ""

# Check if build succeeded
if [ -d "dist/Audio Summary.app" ]; then
    echo "✓ Build successful!"
    echo ""
    echo "App location: dist/Audio Summary.app"
    echo ""
    echo "To test the app:"
    echo "  open 'dist/Audio Summary.app'"
    echo ""
    echo "Creating distribution zip..."
    VERSION=$(sed -n 's/^version = \"\(.*\)\"/\1/p' pyproject.toml | head -n1)
    (cd dist && zip -qr "AudioSummary-${VERSION}.zip" 'Audio Summary.app')
    echo "✓ Created dist/AudioSummary-${VERSION}.zip"
    echo ""
    echo "SHA256 (use in Homebrew cask):"
    shasum -a 256 "dist/AudioSummary-${VERSION}.zip" | awk '{print $1}'
    echo ""
else
    echo "✗ Build failed!"
    exit 1
fi
