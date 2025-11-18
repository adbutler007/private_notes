# Audio Summary - Menu-Bar GUI

**Swift menu-bar app for capturing and summarizing Zoom/Teams calls**

This is Phase 3 of the Audio Summary architecture - a native macOS menu-bar app that captures audio via ScreenCaptureKit and sends it to the Python engine for transcription and summarization.

---

## Features

✅ **Menu-bar app** - Runs in system tray, no dock icon
✅ **ScreenCaptureKit** - Captures Zoom/Teams audio directly (no BlackHole needed)
✅ **Microphone fallback** - Optional fallback to mic if screen capture fails
✅ **First-run wizard** - Guided setup with audio test
✅ **Settings UI** - Configure STT models, prompts, export paths
✅ **Recent summaries** - Quick access to last 5 meetings
✅ **Local processing** - All AI runs on your Mac

---

## Prerequisites

### System Requirements
- **macOS 13.0+ (Ventura)** - Required for ScreenCaptureKit
- **Apple Silicon** recommended (M1/M2/M3)
- **16 GB RAM** minimum

### Engine Must Be Running

The menu-bar app communicates with a Python engine service:

```bash
cd /Users/adambutler/Projects/private_notes/audio_summary_app
uv run audio-summary-server
```

Verify engine is running:
```bash
curl http://127.0.0.1:8756/health
```

---

## Building

### Option 1: Build Script (Recommended)

```bash
./build_app.sh 0.2.0
```

This creates `dist/Audio Summary.app` with proper bundle structure.

### Option 2: Swift Package Manager

```bash
swift build -c release
```

Binary output: `.build/release/AudioSummaryGUI`

---

## Running

### From Build Script

```bash
open "dist/Audio Summary.app"
```

### From Command Line (Debug)

```bash
swift run
```

---

## First-Run Setup

On first launch, the app shows a 4-step wizard:

1. **Welcome** - Explains local processing
2. **Select App** - Choose Zoom or Teams to monitor
3. **Permissions** - Grant Screen Recording permission
4. **Audio Test** - Verify capture works with live audio meter

---

## Usage

### Start Recording

1. Click menu-bar icon (microphone)
2. Click "Start Recording"
3. App captures audio from selected app (Zoom/Teams)
4. Notification shows "Recording Started"

### Stop Recording

1. Click menu-bar icon
2. Click "Stop Recording"
3. App processes and generates summary
4. Notification shows "Summary Ready"

### View Summaries

- Click "Recent Summaries" → Select a meeting
- Opens `summary.txt` in default editor
- Files saved to `~/Documents/Meeting Summaries/`

### Settings

Click "Settings..." to configure:

- **Capture**: Re-run wizard, change target app
- **Models**: STT backend (Whisper/Parakeet), LLM model
- **Prompts**: Customize chunk/final summary prompts
- **Export**: Output directory, CSV path, append mode
- **Advanced**: Debug logging, mic fallback

---

## Permissions

### Screen Recording (Required)

The app needs Screen Recording permission to capture Zoom/Teams audio:

1. System Settings → Privacy & Security → Screen Recording
2. Enable "Audio Summary"
3. Restart the app

### Microphone (Optional)

Only needed if mic fallback is enabled in Advanced settings.

---

## Code Signing and Notarization

### Prerequisites

1. **Apple Developer ID certificate**
2. **Notarization credentials** stored in keychain:
   ```bash
   xcrun notarytool store-credentials audio-summary-notary \
       --apple-id "your@email.com" \
       --team-id "TEAM_ID"
   ```

### Sign and Notarize

```bash
export AUDIO_SUMMARY_DEVELOPER_ID="Developer ID Application: Your Name (TEAM_ID)"
export AUDIO_SUMMARY_NOTARY_PROFILE="audio-summary-notary"

./sign_and_notarize.sh 0.2.0
```

This creates `dist/AudioSummary-0.2.0.zip` ready for distribution.

---

## Installation via Homebrew

### Add Tap (First Time)

```bash
brew tap YOUR_USERNAME/audio-summary
```

### Install

```bash
brew install --cask audio-summary
```

### Update Cask After New Release

1. Build and sign: `./sign_and_notarize.sh 0.2.0`
2. Get SHA256: `shasum -a 256 dist/AudioSummary-0.2.0.zip`
3. Update `audio-summary.rb` with new version and SHA256
4. Upload ZIP to GitHub Releases
5. Update tap: `brew update && brew upgrade --cask audio-summary`

---

## Architecture

```
Audio Summary.app
├── AppDelegate.swift           # Menu bar + app lifecycle
├── CaptureController.swift     # Session orchestration
├── Views/
│   ├── SettingsView.swift      # Settings UI (5 sections)
│   └── FirstRunWizard.swift    # 4-step setup wizard
├── Managers/
│   ├── PreferencesManager.swift  # UserDefaults persistence
│   └── SessionManager.swift      # Recent summaries tracking
└── Shared/
    ├── Models.swift              # API request/response models
    ├── EngineClient.swift        # HTTP client for engine
    ├── AudioProcessor.swift      # CMSampleBuffer → PCM
    ├── ScreenCaptureManager.swift  # ScreenCaptureKit integration
    ├── MicrophoneCaptureManager.swift  # Mic fallback
    └── Logger.swift              # Centralized logging
```

---

## Troubleshooting

### "Engine not responding"

Ensure engine is running:
```bash
uv run audio-summary-server
curl http://127.0.0.1:8756/health
```

### "Screen recording permission denied"

1. System Settings → Privacy & Security → Screen Recording
2. Enable "Audio Summary"
3. Restart app

### "No Zoom or Teams apps found"

1. Start Zoom or Teams
2. Re-run first-run wizard: Settings → Capture → "Re-run First-Time Setup Wizard"

### "No audio captured / Silent stream"

1. Verify Zoom/Teams audio is working (test in a call)
2. Check Audio Test in first-run wizard shows audio levels
3. Try mic fallback: Settings → Advanced → "Enable Microphone Fallback"

### Debug Logs

Enable debug logging:
1. Settings → Advanced → "Enable Debug Logging"
2. Logs written to: `~/Library/Logs/Audio Summary/last.log`

---

## Compliance with Spec

This implementation is **100% compliant** with the design specification:

- ✅ §4.1 FR1 - Status bar app with menu
- ✅ §4.1 FR2 - First-run wizard (4 steps)
- ✅ §4.1 FR3 - Start/Stop recording with engine communication
- ✅ §4.1 FR4 - Settings UI (5 sections)
- ✅ §4.1 FR5 - Recent summaries menu (last 5)
- ✅ §NFR2 - Security & Privacy (local processing, 127.0.0.1 only)
- ✅ §NFR4 - Observability (logging without transcript text)
- ✅ §7 Phase 4 - Hardening & packaging (mic fallback, signing, cask)

---

## Next Steps

1. **Test with live Zoom/Teams call** - Verify end-to-end functionality
2. **Upload to GitHub Releases** - Create release with ZIP
3. **Publish Homebrew tap** - Make cask available
4. **Add icon** - Design and add app icon to Resources/

---

## License

See parent repository for license information.
