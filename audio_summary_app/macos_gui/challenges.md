# ScreenCaptureKit Audio Capture Challenges

## Overview

This document details the challenges encountered while implementing Phase 4 of the Audio Summary application - specifically the issue of ScreenCaptureKit not delivering audio samples from Teams/Zoom calls.

## Core Problem

**ScreenCaptureKit's `didOutputSampleBuffer` delegate method is never called**, even though:
- The stream starts successfully without errors
- Screen Recording permission is granted
- The purple recording indicator appears on the target window
- The app is properly code-signed with a Developer ID certificate

## Symptoms

1. Session is created successfully on the engine server
2. No `/audio_chunk` HTTP requests are received by the engine
3. Summary file contains: "No usable call audio was captured from the target app"
4. No errors are logged during capture

## Investigation Timeline

### Attempt 1: Window-based Filter
**Configuration:**
```swift
let filter = SCContentFilter(desktopIndependentWindow: appWindows[0])
```

**Result:** No audio samples delivered. Purple indicator appeared on Teams window.

### Attempt 2: Display-based Filter with App Exclusion
**Configuration:**
```swift
let excludedApps = content.applications.filter { $0.processID != app.processID }
let filter = SCContentFilter(
    display: display,
    excludingApplications: excludedApps,
    exceptingWindows: []
)
```

**Result:** No audio samples delivered. Purple indicator did NOT appear.

### Attempt 3: Enable Proper Video Capture
**Hypothesis:** ScreenCaptureKit may require video to be properly configured for audio to flow.

**Configuration:**
```swift
config.width = 1920
config.height = 1080
config.minimumFrameInterval = CMTime(value: 1, timescale: 30)  // 30 FPS
```

Also registered both audio and video stream outputs:
```swift
try stream.addStreamOutput(self, type: .audio, sampleHandlerQueue: sampleQueue)
try stream.addStreamOutput(self, type: .screen, sampleHandlerQueue: sampleQueue)
```

**Result:** No audio samples delivered.

### Attempt 4: Add Audio Input Entitlement
**Discovery:** Research revealed that hardened runtime apps require the `com.apple.security.device.audio-input` entitlement for ScreenCaptureKit audio capture.

**Fix:** Created `entitlements.plist`:
```xml
<key>com.apple.security.device.audio-input</key>
<true/>
<key>com.apple.security.device.camera</key>
<true/>
<key>com.apple.security.cs.disable-library-validation</key>
<true/>
```

Signed with: `codesign --entitlements entitlements.plist --options runtime`

**Result:** No audio samples delivered.

### Attempt 5: Add Microphone Permission Request
**Discovery:** Further research revealed that NSMicrophoneUsageDescription must be in Info.plist AND the user must grant Microphone permission for ScreenCaptureKit audio to work.

**Fix:**
1. Added `NSMicrophoneUsageDescription` to Info.plist (already present)
2. Added code to request microphone permission in the wizard:
```swift
let micStatus = AVCaptureDevice.authorizationStatus(for: .audio)
if micStatus == .notDetermined {
    _ = await AVCaptureDevice.requestAccess(for: .audio)
}
```

**Result:** Testing in progress.

## Key Findings from Research

### Stack Overflow / Apple Forums Insights

1. **Memory Management Issue**: "stream output NOT found. Dropping frame" - the stream output delegate may be getting deallocated. Ensure strong reference.

2. **Privacy Requirements**: "Make sure you have Audio Input enabled in App Sandbox or Hardened Runtime... Also make sure you have the microphone privacy description in your Info.plist, or you'll capture no buffers."

3. **Audio Capture Behavior**: "ScreenCaptureKit's audio capture policy always works at the app level. When a single window filter is used, all the audio content from the application that contains the window will be captured."

4. **macOS 15 Issues**: Some developers report ScreenCaptureKit audio capture stopped working on macOS 15 (Sequoia).

## Required Permissions & Entitlements

### Info.plist Keys
- `NSScreenCaptureDescription` - For screen recording permission prompt
- `NSMicrophoneUsageDescription` - Required for audio capture to work

### Hardened Runtime Entitlements
- `com.apple.security.device.audio-input` - Critical for audio capture
- `com.apple.security.device.camera` - For screen capture
- `com.apple.security.cs.disable-library-validation` - For loading frameworks

### System Permissions (Privacy & Security)
- **Screen Recording** - Must be enabled for app
- **Microphone** - Must be enabled for app (critical discovery!)

## Code Signing Requirements

Ad-hoc signed apps do not work reliably with ScreenCaptureKit. Must use:
```bash
codesign --force --deep \
  --sign "Developer ID Application: <Name> (<Team ID>)" \
  --entitlements entitlements.plist \
  --options runtime \
  "App.app"
```

## Current Status

**As of 2024-11-18:**
- All entitlements in place
- Both Screen Recording and Microphone permissions granted
- App properly signed with Developer ID
- Still testing if audio samples are being delivered

## Alternative Approaches to Consider

If ScreenCaptureKit continues to fail:

1. **AudioHardwareCreateProcessTap** - Alternative API for capturing system audio
2. **CATap API (macOS 13+)** - Can capture both mic and system audio with synchronization
3. **Virtual Audio Device** - Route app audio through a virtual device (e.g., BlackHole)
4. **Microphone Fallback** - Use AVAudioEngine to capture microphone input (captures user speech only, not remote participants)

## Lessons Learned

1. **Permissions are non-obvious**: Microphone permission is required even though we're not using the microphone API directly.

2. **Entitlements matter for hardened runtime**: The audio-input entitlement is essential and not well-documented.

3. **Code signing affects API behavior**: ScreenCaptureKit behaves differently for ad-hoc vs Developer ID signed apps.

4. **The purple indicator is misleading**: Seeing the recording indicator doesn't mean audio samples are being delivered.

5. **Debug logging is essential**: Always add print statements in `didOutputSampleBuffer` to verify samples are actually being received.

## Debugging Checklist

When ScreenCaptureKit audio isn't working:

- [ ] Is the app signed with Developer ID (not ad-hoc)?
- [ ] Does entitlements.plist include `com.apple.security.device.audio-input`?
- [ ] Is `NSMicrophoneUsageDescription` in Info.plist?
- [ ] Is Screen Recording permission granted in System Settings?
- [ ] Is Microphone permission granted in System Settings?
- [ ] Is `config.capturesAudio = true` set?
- [ ] Is the stream output delegate being retained (not deallocated)?
- [ ] Are you checking for errors from `stream.startCapture()`?
- [ ] Did you add debug logging in `didOutputSampleBuffer`?
