// SessionManager.swift
// Tracks recording sessions and recent summaries
// Per spec §4.1 FR5 - Recent Summaries menu

import Foundation
import AppKit

struct SessionRecord: Codable, Identifiable {
    let id: UUID
    let sessionId: String
    let timestamp: Date
    let summaryPath: String?
    let dataPath: String?
    let csvPath: String?
    let status: String
    let company: String?
    let contact: String?

    var displayName: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd HH:mm"
        let dateStr = formatter.string(from: timestamp)

        if let company = company, let contact = contact {
            return "\(dateStr) – \(company) – \(contact)"
        } else if let company = company {
            return "\(dateStr) – \(company)"
        } else {
            return dateStr
        }
    }
}

class SessionManager: ObservableObject {
    static let shared = SessionManager()

    @Published var recentSessions: [SessionRecord] = []

    private let defaults = UserDefaults.standard
    private let maxRecentSessions = 5
    private let sessionsKey = "recent_sessions"

    private init() {
        loadSessions()
    }

    // MARK: - Add Session

    func addSession(_ record: SessionRecord) {
        recentSessions.insert(record, at: 0)

        // Keep only the most recent N sessions
        if recentSessions.count > maxRecentSessions {
            recentSessions = Array(recentSessions.prefix(maxRecentSessions))
        }

        saveSessions()
    }

    // MARK: - Get Recent Sessions

    func getRecentSessions() -> [SessionRecord] {
        return recentSessions
    }

    // MARK: - Persistence

    private func saveSessions() {
        if let encoded = try? JSONEncoder().encode(recentSessions) {
            defaults.set(encoded, forKey: sessionsKey)
        }
    }

    private func loadSessions() {
        if let data = defaults.data(forKey: sessionsKey),
           let sessions = try? JSONDecoder().decode([SessionRecord].self, from: data) {
            recentSessions = sessions
        }
    }

    // MARK: - Open Summary

    func openSummary(for record: SessionRecord) {
        guard let summaryPath = record.summaryPath else {
            print("No summary path for session")
            return
        }

        // Expand tilde in path
        let expandedPath = NSString(string: summaryPath).expandingTildeInPath
        let url = URL(fileURLWithPath: expandedPath)

        // Open in default text editor
        NSWorkspace.shared.open(url)
    }
}
