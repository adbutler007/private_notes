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
uv pip install py2app || echo "py2app already installed"
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
    echo "To create DMG for distribution:"
    echo "  ./create_dmg.sh"
    echo ""
else
    echo "✗ Build failed!"
    exit 1
fi
