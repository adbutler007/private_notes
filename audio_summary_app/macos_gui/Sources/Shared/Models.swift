// Models.swift
// Data models for engine API requests/responses
// Matches Python engine API schema per spec §4.2

import Foundation

// MARK: - Health Endpoint

struct HealthResponse: Codable {
    let status: String
    let engineVersion: String
    let apiVersion: String
    let sttBackends: [String]
    let llmModels: [String]

    enum CodingKeys: String, CodingKey {
        case status
        case engineVersion = "engine_version"
        case apiVersion = "api_version"
        case sttBackends = "stt_backends"
        case llmModels = "llm_models"
    }
}

// MARK: - Start Session Endpoint

struct UserSettings: Codable {
    let chunkSummaryPrompt: String
    let finalSummaryPrompt: String
    let dataExtractionPrompt: String?
    let llmModelName: String
    let outputDir: String
    let csvExportPath: String
    let appendCsv: Bool

    enum CodingKeys: String, CodingKey {
        case chunkSummaryPrompt = "chunk_summary_prompt"
        case finalSummaryPrompt = "final_summary_prompt"
        case dataExtractionPrompt = "data_extraction_prompt"
        case llmModelName = "llm_model_name"
        case outputDir = "output_dir"
        case csvExportPath = "csv_export_path"
        case appendCsv = "append_csv"
    }
}

struct StartSessionRequest: Codable {
    let sessionId: String
    let model: String  // "whisper" or "parakeet"
    let sampleRate: Int
    let userSettings: UserSettings

    enum CodingKeys: String, CodingKey {
        case sessionId = "session_id"
        case model
        case sampleRate = "sample_rate"
        case userSettings = "user_settings"
    }
}

struct StartSessionResponse: Codable {
    let status: String
}

// MARK: - Audio Chunk Endpoint

struct AudioChunkRequest: Codable {
    let sessionId: String
    let timestamp: Double
    let pcmB64: String
    let sampleRate: Int

    enum CodingKeys: String, CodingKey {
        case sessionId = "session_id"
        case timestamp
        case pcmB64 = "pcm_b64"
        case sampleRate = "sample_rate"
    }
}

struct AudioChunkResponse: Codable {
    let status: String
    let bufferedSeconds: Double
    let queueDepth: Int

    enum CodingKeys: String, CodingKey {
        case status
        case bufferedSeconds = "buffered_seconds"
        case queueDepth = "queue_depth"
    }
}

// MARK: - Stop Session Endpoint

struct StopSessionRequest: Codable {
    let sessionId: String

    enum CodingKeys: String, CodingKey {
        case sessionId = "session_id"
    }
}

struct StopSessionResponse: Codable {
    let status: String
    let summaryPath: String?
    let dataPath: String?
    let csvPath: String?
    let sessionStatus: String

    enum CodingKeys: String, CodingKey {
        case status
        case summaryPath = "summary_path"
        case dataPath = "data_path"
        case csvPath = "csv_path"
        case sessionStatus = "session_status"
    }
}

// MARK: - Error Response

struct ErrorResponse: Codable {
    let status: String
    let errorCode: String
    let message: String
    let details: [String: String]

    enum CodingKeys: String, CodingKey {
        case status
        case errorCode = "error_code"
        case message
        case details
    }
}

// MARK: - Engine Errors

enum EngineError: Error, LocalizedError {
    case invalidResponse
    case httpError(statusCode: Int, error: ErrorResponse?)
    case networkError(Error)
    case decodingError(Error)
    case encodingError(Error)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "Invalid response from engine"
        case .httpError(let code, let error):
            if let error = error {
                return "HTTP \(code): [\(error.errorCode)] \(error.message)"
            }
            return "HTTP error: \(code)"
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        case .decodingError(let error):
            return "Failed to decode response: \(error.localizedDescription)"
        case .encodingError(let error):
            return "Failed to encode request: \(error.localizedDescription)"
        }
    }
}
