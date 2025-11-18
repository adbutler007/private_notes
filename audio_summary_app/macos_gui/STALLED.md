# Audio Summary macOS GUI - Current Status

## Summary
The macOS GUI app is crashing on launch and not capturing audio properly. We've implemented device selection for BlackHole/Aggregate Device capture, but the app is unstable.

## What We've Implemented

### Device Selection Feature (Completed)
- Added `MicrophoneCaptureManager.getInputDevices()` to enumerate all audio input devices
- Added `startCapture(fromDevice:)` to capture from a specific device
- Added "Record from Device" submenu in AppDelegate with all input devices listed
- BlackHole devices are highlighted with ⭐
- Aggregate devices appear in the list

### Files Modified
- `Sources/Shared/MicrophoneCaptureManager.swift` - Device enumeration and selection
- `Sources/CaptureController.swift` - `startRecording(fromDevice:)` method
- `Sources/AppDelegate.swift` - "Record from Device" submenu

## Current Issues

### 1. App Crashes on Launch
- Crash reports in `~/Library/Logs/DiagnosticReports/Audio Summary-2025-11-18-*.ips`
- App shows `applicationDidFinishLaunching` is called but then crashes
- Need to investigate crash logs for root cause

### 2. No Audio Being Captured
- Previous recordings show "있 있 있" (Korean hallucinations from silence)
- Indicates Parakeet model receiving zero/near-zero amplitude audio
- BlackHole is not receiving audio from Multi-Output Device

### 3. Audio Routing Configuration Confusion
The user has set up:
- **Multi-Output Device**: MacBook Air Speakers + BlackHole 2ch
- **Aggregate Device "Audio Summary"**: BlackHole 2ch + MacBook Air Microphone

**Problem**: Teams was set to use "Audio Summary (Aggregate)" as Speaker, but Aggregate Devices are for INPUT aggregation, not output. Audio was not being routed through BlackHole.

**Correct Setup**:
1. Teams Speaker → **Multi-Output Device** (sends audio to speakers + BlackHole)
2. Teams Microphone → MacBook Air Microphone (or Audio Summary Aggregate)
3. Audio Summary recording → **Audio Summary (Aggregate Device)** (captures BlackHole + Mic)

## Known Compiler Warnings

```
MicrophoneCaptureManager.swift:146:29: warning: forming 'UnsafeMutableRawPointer' to a variable of type 'CFString'; this is likely incorrect
MicrophoneCaptureManager.swift:167:29: warning: forming 'UnsafeMutableRawPointer' to a variable of type 'CFString'; this is likely incorrect
```

These warnings are in the CoreAudio device enumeration code for getting device names/UIDs. May be causing crashes.

## What Was Tried

### Attempt 1: ScreenCaptureKit Audio Capture
- `didOutputSampleBuffer` delegate method NEVER called on macOS 15 Sequoia
- Video frames received but zero audio samples
- Tried multiple SCStreamConfiguration settings
- Known Apple bug on Sequoia

### Attempt 2: Microphone Fallback
- Implemented `MicrophoneCaptureManager` using AVAudioEngine
- Works for direct microphone capture
- Added device selection to capture from BlackHole/Aggregate devices

### Attempt 3: Device Selection via System Default
- `AVAudioEngine` only reads from system default input device
- Implemented `setDefaultInputDevice()` to temporarily change system default
- This may be causing issues or conflicts

## Next Steps to Try

1. **Fix Crash**:
   - Examine crash logs in detail
   - Fix CFString pointer warnings (use proper CoreAudio patterns)
   - Add more defensive nil checks

2. **Verify Audio Routing**:
   - Test with a simple audio file playing through Multi-Output Device
   - Verify BlackHole shows audio input in Audio MIDI Setup
   - Record from just BlackHole 2ch (not Aggregate) to isolate issue

3. **Alternative Approach - Direct Device Selection**:
   - Instead of changing system default, use `AudioUnit` directly with specific device
   - More reliable than AVAudioEngine for non-default devices

4. **Consider Simpler Architecture**:
   - Just capture from built-in microphone (works reliably)
   - User places laptop near speaker to capture call audio
   - Less ideal but more reliable

## Environment
- macOS 15 Sequoia
- Apple Silicon (M-series)
- Audio Summary v0.2.0 (dev build)
- BlackHole 2ch installed

## Build Command
```bash
cd /Users/adambutler/Projects/private_notes/audio_summary_app/macos_gui
./build_app.sh
```

## Test Command
```bash
# Start engine
cd /Users/adambutler/Projects/private_notes/audio_summary_app
uv run python -m audio_summary_app.engine.server &

# Launch app
open "/Applications/Audio Summary.app"
```
