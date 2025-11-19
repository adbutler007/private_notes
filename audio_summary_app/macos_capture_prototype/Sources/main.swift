// main.swift
// Audio Capture Prototype - Phase 2
// Console app that captures Zoom/Teams audio and sends to engine
// Per spec §7: Phase 2 - Swift ScreenCaptureKit Prototype

import Foundation
import ScreenCaptureKit

// MARK: - Configuration

let ENGINE_URL = "http://127.0.0.1:8756"
let CAPTURE_DURATION_SECONDS: UInt32 = 60  // Capture for 60 seconds
let CHUNK_BUFFER_SIZE = 96000  // ~2 seconds at 48kHz

// Default prompts (from Python config)
let DEFAULT_CHUNK_PROMPT = """
Summarize this conversation segment in 2-3 concise paragraphs. Focus on:
- Main discussion points and context
- Key decisions or action items
- Important information shared

If contact/company/deal data is mentioned (names, roles, AUM, ticket sizes, products, strategies), note it briefly but do NOT format it as structured lists - that will be extracted separately.

Transcript:
{text}

Summary:
"""

let DEFAULT_FINAL_PROMPT = """
You are summarizing a sales discovery call at an asset management company focused on alternative investments.

Create a maximally concise final summary:
1. Meeting context and participants
2. Key discussion points and client needs
3. Important decisions or next steps
4. Notable insights or observations

Strictly summarize the provided meeting context and nothing else. Never hallucinate or add additional information. DO NOT repeat structured data (names, roles, AUM, ticket sizes, products) in list format - this will be extracted separately. Keep the summary narrative and flowing.

Segment Summaries:
{summaries_text}

Final Summary:
"""

let DEFAULT_DATA_EXTRACTION_PROMPT = """
You are extracting structured data from meeting summaries. Review the summaries below and extract all mentioned information into the specified JSON format.

If information is not mentioned or unclear, use null for that field.

Summaries:
{summaries_text}

Extract the following information as JSON:
"""

// MARK: - Global State

var chunkBuffer: [CMSampleBuffer] = []
var chunkBufferSampleCount = 0
var isShuttingDown = false

// MARK: - Main Entry Point

// Set up signal handling for graceful shutdown
signal(SIGINT) { _ in
    print("\n\nReceived interrupt signal (Ctrl+C)")
    isShuttingDown = true
}

Task {
    do {
        // Run the prototype
        try await runPrototype()
        exit(0)
    } catch {
        print("\nERROR: \(error.localizedDescription)")
        exit(1)
    }
}

// Keep process alive
dispatchMain()

// MARK: - Main Prototype Logic

func runPrototype() async throws {
    // 1. List shareable content
    print("1. Listing available applications...")
    let captureManager = ScreenCaptureManager()
    let content = try await captureManager.getShareableContent()

    print("   Found \(content.applications.count) running applications")

    // 2. Filter for Zoom/Teams
    print("\n2. Filtering for Zoom/Teams...")
    let targetApps = captureManager.findTargetApps(in: content)

    guard !targetApps.isEmpty else {
        throw ScreenCaptureError.noTargetAppFound
    }

    print("   Found \(targetApps.count) target app(s):")
    for (index, app) in targetApps.enumerated() {
        print("   [\(index + 1)] \(app.applicationName) (\(app.bundleIdentifier))")
    }

    // 3. Select app (auto-select if only one, otherwise prompt)
    let selectedApp: SCRunningApplication
    if targetApps.count == 1 {
        selectedApp = targetApps[0]
        print("\n   Auto-selecting: \(selectedApp.applicationName)")
    } else {
        print("\nSelect app [1-\(targetApps.count)]: ", terminator: "")
        guard let input = readLine(), let selection = Int(input),
              selection >= 1 && selection <= targetApps.count else {
            print("Invalid selection")
            exit(1)
        }
        selectedApp = targetApps[selection - 1]
    }

    // 4. Initialize engine client
    print("\n3. Connecting to engine...")
    guard let engineURL = URL(string: ENGINE_URL) else {
        print("ERROR: Invalid engine URL")
        exit(1)
    }

    let engine = EngineClient(baseURL: engineURL)

    // 5. Check engine health
    do {
        let health = try await engine.health()
        print("   Engine version: \(health.engineVersion)")
        print("   API version: \(health.apiVersion)")
        print("   STT backends: \(health.sttBackends.joined(separator: ", "))")
        print("   LLM models: \(health.llmModels.joined(separator: ", "))")
    } catch {
        print("   ERROR: Engine not responding. Make sure it's running:")
        print("   → uv run audio-summary-server")
        throw error
    }

    // 6. Start session
    print("\n4. Starting session...")
    let sessionId = UUID().uuidString

    let startRequest = StartSessionRequest(
        sessionId: sessionId,
        model: "whisper",  // Use Whisper backend
        sampleRate: 48000,  // ScreenCaptureKit provides 48kHz
        userSettings: UserSettings(
            chunkSummaryPrompt: DEFAULT_CHUNK_PROMPT,
            finalSummaryPrompt: DEFAULT_FINAL_PROMPT,
            dataExtractionPrompt: DEFAULT_DATA_EXTRACTION_PROMPT,
            llmModelName: "qwen3:4b-instruct",
            outputDir: "~/Documents/Meeting Summaries",
            csvExportPath: "~/Documents/Meeting Summaries/meetings.csv",
            appendCsv: true
        )
    )

    do {
        _ = try await engine.startSession(request: startRequest)
        print("   Session ID: \(sessionId)")
        print("   Session started successfully")
    } catch {
        print("   ERROR: Failed to start session")
        throw error
    }

    // 7. Start capture
    print("\n5. Starting audio capture from \(selectedApp.applicationName)...")
    print("   Press Ctrl+C to stop (or capturing for \(CAPTURE_DURATION_SECONDS)s)\n")

    var audioChunkCount = 0
    var totalAudioDuration: Double = 0.0

    // Set up audio callback
    captureManager.onAudioCaptured = { sampleBuffer, sampleRate in
        // Buffer chunks to reduce HTTP overhead
        chunkBuffer.append(sampleBuffer)

        // Count samples (for display purposes)
        if let sampleCount = CMSampleBufferGetNumSamples(sampleBuffer) as Int? {
            chunkBufferSampleCount += sampleCount
        }

        // Send chunk when buffer is large enough (~2 seconds)
        if chunkBufferSampleCount >= CHUNK_BUFFER_SIZE {
            Task {
                do {
                    // Merge buffered samples
                    guard let mergedBuffer = chunkBuffer.first else { return }

                    // Convert to base64 PCM
                    let (pcmB64, actualSampleRate) = try AudioProcessor.convertToBase64PCM(mergedBuffer)

                    // Send to engine
                    let chunkRequest = AudioChunkRequest(
                        sessionId: sessionId,
                        timestamp: Date().timeIntervalSince1970,
                        pcmB64: pcmB64,
                        sampleRate: actualSampleRate
                    )

                    let response = try await engine.sendAudioChunk(request: chunkRequest)

                    audioChunkCount += 1
                    totalAudioDuration += response.bufferedSeconds

                    print("   Chunk \(audioChunkCount): \(actualSampleRate) Hz, " +
                          "\(chunkBufferSampleCount) samples → " +
                          "buffered: \(String(format: "%.1f", response.bufferedSeconds))s, " +
                          "queue: \(response.queueDepth) segments")

                    // Clear buffer
                    chunkBuffer.removeAll()
                    chunkBufferSampleCount = 0

                } catch {
                    print("   ERROR sending chunk: \(error.localizedDescription)")
                }
            }
        }
    }

    try await captureManager.startCapture(for: selectedApp)

    // 8. Run for duration (or until interrupted)
    let startTime = Date()
    while !isShuttingDown {
        try await Task.sleep(nanoseconds: 1_000_000_000)  // Sleep 1 second

        let elapsed = Date().timeIntervalSince(startTime)
        if elapsed >= Double(CAPTURE_DURATION_SECONDS) {
            print("\n   Reached \(CAPTURE_DURATION_SECONDS)s capture duration")
            break
        }
    }

    // 9. Stop capture
    print("\n6. Stopping capture...")
    await captureManager.stopCapture()

    // Flush any remaining buffered chunks
    if !chunkBuffer.isEmpty {
        print("   Flushing remaining \(chunkBuffer.count) buffered chunk(s)...")
        if let mergedBuffer = chunkBuffer.first {
            do {
                let (pcmB64, actualSampleRate) = try AudioProcessor.convertToBase64PCM(mergedBuffer)
                let chunkRequest = AudioChunkRequest(
                    sessionId: sessionId,
                    timestamp: Date().timeIntervalSince1970,
                    pcmB64: pcmB64,
                    sampleRate: actualSampleRate
                )
                _ = try await engine.sendAudioChunk(request: chunkRequest)
                print("   Flushed final chunk")
            } catch {
                print("   Warning: Failed to flush final chunk: \(error.localizedDescription)")
            }
        }
    }

    print("   Sent \(audioChunkCount) total chunks")

    // 10. Stop session
    print("\n7. Stopping session and generating summary...")
    print("   This may take 30-60 seconds depending on transcript length...\n")

    let stopRequest = StopSessionRequest(sessionId: sessionId)

    do {
        let result = try await engine.stopSession(request: stopRequest)

        // 11. Print results
        print("=== Session Complete ===")
        print("Status: \(result.sessionStatus)")

        if let summaryPath = result.summaryPath {
            print("Summary: \(summaryPath)")

            // Read and display summary
            if let summaryContent = try? String(contentsOfFile: summaryPath.replacingOccurrences(of: "~", with: NSHomeDirectory())) {
                print("\n--- Generated Summary ---")
                print(summaryContent)
                print("--- End Summary ---")
            }
        }

        if let dataPath = result.dataPath {
            print("Data: \(dataPath)")
        }

        if let csvPath = result.csvPath {
            print("CSV: \(csvPath)")
        }

        print("\n=== Prototype Complete ===")

    } catch {
        print("ERROR stopping session: \(error.localizedDescription)")
        throw error
    }
}
