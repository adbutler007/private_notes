# Audio Capture Prototype - Phase 2

**Swift ScreenCaptureKit prototype for capturing Zoom/Teams audio**

This is a command-line prototype that validates core functionality before building the full menu-bar GUI (Phase 3).

---

## Features

✅ Lists all running applications
✅ Filters for Zoom and Microsoft Teams
✅ Captures audio-only via ScreenCaptureKit
✅ Converts CMSampleBuffer → float32 PCM → base64
✅ Sends audio chunks to engine HTTP API
✅ Receives and displays generated summary

---

## Prerequisites

### System Requirements
- macOS 13.0+ (Ventura) for ScreenCaptureKit
- Xcode 14+ or Swift 5.9+
- Screen Recording permission (will be prompted on first run)

### Engine Must Be Running
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

### Option 1: Swift Package Manager (Recommended)
```bash
cd macos_capture_prototype
swift build
```

### Option 2: Xcode
```bash
cd macos_capture_prototype
open Package.swift  # Opens in Xcode
# Build and run from Xcode
```

---

## Running

### From Command Line
```bash
# Build first
swift build

# Run
./.build/debug/AudioCapturePrototype
```

### From Xcode
- Product → Run (⌘R)

---

## Usage

1. **Start the engine**
   ```bash
   uv run audio-summary-server
   ```

2. **Start Zoom or Teams meeting** (or just have the app running)

3. **Run the prototype**
   ```bash
   swift run
   ```

4. **Follow prompts**
   - Grant Screen Recording permission if prompted
   - Select target app if multiple found
   - Prototype will capture for 60 seconds (or until Ctrl+C)

5. **View summary**
   - Summary is displayed in console
   - Files saved to `~/Documents/Meeting Summaries/`

---

## Expected Output

```
=== Audio Capture Prototype - Phase 2 ===
Capturing audio from Zoom/Teams and sending to engine

1. Listing available applications...
   Found 47 running applications

2. Filtering for Zoom/Teams...
   Found 1 target app(s):
   [1] zoom.us (us.zoom.xos)

   Auto-selecting: zoom.us

3. Connecting to engine...
   Engine version: 1.0.0
   API version: 1
   STT backends: whisper, parakeet
   LLM models: qwen3:4b-instruct, llama3.2:3b, phi3:3.8b

4. Starting session...
   Session ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
   Session started successfully

5. Starting audio capture from zoom.us...
   Press Ctrl+C to stop (or capturing for 60s)

   Chunk 1: 48000 Hz, 96000 samples → buffered: 2.0s, queue: 0 segments
   Chunk 2: 48000 Hz, 96000 samples → buffered: 0.0s, queue: 1 segments
   ...

6. Stopping capture...
   Sent 30 total chunks

7. Stopping session and generating summary...
   This may take 30-60 seconds depending on transcript length...

=== Session Complete ===
Status: completed
Summary: /Users/adambutler/Documents/Meeting Summaries/summary_20251116_150422.txt
Data: /Users/adambutler/Documents/Meeting Summaries/data_20251116_150422.json
CSV: /Users/adambutler/Documents/Meeting Summaries/meetings.csv

--- Generated Summary ---
[Summary text here]
--- End Summary ---

=== Prototype Complete ===
```

---

## Permissions

### Screen Recording Permission

On first run, macOS will prompt:

> "AudioCapturePrototype" would like to record the contents of your screen.

**Click "Open System Settings"** and enable Screen Recording for the app.

You can manually grant permission:
1. System Settings → Privacy & Security → Screen Recording
2. Enable "AudioCapturePrototype"
3. Restart the app

---

## Architecture

```
AudioCapturePrototype
├── Models.swift               # API request/response models
├── EngineClient.swift         # HTTP client for engine
├── AudioProcessor.swift       # CMSampleBuffer → PCM conversion
├── ScreenCaptureManager.swift # ScreenCaptureKit integration
└── main.swift                 # Main console app logic
```

---

## Troubleshooting

### "No Zoom or Teams apps found running"
- Start Zoom or Teams
- Join a meeting (or just have the app open)
- Run prototype again

### "Engine not responding"
```bash
# Ensure engine is running
uv run audio-summary-server

# Check engine health
curl http://127.0.0.1:8756/health
```

### "Screen recording permission denied"
1. Go to System Settings → Privacy & Security → Screen Recording
2. Enable "AudioCapturePrototype"
3. Restart the app

### "No audio captured / Silent stream"
- Check Zoom/Teams audio settings (ensure not muted)
- Verify someone is speaking during capture
- Check engine logs for transcription activity
- Try a longer capture duration

### Build errors
```bash
# Clean build
swift package clean
swift build
```

---

## Limitations (Phase 2 Prototype)

This is a minimal prototype. The following are deferred to Phase 3:

- ❌ No GUI (console-only)
- ❌ Fixed 60-second capture duration
- ❌ No audio level monitoring
- ❌ Limited error recovery
- ❌ No app switching mid-capture
- ❌ No prompt customization

Phase 3 will add:
- ✅ Menu-bar GUI with start/stop
- ✅ Settings window for prompts
- ✅ First-run wizard with audio test
- ✅ Recent summaries menu
- ✅ Dynamic capture control

---

## Compliance with Spec

This prototype validates Phase 2 requirements from the spec (§7):

| Requirement | Status |
|-------------|--------|
| List SCShareableContent | ✅ |
| Filter Zoom/Teams | ✅ |
| Capture audio via ScreenCaptureKit | ✅ |
| Convert CMSampleBuffer → PCM | ✅ |
| POST to engine endpoints | ✅ |
| Print responses and summary | ✅ |

---

## Next Steps

Once this prototype is validated with live Zoom/Teams capture:

**Phase 3: Menu-Bar GUI**
- Convert to NSStatusItem app
- Add SwiftUI Settings window
- Implement first-run wizard
- Add Recent Summaries menu
- Polish UX and error handling
