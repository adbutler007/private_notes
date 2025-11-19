// CaptureController.swift
// Orchestrates capture sessions: engine communication + audio capture
// Per spec §4.1 FR3 - Start/Stop Recording

import Foundation
import ScreenCaptureKit
import CoreMedia
import UserNotifications

enum CaptureState {
    case idle
    case starting
    case recording(sessionId: String)
    case stopping
    case error(String)
}

class CaptureController: ObservableObject {
    @Published var state: CaptureState = .idle
    @Published var bufferStatus: String = ""

    private let engine: EngineClient
    private let captureManager = ScreenCaptureManager()
    private let micCaptureManager = MicrophoneCaptureManager()  // Mic fallback
    private let preferences = PreferencesManager.shared
    private let sessionManager = SessionManager.shared
    private let logger = AppLogger.shared

    private var currentSessionId: String?
    private var sessionStartTime: Date?
    private var chunkBuffer: [CMSampleBuffer] = []
    private var chunkBufferSampleCount = 0
    private let chunkBufferSize = 96000  // ~2 seconds at 48kHz

    private var audioChunkCount = 0
    private var usingMicFallback = false  // Track if using mic instead of screen capture
    private var lastAudioTimestamp: Date?
    private var audioWatchdogTask: Task<Void, Never>?

    init(engineURL: URL = URL(string: "http://127.0.0.1:8756")!) {
        self.engine = EngineClient(baseURL: engineURL)
    }

    // MARK: - Start Recording

    /// Start recording from an audio input device (e.g., BlackHole)
    func startRecording(fromDevice device: AudioInputDevice) async {
        guard case .idle = state else {
            logger.warning("Cannot start: not in idle state")
            return
        }

        logger.info("Starting capture from audio device: \(device.name)")
        state = .starting

        do {
            // 1. Check engine health
            _ = try await engine.health()
            logger.logEngineStatus("connected")

            // 2. Start session
            let sessionId = UUID().uuidString
            currentSessionId = sessionId
            sessionStartTime = Date()

            let startRequest = StartSessionRequest(
                sessionId: sessionId,
                model: preferences.sttBackend,
                sampleRate: 48000,
                userSettings: UserSettings(
                    chunkSummaryPrompt: preferences.chunkSummaryPrompt,
                    finalSummaryPrompt: preferences.finalSummaryPrompt,
                    dataExtractionPrompt: preferences.dataExtractionPrompt,
                    llmModelName: preferences.llmModel,
                    outputDir: preferences.outputDir,
                    csvExportPath: preferences.csvExportPath,
                    appendCsv: preferences.appendCSV
                )
            )

            _ = try await engine.startSession(request: startRequest)

            // 3. Set up audio callback
            micCaptureManager.onAudioCaptured = { [weak self] sampleBuffer, sampleRate in
                self?.handleAudioChunk(sampleBuffer: sampleBuffer, sampleRate: sampleRate)
            }

            // 4. Start capture from device
            try await micCaptureManager.startCapture(fromDevice: device)
            usingMicFallback = true
            logger.logCaptureEvent("started", sessionId: sessionId, usingMicFallback: true)

            // 5. Update state
            await MainActor.run {
                state = .recording(sessionId: sessionId)
            }

            // 6. Send notification
            sendNotification(title: "Recording Started", body: "Capturing audio from \(device.name)")

        } catch {
            logger.logError(error, context: "Failed to start device recording")
            await MainActor.run {
                state = .error("Failed to start: \(error.localizedDescription)")
            }
        }
    }

    func startRecording(app: SCRunningApplication) async {
        guard case .idle = state else {
            logger.warning("Cannot start: not in idle state")
            return
        }

        logger.logAppSelection(app.applicationName)
        state = .starting

        do {
            // 1. Check engine health
            _ = try await engine.health()
            logger.logEngineStatus("connected")

            // 2. Start session
            let sessionId = UUID().uuidString
            currentSessionId = sessionId
            sessionStartTime = Date()

            let startRequest = StartSessionRequest(
                sessionId: sessionId,
                model: preferences.sttBackend,
                sampleRate: 48000,
                userSettings: UserSettings(
                    chunkSummaryPrompt: preferences.chunkSummaryPrompt,
                    finalSummaryPrompt: preferences.finalSummaryPrompt,
                    dataExtractionPrompt: preferences.dataExtractionPrompt,
                    llmModelName: preferences.llmModel,
                    outputDir: preferences.outputDir,
                    csvExportPath: preferences.csvExportPath,
                    appendCsv: preferences.appendCSV
                )
            )

            _ = try await engine.startSession(request: startRequest)

            // 3. Set up audio + error callbacks
            captureManager.onAudioCaptured = { [weak self] sampleBuffer, sampleRate in
                self?.handleAudioChunk(sampleBuffer: sampleBuffer, sampleRate: sampleRate)
            }
            captureManager.onError = { [weak self] error in
                guard let self = self else { return }
                self.logger.logError(error, context: "Screen capture error")
                Task { @MainActor in
                    self.state = .error(error.localizedDescription)
                }
            }

            // 4. Start capture
            do {
                lastAudioTimestamp = nil
                audioWatchdogTask?.cancel()
                try await captureManager.startCapture(for: app)
                usingMicFallback = false
                logger.logCaptureEvent("started", sessionId: sessionId, usingMicFallback: false)

                // Start audio watchdog: if no audio within 6 seconds, surface an error
                startAudioWatchdog(sessionId: sessionId, appName: app.applicationName)
            } catch {
                // Surface ScreenCaptureKit error to caller; no microphone fallback
                throw error
            }

            // 5. Update state
            await MainActor.run {
                state = .recording(sessionId: sessionId)
            }

            // 6. Send notification
            sendNotification(title: "Recording Started", body: "Capturing audio from \(app.applicationName)")

        } catch {
            logger.logError(error, context: "Failed to start recording")
            await MainActor.run {
                state = .error("Failed to start: \(error.localizedDescription)")
            }
        }
    }

    // MARK: - Stop Recording

    func stopRecording() async {
        guard case .recording(let sessionId) = state else {
            logger.warning("Cannot stop: not recording")
            return
        }

        logger.logCaptureEvent("stopping", sessionId: sessionId, usingMicFallback: usingMicFallback)
        state = .stopping

        audioWatchdogTask?.cancel()
        audioWatchdogTask = nil

        // 1. Stop capture (either screen capture or mic capture)
        if usingMicFallback {
            await micCaptureManager.stopCapture()
        } else {
            await captureManager.stopCapture()
        }

        // 2. Flush remaining chunks
        if !chunkBuffer.isEmpty {
            await flushChunkBuffer(sessionId: sessionId)
        }

        // 3. Stop session and generate summary (this can take 1-3 minutes for long recordings)
        await MainActor.run {
            bufferStatus = "Generating final summary... (this may take a few minutes)"
        }
        
        do {
            let stopRequest = StopSessionRequest(sessionId: sessionId)
            let result = try await engine.stopSession(request: stopRequest)

            // Calculate session duration
            let duration = sessionStartTime.map { Date().timeIntervalSince($0) }

            // Log session metadata (per spec §NFR4)
            logger.logSessionMetadata(
                sessionId: sessionId,
                duration: duration,
                audioChunks: audioChunkCount,
                status: result.sessionStatus
            )

            // 4. Save to recent sessions
            let record = SessionRecord(
                id: UUID(),
                sessionId: sessionId,
                timestamp: Date(),
                summaryPath: result.summaryPath,
                dataPath: result.dataPath,
                csvPath: result.csvPath,
                status: result.sessionStatus,
                company: nil,  // TODO: Parse from data.json
                contact: nil
            )

            await MainActor.run {
                sessionManager.addSession(record)
                state = .idle
            }

            logger.logCaptureEvent("stopped", sessionId: sessionId, usingMicFallback: usingMicFallback)

            // 5. Send notification
            if result.sessionStatus == "completed" {
                sendNotification(
                    title: "Summary Ready",
                    body: "Meeting summary has been generated"
                )
            } else {
                sendNotification(
                    title: "Recording Complete",
                    body: "Status: \(result.sessionStatus)"
                )
            }

            // Reset counters
            audioChunkCount = 0
            sessionStartTime = nil

        } catch {
            logger.logError(error, context: "Failed to stop recording")
            await MainActor.run {
                state = .error("Failed to stop: \(error.localizedDescription)")
            }
        }

        currentSessionId = nil
        audioChunkCount = 0
        lastAudioTimestamp = nil
    }

    // MARK: - Audio Chunk Handling

    private func handleAudioChunk(sampleBuffer: CMSampleBuffer, sampleRate: Int) {
        guard case .recording(let sessionId) = state else { return }

        // Mark that we have received audio
        lastAudioTimestamp = Date()

        // Buffer chunks
        chunkBuffer.append(sampleBuffer)

        if let sampleCount = CMSampleBufferGetNumSamples(sampleBuffer) as Int? {
            chunkBufferSampleCount += sampleCount
        }

        // Send when buffer is full
        if chunkBufferSampleCount >= chunkBufferSize {
            Task {
                await sendChunkBuffer(sessionId: sessionId)
            }
        }
    }

    private func sendChunkBuffer(sessionId: String) async {
        await processAndSendChunk(sessionId: sessionId)
    }

    private func flushChunkBuffer(sessionId: String) async {
        await processAndSendChunk(sessionId: sessionId)
    }
    
    private func processAndSendChunk(sessionId: String) async {
        guard !chunkBuffer.isEmpty else { return }

        do {
            // Merge and convert all buffers
            var allSamples: [Float] = []
            var finalSampleRate = 48000
            
            for buffer in chunkBuffer {
                // Extract samples
                if let (samples, rate, channels) = try? AudioProcessor.extractFloat32Samples(buffer) {
                    finalSampleRate = rate
                    
                    // Convert to mono
                    let monoSamples = channels > 1 ? AudioProcessor.stereoToMono(samples, channelCount: channels) : samples
                    
                    allSamples.append(contentsOf: monoSamples)
                }
            }
            
            guard !allSamples.isEmpty else {
                chunkBuffer.removeAll()
                chunkBufferSampleCount = 0
                return
            }
            
            // Normalize
            let normalizedSamples = AudioProcessor.normalize(allSamples)
            
            // Encode
            let pcmB64 = AudioProcessor.encodeToBase64(normalizedSamples)

            // Send to engine
            let chunkRequest = AudioChunkRequest(
                sessionId: sessionId,
                timestamp: Date().timeIntervalSince1970,
                pcmB64: pcmB64,
                sampleRate: finalSampleRate
            )

            let response = try await engine.sendAudioChunk(request: chunkRequest)

            audioChunkCount += 1

            // Update buffer status
            await MainActor.run {
                bufferStatus = String(format: "Chunk %d: %.1fs buffered, %d segments",
                                     audioChunkCount,
                                     response.bufferedSeconds,
                                     response.queueDepth)
            }

            // Clear buffer
            chunkBuffer.removeAll()
            chunkBufferSampleCount = 0

        } catch {
            print("Error sending chunk: \(error.localizedDescription)")
            // Clear buffer to avoid memory growth on persistent error
            chunkBuffer.removeAll()
            chunkBufferSampleCount = 0
        }
    }

    // MARK: - Audio Watchdog

    private func startAudioWatchdog(sessionId: String, appName: String) {
        audioWatchdogTask?.cancel()
        audioWatchdogTask = Task { [weak self] in
            guard let self = self else { return }

            // Wait 6 seconds after start; if still no audio, surface an error
            try? await Task.sleep(nanoseconds: 6_000_000_000)

            // If task was cancelled or state changed, do nothing
            guard !Task.isCancelled else { return }
            guard case .recording = self.state else { return }

            let hadAudio = self.lastAudioTimestamp != nil
            if hadAudio {
                return
            }

            self.logger.warning("No audio received from ScreenCaptureKit within watchdog window; stopping capture and surfacing error")

            await self.captureManager.stopCapture()
            await MainActor.run {
                self.state = .error("No audio detected from \(appName). Screen capture did not deliver any audio samples.")
                self.sendNotification(
                    title: "No Call Audio Detected",
                    body: "Screen capture from \(appName) did not produce audio. Check Screen Recording and Microphone permissions, then try again."
                )
            }
        }
    }

    // MARK: - Notifications

    private func sendNotification(title: String, body: String) {
        let content = UNMutableNotificationContent()
        content.title = title
        content.body = body
        content.sound = .default

        let request = UNNotificationRequest(
            identifier: UUID().uuidString,
            content: content,
            trigger: nil
        )

        UNUserNotificationCenter.current().add(request)
    }
}
