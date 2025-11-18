// EngineClient.swift
// HTTP client for communicating with Audio Summary Engine
// Per spec §4.2 (FR7) - HTTP API endpoints

import Foundation

class EngineClient {
    let baseURL: URL
    let authToken: String?
    private let session: URLSession

    init(baseURL: URL, authToken: String? = nil) {
        self.baseURL = baseURL
        self.authToken = authToken

        // Configure URLSession with reasonable timeouts
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30.0  // 30s per request
        config.timeoutIntervalForResource = 300.0  // 5min total
        self.session = URLSession(configuration: config)
    }

    // MARK: - Health Check

    func health() async throws -> HealthResponse {
        return try await request("/health", method: "GET")
    }

    // MARK: - Start Session

    func startSession(request: StartSessionRequest) async throws -> StartSessionResponse {
        return try await self.request("/start_session", method: "POST", body: request)
    }

    // MARK: - Send Audio Chunk

    func sendAudioChunk(request: AudioChunkRequest) async throws -> AudioChunkResponse {
        return try await self.request("/audio_chunk", method: "POST", body: request)
    }

    // MARK: - Stop Session

    func stopSession(request: StopSessionRequest) async throws -> StopSessionResponse {
        return try await self.request("/stop_session", method: "POST", body: request)
    }

    // MARK: - Generic Request Method

    private func request<T: Decodable>(
        _ endpoint: String,
        method: String = "GET",
        body: (any Encodable)? = nil
    ) async throws -> T {
        // Build URL
        let url = baseURL.appendingPathComponent(endpoint)
        var urlRequest = URLRequest(url: url)
        urlRequest.httpMethod = method

        // Set headers
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")

        // Add auth token if present
        if let authToken = authToken {
            urlRequest.setValue(authToken, forHTTPHeaderField: "X-Engine-Token")
        }

        // Encode body if present
        if let body = body {
            do {
                let encoder = JSONEncoder()
                urlRequest.httpBody = try encoder.encode(body)
            } catch {
                throw EngineError.encodingError(error)
            }
        }

        // Perform request
        let (data, response): (Data, URLResponse)
        do {
            (data, response) = try await session.data(for: urlRequest)
        } catch {
            throw EngineError.networkError(error)
        }

        // Validate HTTP response
        guard let httpResponse = response as? HTTPURLResponse else {
            throw EngineError.invalidResponse
        }

        // Check status code
        guard (200...299).contains(httpResponse.statusCode) else {
            // Try to decode error response
            let errorResponse = try? JSONDecoder().decode(ErrorResponse.self, from: data)
            throw EngineError.httpError(statusCode: httpResponse.statusCode, error: errorResponse)
        }

        // Decode successful response
        do {
            let decoder = JSONDecoder()
            return try decoder.decode(T.self, from: data)
        } catch {
            // Log response data for debugging
            if let responseStr = String(data: data, encoding: .utf8) {
                print("Failed to decode response: \(responseStr)")
            }
            throw EngineError.decodingError(error)
        }
    }
}
