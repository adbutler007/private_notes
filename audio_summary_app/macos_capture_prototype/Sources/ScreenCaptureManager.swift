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

    // MARK: - List Shareable Content

    /// Get all shareable content (apps, windows, displays)
    /// Per spec §7: List SCShareableContent
    func getShareableContent() async throws -> SCShareableContent {
        do {
            let content = try await SCShareableContent.excludingDesktopWindows(
                false,
                onScreenWindowsOnly: true
            )
            return content
        } catch {
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

        // Get all available displays
        let content = try await getShareableContent()
        guard let display = content.displays.first else {
            throw ScreenCaptureError.noShareableContent
        }

        // Create content filter
        // We want to capture audio from the target app, excluding all others
        let excludedApps = content.applications.filter { $0.processID != app.processID }

        let filter = SCContentFilter(
            display: display,
            excludingApplications: excludedApps,
            exceptingWindows: []
        )

        // Configure stream for audio-only capture
        let config = SCStreamConfiguration()

        // Audio settings
        config.capturesAudio = true
        config.sampleRate = 48000  // 48kHz default from ScreenCaptureKit
        config.channelCount = 2    // Stereo (will be converted to mono)

        // Disable video
        config.width = 1
        config.height = 1
        config.minimumFrameInterval = CMTime(value: 1, timescale: 1)
        config.queueDepth = 5

        // Create stream
        stream = SCStream(filter: filter, configuration: config, delegate: self)

        guard let stream = stream else {
            throw ScreenCaptureError.captureInitFailed("Failed to create SCStream")
        }

        // Add stream output
        do {
            try stream.addStreamOutput(
                self,
                type: .audio,
                sampleHandlerQueue: DispatchQueue(label: "com.audiosummary.audioqueue")
            )
        } catch {
            throw ScreenCaptureError.captureInitFailed("Failed to add stream output: \(error.localizedDescription)")
        }

        // Start capture
        do {
            try await stream.startCapture()
            isCapturing = true
            print("[ScreenCapture] Started capturing audio from \(app.applicationName)")
        } catch {
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

    func stream(
        _ stream: SCStream,
        didOutputSampleBuffer sampleBuffer: CMSampleBuffer,
        of type: SCStreamOutputType
    ) {
        // Only process audio samples
        guard type == .audio else { return }

        // Get sample rate from buffer
        guard let sampleRate = AudioProcessor.getSampleRate(sampleBuffer) else {
            print("[ScreenCapture] Warning: Could not get sample rate from buffer")
            return
        }

        // Call callback with audio chunk
        onAudioCaptured?(sampleBuffer, sampleRate)
    }
}
