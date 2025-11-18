// FirstRunWizard.swift
// First-run wizard with 4 steps
// Per spec §4.1 FR2 - First-Run Wizard

import SwiftUI
import ScreenCaptureKit
import CoreMedia
import AVFoundation

struct FirstRunWizard: View {
    @EnvironmentObject var preferences: PreferencesManager

    @State private var currentStep = 0
    @State private var selectedApp: SCRunningApplication?
    @State private var availableApps: [SCRunningApplication] = []
    @State private var permissionsGranted = false
    @State private var audioTestPassed = false

    var body: some View {
        VStack(spacing: 0) {
            // Progress indicator
            HStack(spacing: 4) {
                ForEach(0..<4) { step in
                    Circle()
                        .fill(step <= currentStep ? Color.accentColor : Color.gray.opacity(0.3))
                        .frame(width: 12, height: 12)
                }
            }
            .padding(.top, 20)

            Divider()
                .padding(.top, 16)

            // Step content
            TabView(selection: $currentStep) {
                WelcomeStep()
                    .tag(0)

                SelectAppStep(selectedApp: $selectedApp, availableApps: $availableApps)
                    .tag(1)

                PermissionsStep(permissionsGranted: $permissionsGranted)
                    .tag(2)

                AudioTestStep(
                    selectedApp: selectedApp,
                    audioTestPassed: $audioTestPassed
                )
                .tag(3)
            }
            .tabViewStyle(.automatic)

            Divider()

            // Navigation buttons
            HStack {
                if currentStep > 0 {
                    Button("Back") {
                        currentStep -= 1
                    }
                }

                Spacer()

                if currentStep < 3 {
                    Button("Next") {
                        currentStep += 1
                    }
                    .disabled(!canProceed())
                } else {
                    Button("Finish") {
                        completeWizard()
                    }
                    .disabled(!audioTestPassed)
                }
            }
            .padding()
        }
    }

    private func canProceed() -> Bool {
        switch currentStep {
        case 0: return true
        case 1: return selectedApp != nil
        case 2: return permissionsGranted
        case 3: return true  // Audio test is optional - can skip
        default: return false
        }
    }

    private func completeWizard() {
        preferences.firstRunCompleted = true
        NSApp.keyWindow?.close()
    }
}

// MARK: - Step 1: Welcome

struct WelcomeStep: View {
    var body: some View {
        VStack(spacing: 24) {
            Image(systemName: "mic.fill")
                .font(.system(size: 64))
                .foregroundColor(.accentColor)

            Text("Welcome to Audio Summary")
                .font(.largeTitle)
                .fontWeight(.bold)

            VStack(spacing: 12) {
                Text("Audio Summary captures and transcribes your Zoom and Teams calls, then generates concise summaries using local AI models.")
                    .multilineTextAlignment(.center)

                Text("All processing happens on your device. No data leaves your Mac.")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
            }
            .padding(.horizontal, 32)

            VStack(alignment: .leading, spacing: 8) {
                FeatureRow(icon: "lock.fill", text: "100% local processing")
                FeatureRow(icon: "waveform", text: "Real-time transcription")
                FeatureRow(icon: "doc.text.fill", text: "AI-powered summaries")
                FeatureRow(icon: "table", text: "Export to CSV")
            }
            .padding(.horizontal, 48)
        }
        .padding()
    }
}

struct FeatureRow: View {
    let icon: String
    let text: String

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .foregroundColor(.accentColor)
                .frame(width: 24)

            Text(text)
                .font(.body)
        }
    }
}

// MARK: - Step 2: Select App

struct SelectAppStep: View {
    @Binding var selectedApp: SCRunningApplication?
    @Binding var availableApps: [SCRunningApplication]

    @State private var isLoading = true
    @State private var errorMessage: String?

    var body: some View {
        VStack(spacing: 24) {
            Image(systemName: "video.fill")
                .font(.system(size: 48))
                .foregroundColor(.accentColor)

            Text("Select Capture Source")
                .font(.title)
                .fontWeight(.bold)

            Text("Audio Summary will capture audio from Zoom or Microsoft Teams. Please select which app to monitor:")
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)

            if isLoading {
                ProgressView("Scanning for Zoom and Teams...")
                    .padding()
            } else if let error = errorMessage {
                VStack(spacing: 12) {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .font(.system(size: 32))
                        .foregroundColor(.orange)

                    Text(error)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)

                    Button("Retry") {
                        Task { await scanForApps() }
                    }
                }
            } else if availableApps.isEmpty {
                VStack(spacing: 12) {
                    Image(systemName: "app.dashed")
                        .font(.system(size: 32))
                        .foregroundColor(.secondary)

                    Text("No Zoom or Teams apps are currently running.")
                        .foregroundColor(.secondary)

                    Text("Please start Zoom or Teams and click Retry.")
                        .font(.subheadline)
                        .foregroundColor(.secondary)

                    Button("Retry") {
                        Task { await scanForApps() }
                    }
                }
            } else {
                VStack(spacing: 12) {
                    ForEach(availableApps, id: \.processID) { app in
                        AppSelectionRow(
                            app: app,
                            isSelected: selectedApp?.processID == app.processID
                        ) {
                            selectedApp = app
                        }
                    }
                }
                .padding(.horizontal, 32)
            }
        }
        .padding()
        .task {
            await scanForApps()
        }
    }

    private func scanForApps() async {
        isLoading = true
        errorMessage = nil

        do {
            let captureManager = ScreenCaptureManager()
            let content = try await captureManager.getShareableContent()
            let apps = captureManager.findTargetApps(in: content)

            await MainActor.run {
                availableApps = apps
                if apps.count == 1 {
                    selectedApp = apps[0]
                }
                isLoading = false
            }
        } catch {
            await MainActor.run {
                errorMessage = "Failed to scan for apps: \(error.localizedDescription)"
                isLoading = false
            }
        }
    }
}

struct AppSelectionRow: View {
    let app: SCRunningApplication
    let isSelected: Bool
    let onSelect: () -> Void

    var body: some View {
        Button(action: onSelect) {
            HStack {
                Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                    .foregroundColor(isSelected ? .accentColor : .gray)
                    .font(.title3)

                VStack(alignment: .leading) {
                    Text(app.applicationName)
                        .font(.headline)
                        .foregroundColor(.primary)

                    Text(app.bundleIdentifier)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }

                Spacer()
            }
            .padding()
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(isSelected ? Color.accentColor.opacity(0.1) : Color.gray.opacity(0.05))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(isSelected ? Color.accentColor : Color.clear, lineWidth: 2)
            )
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Step 3: Permissions

struct PermissionsStep: View {
    @Binding var permissionsGranted: Bool

    var body: some View {
        VStack(spacing: 24) {
            Image(systemName: "lock.shield.fill")
                .font(.system(size: 48))
                .foregroundColor(.accentColor)

            Text("Grant Permissions")
                .font(.title)
                .fontWeight(.bold)

            Text("Audio Summary needs Screen Recording and Microphone permissions to capture audio from Zoom and Teams.")
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)

            VStack(alignment: .leading, spacing: 16) {
                PermissionRow(
                    number: 1,
                    text: "Click 'Request Permission' below"
                )

                PermissionRow(
                    number: 2,
                    text: "macOS will show a permission dialog"
                )

                PermissionRow(
                    number: 3,
                    text: "Click 'Open System Settings'"
                )

                PermissionRow(
                    number: 4,
                    text: "Enable Screen Recording for Audio Summary"
                )

                PermissionRow(
                    number: 5,
                    text: "Return here and click 'Verify Permission'"
                )
            }
            .padding(.horizontal, 48)

            HStack(spacing: 16) {
                Button("Request Permission") {
                    Task {
                        await requestScreenCapturePermission()
                    }
                }

                Button("Verify Permission") {
                    Task {
                        await verifyPermission()
                    }
                }
            }

            if permissionsGranted {
                HStack(spacing: 8) {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.green)

                    Text("Permission granted!")
                        .foregroundColor(.green)
                        .fontWeight(.medium)
                }
            }
        }
        .padding()
        .task {
            // Auto-verify on appear
            await verifyPermission()
        }
    }

    private func requestScreenCapturePermission() async {
        do {
            // Request microphone permission first (required for ScreenCaptureKit audio)
            let micStatus = AVCaptureDevice.authorizationStatus(for: .audio)
            if micStatus == .notDetermined {
                _ = await AVCaptureDevice.requestAccess(for: .audio)
            }

            // Trigger screen recording permission prompt by attempting to get shareable content
            let captureManager = ScreenCaptureManager()
            _ = try await captureManager.getShareableContent()
            await verifyPermission()
        } catch {
            print("Permission request error: \(error)")
        }
    }

    private func verifyPermission() async {
        // Try to get shareable content - if successful, permission is granted
        do {
            let captureManager = ScreenCaptureManager()
            _ = try await captureManager.getShareableContent()
            await MainActor.run {
                permissionsGranted = true
            }
        } catch {
            await MainActor.run {
                permissionsGranted = false
            }
        }
    }
}

struct PermissionRow: View {
    let number: Int
    let text: String

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Text("\(number).")
                .fontWeight(.bold)
                .foregroundColor(.accentColor)
                .frame(width: 24, alignment: .trailing)

            Text(text)
                .font(.body)
        }
    }
}

// MARK: - Step 4: Audio Test

struct AudioTestStep: View {
    let selectedApp: SCRunningApplication?
    @Binding var audioTestPassed: Bool

    @State private var isTesting = false
    @State private var audioLevel: Float = 0.0
    @State private var captureManager: ScreenCaptureManager?
    @State private var testError: String?

    var body: some View {
        VStack(spacing: 24) {
            Image(systemName: "waveform")
                .font(.system(size: 48))
                .foregroundColor(.accentColor)

            Text("Audio Test")
                .font(.title)
                .fontWeight(.bold)

            Text("Let's verify that Audio Summary can capture audio from your selected app.")
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)

            if let app = selectedApp {
                Text("Testing: \(app.applicationName)")
                    .font(.headline)
                    .foregroundColor(.secondary)
            }

            // Audio level meter
            VStack(spacing: 12) {
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 8)
                        .fill(Color.gray.opacity(0.2))
                        .frame(height: 40)

                    RoundedRectangle(cornerRadius: 8)
                        .fill(
                            LinearGradient(
                                colors: [.green, .yellow, .orange, .red],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .frame(width: CGFloat(audioLevel) * 400, height: 40)
                }
                .frame(width: 400)

                Text(String(format: "Level: %.1f%%", audioLevel * 100))
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            if isTesting {
                VStack(spacing: 8) {
                    ProgressView()
                        .scaleEffect(0.8)

                    Text("Listening for audio...")
                        .font(.subheadline)
                        .foregroundColor(.secondary)

                    Text("Play audio in \(selectedApp?.applicationName ?? "the app") to test")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }

            if let error = testError {
                Text(error)
                    .foregroundColor(.red)
                    .font(.subheadline)
            }

            HStack(spacing: 16) {
                Button(isTesting ? "Stop Test" : "Start Audio Test") {
                    if isTesting {
                        stopAudioTest()
                    } else {
                        Task {
                            await startAudioTest()
                        }
                    }
                }
                .disabled(selectedApp == nil)

                Button("Skip Test") {
                    // Allow user to skip the audio test
                    audioTestPassed = true
                }
                .disabled(isTesting)

                if audioTestPassed {
                    HStack(spacing: 8) {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundColor(.green)

                        Text("Audio detected!")
                            .foregroundColor(.green)
                            .fontWeight(.medium)
                    }
                }
            }

            VStack(spacing: 8) {
                Text("You should see the level meter move when audio is playing in the app.")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)

                Text("If the test fails, you can skip it and try recording a real call.")
                    .font(.caption)
                    .foregroundColor(.orange)
                    .multilineTextAlignment(.center)
            }
            .padding(.horizontal, 48)
        }
        .padding()
        .onDisappear {
            stopAudioTest()
        }
    }

    private func startAudioTest() async {
        guard let app = selectedApp else { return }

        await MainActor.run {
            isTesting = true
            testError = nil
            audioTestPassed = false
            audioLevel = 0.0
        }

        do {
            let manager = ScreenCaptureManager()
            captureManager = manager

            // Set up audio callback to monitor levels
            manager.onAudioCaptured = { sampleBuffer, _ in
                let level = calculateAudioLevel(sampleBuffer)

                Task { @MainActor in
                    audioLevel = level

                    // If we detect significant audio, mark test as passed
                    if level > 0.1 {
                        audioTestPassed = true
                    }
                }
            }

            try await manager.startCapture(for: app)

        } catch {
            await MainActor.run {
                testError = "Failed to start audio test: \(error.localizedDescription)"
                isTesting = false
            }
        }
    }

    private func stopAudioTest() {
        guard let manager = captureManager else { return }

        Task {
            await manager.stopCapture()
            await MainActor.run {
                isTesting = false
                captureManager = nil
            }
        }
    }

    private func calculateAudioLevel(_ sampleBuffer: CMSampleBuffer) -> Float {
        do {
            let (samples, _, _) = try AudioProcessor.extractFloat32Samples(sampleBuffer)

            // Calculate RMS level
            var sumSquares: Float = 0.0
            for sample in samples {
                sumSquares += sample * sample
            }
            let rms = sqrt(sumSquares / Float(samples.count))

            // Normalize to 0-1 range (assuming typical speech is around -20dB to 0dB)
            let normalizedLevel = min(rms * 3.0, 1.0)

            return normalizedLevel

        } catch {
            return 0.0
        }
    }
}
