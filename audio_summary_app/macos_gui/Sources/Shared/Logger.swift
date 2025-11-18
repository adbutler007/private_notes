// Logger.swift
// Centralized logging for Audio Summary GUI
// Per spec §NFR4 - Observability

import Foundation
import os.log

class AppLogger {
    static let shared = AppLogger()

    private let logger: OSLog
    private let fileLogger: FileHandle?
    private let preferences = PreferencesManager.shared

    private init() {
        // System logger (goes to Console.app)
        logger = OSLog(subsystem: "com.audiosummary.gui", category: "general")

        // File logger (if debug logging enabled)
        if preferences.enableDebugLogging {
            let logDir = FileManager.default.homeDirectoryForCurrentUser
                .appendingPathComponent("Library/Logs/Audio Summary")

            try? FileManager.default.createDirectory(at: logDir, withIntermediateDirectories: true)

            let logFile = logDir.appendingPathComponent("last.log")

            // Truncate existing log file
            FileManager.default.createFile(atPath: logFile.path, contents: nil)

            fileLogger = try? FileHandle(forWritingTo: logFile)
        } else {
            fileLogger = nil
        }
    }

    deinit {
        try? fileLogger?.close()
    }

    // MARK: - Logging Methods

    func info(_ message: String, file: String = #file, function: String = #function, line: Int = #line) {
        log(message, level: .info, file: file, function: function, line: line)
    }

    func debug(_ message: String, file: String = #file, function: String = #function, line: Int = #line) {
        log(message, level: .debug, file: file, function: function, line: line)
    }

    func error(_ message: String, file: String = #file, function: String = #function, line: Int = #line) {
        log(message, level: .error, file: file, function: function, line: line)
    }

    func warning(_ message: String, file: String = #file, function: String = #function, line: Int = #line) {
        log(message, level: .default, file: file, function: function, line: line)
    }

    // MARK: - Event Logging (Per spec §NFR4)

    /// Log app selection (per spec requirement)
    func logAppSelection(_ app: String) {
        info("App selected: \(app)")
    }

    /// Log permission status (per spec requirement)
    func logPermissionStatus(_ permission: String, granted: Bool) {
        info("Permission \(permission): \(granted ? "granted" : "denied")")
    }

    /// Log capture start/stop (per spec requirement)
    func logCaptureEvent(_ event: String, sessionId: String?, usingMicFallback: Bool = false) {
        let source = usingMicFallback ? "microphone (fallback)" : "screen capture"
        if let sid = sessionId {
            info("Capture \(event): session=\(sid), source=\(source)")
        } else {
            info("Capture \(event): source=\(source)")
        }
    }

    /// Log engine health/connection status (per spec requirement)
    func logEngineStatus(_ status: String, details: String? = nil) {
        if let d = details {
            info("Engine status: \(status) - \(d)")
        } else {
            info("Engine status: \(status)")
        }
    }

    /// Log session metadata (per spec §NFR4 - no transcript text)
    func logSessionMetadata(sessionId: String, duration: TimeInterval?, audioChunks: Int?, status: String) {
        var msg = "Session \(sessionId): status=\(status)"
        if let dur = duration {
            msg += ", duration=\(String(format: "%.1f", dur))s"
        }
        if let chunks = audioChunks {
            msg += ", chunks=\(chunks)"
        }
        info(msg)
    }

    /// Log errors with context
    func logError(_ error: Error, context: String) {
        self.error("\(context): \(error.localizedDescription)")
    }

    // MARK: - Internal Logging

    private func log(_ message: String, level: OSLogType, file: String, function: String, line: Int) {
        let fileName = (file as NSString).lastPathComponent
        let timestamp = ISO8601DateFormatter().string(from: Date())

        // Log to system logger (Console.app)
        os_log("%{public}@", log: logger, type: level, message)

        // Log to file if debug logging enabled
        if preferences.enableDebugLogging, let fh = fileLogger {
            let levelStr: String
            switch level {
            case .info: levelStr = "INFO"
            case .debug: levelStr = "DEBUG"
            case .error: levelStr = "ERROR"
            case .fault: levelStr = "FAULT"
            default: levelStr = "DEFAULT"
            }

            let logLine = "[\(timestamp)] [\(levelStr)] [\(fileName):\(line) \(function)] \(message)\n"

            if let data = logLine.data(using: .utf8) {
                try? fh.write(contentsOf: data)
            }
        }
    }
}
