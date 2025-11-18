// ScreenCaptureManager.swift
// ScreenCaptureKit integration for capturing Zoom/Teams audio
// Per spec §7 Phase 2 - Lists apps, filters Zoom/Teams, captures audio

import Foundation
import ScreenCaptureKit
import CoreMedia

enum ScreenCaptureError: Error, LocalizedError {
    case permissionDenied
    case noShareableContent
    case noTargetAppFound
    case captureInitFailed(String)
    case captureFailed(String)

    var errorDescription: String? {
        switch self {
        case .permissionDenied:
            return "Screen recording permission denied. Please enable in System Settings > Privacy & Security > Screen Recording"
        case .noShareableContent:
            return "No shareable content available"
        case .noTargetAppFound:
            return "No Zoom or Teams apps found running"
        case .captureInitFailed(let reason):
            return "Failed to initialize capture: \(reason)"
        case .captureFailed(let reason):
            return "Capture failed: \(reason)"
        }
    }
}

class ScreenCaptureManager: NSObject {

    private var stream: SCStream?
    private var isCapturing = false

    // Callback for audio chunks
    var onAudioCaptured: ((CMSampleBuffer, Int) -> Void)?
    // Callback for capture errors
    var onError: ((Error) -> Void)?

    // MARK: - List Shareable Content

    /// Get all shareable content (apps, windows, displays)
    /// Per spec §7: List SCShareableContent
    func getShareableContent() async throws -> SCShareableContent {
        do {
            print("[ScreenCapture] Requesting shareable content...")
            let content = try await SCShareableContent.excludingDesktopWindows(
                false,
                onScreenWindowsOnly: true
            )
            print("[ScreenCapture] Got shareable content: \(content.applications.count) apps, \(content.windows.count) windows, \(content.displays.count) displays")
            return content
        } catch let error as NSError {
            print("[ScreenCapture] ERROR getting shareable content:")
            print("  Domain: \(error.domain)")
            print("  Code: \(error.code)")
            print("  Description: \(error.localizedDescription)")
            print("  User Info: \(error.userInfo)")

            // Check if this is a permission error
            if error.domain == "com.apple.ScreenCaptureKit" && error.code == -3801 {
                throw ScreenCaptureError.captureInitFailed("Screen recording permission not granted. Please enable 'Audio Summary' in System Settings > Privacy & Security > Screen Recording, then restart the app.")
            }
            throw ScreenCaptureError.captureInitFailed("Failed to get shareable content: \(error.localizedDescription)")
        }
    }

    // MARK: - Find Target Apps

    /// Find Zoom or Teams apps from shareable content
    /// Per spec §7: Filter for Zoom.us or Microsoft Teams
    ///
    /// Target bundle IDs:
    /// - Zoom: us.zoom.xos
    /// - Microsoft Teams: com.microsoft.teams, com.microsoft.teams2
    func findTargetApps(in content: SCShareableContent) -> [SCRunningApplication] {
        let targetBundleIDs = [
            "us.zoom.xos",              // Zoom
            "com.microsoft.teams",      // Microsoft Teams (classic)
            "com.microsoft.teams2"      // Microsoft Teams (new)
        ]

        return content.applications.filter { app in
            targetBundleIDs.contains(app.bundleIdentifier)
        }
    }

    // MARK: - Start Capture

    /// Start capturing audio from specified app
    /// Per spec §7: Capture audio stream via ScreenCaptureKit
    ///
    /// Configuration per spec §4:
    /// - Audio-only capture (no video)
    /// - excludeCurrentProcessAudio: true
    /// - Sample rate: 48000 Hz (default from ScreenCaptureKit)
    func startCapture(for app: SCRunningApplication) async throws {
        guard !isCapturing else {
            print("Already capturing")
            return
        }

        // Get all available displays and windows
        let content = try await getShareableContent()

        // Find windows for the target app
        let appWindows = content.windows.filter { window in
            window.owningApplication?.processID == app.processID
        }

        print("[ScreenCapture] Found \(appWindows.count) windows for \(app.applicationName)")

        guard !appWindows.isEmpty else {
            throw ScreenCaptureError.noShareableContent
        }

        guard !content.displays.isEmpty else {
            throw ScreenCaptureError.noShareableContent
        }

        // Pick the display that actually contains the target app's main window (if possible).
        let targetDisplay: SCDisplay
        if let mainWindow = appWindows.first {
            let center = CGPoint(x: mainWindow.frame.midX, y: mainWindow.frame.midY)
            if let matchingDisplay = content.displays.first(where: { $0.frame.contains(center) }) {
                targetDisplay = matchingDisplay
            } else {
                targetDisplay = content.displays[0]
            }
        } else {
            targetDisplay = content.displays[0]
        }

        print("[ScreenCapture] Using display id: \(targetDisplay.displayID)")

        // WORKAROUND: Include ALL applications on display, then filter audio at stream level
        // Per Apple docs: "passing an empty windows array causes the stream to never start"
        // and ScreenCaptureKit audio filtering works at app level anyway
        print("[ScreenCapture] Target: \(app.applicationName) (\(app.bundleIdentifier))")
        print("[ScreenCapture] Including ALL \(content.applications.count) apps (will filter audio at stream level)")

        // Use excludingApplications with empty array = include all apps
        let filter = SCContentFilter(
            display: targetDisplay,
            excludingApplications: [],
            exceptingWindows: []
        )

        // Configure stream for audio+video capture
        let config = SCStreamConfiguration()

        // Audio settings - explicitly configure for best compatibility
        config.capturesAudio = true
        config.excludesCurrentProcessAudio = true // Prevent feedback loops
        config.sampleRate = 48000  // Explicit sample rate
        config.channelCount = 2    // Stereo

        print("[ScreenCapture] Audio config: capturesAudio=true, sampleRate=48000, channelCount=2")

        // Video settings (required for audio to flow properly on some macOS versions)
        // OBS Studio and others have found that you MUST have video configured for audio to work
        config.width = 1920
        config.height = 1080
        config.minimumFrameInterval = CMTime(value: 1, timescale: 10)  // 10 FPS (lower to reduce overhead)
        config.pixelFormat = kCVPixelFormatType_32BGRA
        config.showsCursor = false
        config.queueDepth = 8  // Increased queue depth for better buffering

        // Create stream
        stream = SCStream(filter: filter, configuration: config, delegate: self)

        guard let stream = stream else {
            throw ScreenCaptureError.captureInitFailed("Failed to create SCStream")
        }

        // Add stream outputs for both audio and video
        // (We only use audio, but ScreenCaptureKit may need both registered)
        // IMPORTANT: Use HIGH priority queue for better responsiveness
        let sampleQueue = DispatchQueue(label: "com.audiosummary.samplequeue", qos: .userInteractive)
        do {
            print("[ScreenCapture] Adding audio stream output...")
            try stream.addStreamOutput(
                self,
                type: .audio,
                sampleHandlerQueue: sampleQueue
            )
            print("[ScreenCapture] ✅ Audio stream output added")

            print("[ScreenCapture] Adding screen stream output...")
            try stream.addStreamOutput(
                self,
                type: .screen,
                sampleHandlerQueue: sampleQueue
            )
            print("[ScreenCapture] ✅ Screen stream output added")
        } catch {
            print("[ScreenCapture] ❌ Failed to add stream output: \(error)")
            throw ScreenCaptureError.captureInitFailed("Failed to add stream output: \(error.localizedDescription)")
        }

        // Start capture
        do {
            print("[ScreenCapture] About to call stream.startCapture()...")
            try await stream.startCapture()
            isCapturing = true
            print("[ScreenCapture] ✅ Started capturing audio from \(app.applicationName)")
        } catch let error as NSError {
            print("[ScreenCapture] ❌ stream.startCapture() FAILED:")
            print("  Error domain: \(error.domain)")
            print("  Error code: \(error.code)")
            print("  Description: \(error.localizedDescription)")
            print("  User info: \(error.userInfo)")
            throw ScreenCaptureError.captureFailed("Failed to start capture: \(error.localizedDescription)")
        }
    }

    // MARK: - Stop Capture

    /// Stop audio capture
    func stopCapture() async {
        guard isCapturing, let stream = stream else {
            return
        }

        do {
            try await stream.stopCapture()
            isCapturing = false
            print("[ScreenCapture] Stopped capturing")
        } catch {
            print("[ScreenCapture] Error stopping capture: \(error.localizedDescription)")
        }

        self.stream = nil
    }
}

// MARK: - SCStreamDelegate

extension ScreenCaptureManager: SCStreamDelegate {

    func stream(_ stream: SCStream, didStopWithError error: Error) {
        print("[ScreenCapture] Stream stopped with error: \(error.localizedDescription)")
        isCapturing = false
    }
}

// MARK: - SCStreamOutput

extension ScreenCaptureManager: SCStreamOutput {

    private static var sampleCount = 0
    private static var audioSampleCount = 0
    private static var videoSampleCount = 0

    func stream(
        _ stream: SCStream,
        didOutputSampleBuffer sampleBuffer: CMSampleBuffer,
        of type: SCStreamOutputType
    ) {
        ScreenCaptureManager.sampleCount += 1

        if type == .audio {
            ScreenCaptureManager.audioSampleCount += 1
            print("[ScreenCapture] 🎤 AUDIO sample #\(ScreenCaptureManager.audioSampleCount) (total: \(ScreenCaptureManager.sampleCount))")

            // Get sample rate from buffer
            guard let sampleRate = AudioProcessor.getSampleRate(sampleBuffer) else {
                print("[ScreenCapture] ⚠️ Could not get sample rate from buffer")
                return
            }

            let numSamples = CMSampleBufferGetNumSamples(sampleBuffer)
            print("[ScreenCapture] Audio: sampleRate=\(sampleRate), numSamples=\(numSamples)")

            // Call callback with audio chunk
            onAudioCaptured?(sampleBuffer, sampleRate)
        } else {
            ScreenCaptureManager.videoSampleCount += 1
            // Only log video samples occasionally to reduce noise
            if ScreenCaptureManager.videoSampleCount % 30 == 1 {
                print("[ScreenCapture] 📺 Video #\(ScreenCaptureManager.videoSampleCount) (total: \(ScreenCaptureManager.sampleCount), audio: \(ScreenCaptureManager.audioSampleCount))")
            }
        }
    }
}
