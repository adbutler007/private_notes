# Deployment Guide

This guide covers building and distributing Audio Summary as a macOS application.

## Prerequisites

- macOS with Apple Silicon (M1/M2/M3/M4)
- Python 3.11+
- uv package manager
- Homebrew (for distribution)

## Building the .app

### 1. Install py2app

```bash
uv pip install --extra macos
```

### 2. Build the application

```bash
./build_app.sh
```

This creates `dist/Audio Summary.app`

### 3. Test the app

```bash
open "dist/Audio Summary.app"
```

## Distribution via Homebrew

### Creating a Release

1. Tag the release:
```bash
git tag -a v0.1.0 -m "Release 0.1.0"
git push origin v0.1.0
```

2. Create a GitHub release with the .app bundled as a .zip

3. Get the SHA256 of the .zip:
```bash
shasum -a 256 AudioSummary-0.1.0.zip
```

### Homebrew Cask Formula

The formula is in `homebrew-cask/audio-summary.rb`.

To install via Homebrew:

```bash
brew tap adbutler007/audio-summary
brew install --cask audio-summary
```

## Manual Installation

Users can also download the .app directly:

1. Download from GitHub releases
2. Unzip
3. Move to /Applications
4. First run: Right-click → Open (to bypass Gatekeeper)

## Requirements for Users

Users need to install:

1. **Ollama** (for LLM):
   ```bash
   brew install ollama
   ```

2. **BlackHole** (for Zoom/Teams audio capture - optional):
   ```bash
   brew install blackhole-2ch
   ```

3. **Download LLM model** (first-time):
   ```bash
   ollama pull qwen3:4b-instruct
   ```

The First-Run Wizard guides users through this setup.

## Code Signing (Optional)

For wider distribution, you may want to code sign:

1. Get an Apple Developer account ($99/year)
2. Create certificates in Xcode
3. Sign the app:
   ```bash
   codesign --deep --force --sign "Developer ID Application: Your Name" "dist/Audio Summary.app"
   ```

4. Notarize with Apple:
   ```bash
   xcrun notarytool submit AudioSummary.zip --apple-id you@example.com --wait
   ```

## Troubleshooting

### "App is damaged" error
This happens when Gatekeeper blocks unsigned apps. Users should:
```bash
xattr -cr "/Applications/Audio Summary.app"
```

### Missing dependencies
Make sure py2app includes all required packages in setup.py

### MLX Whisper issues
MLX is Apple Silicon only. For Intel Macs, we'd need a separate build with faster-whisper backend.
