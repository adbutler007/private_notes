// PreferencesManager.swift
// Manages user preferences and settings via UserDefaults
// Per spec §4.1 FR4 - Settings persistence

import Foundation

class PreferencesManager: ObservableObject {
    static let shared = PreferencesManager()

    private let defaults = UserDefaults.standard

    // MARK: - Keys

    private enum Keys {
        static let firstRunCompleted = "first_run_completed"
        static let selectedAppBundleID = "selected_app_bundle_id"
        static let sttBackend = "stt_backend"
        static let whisperModel = "whisper_model"
        static let parakeetModel = "parakeet_model"
        static let llmModel = "llm_model"
        static let chunkSummaryPrompt = "chunk_summary_prompt"
        static let finalSummaryPrompt = "final_summary_prompt"
        static let dataExtractionPrompt = "data_extraction_prompt"
        static let outputDir = "output_dir"
        static let csvExportPath = "csv_export_path"
        static let appendCSV = "append_csv"
        static let enableDebugLogging = "enable_debug_logging"
        static let allowMicFallback = "allow_mic_fallback"
    }

    // MARK: - First Run

    @Published var firstRunCompleted: Bool {
        didSet {
            defaults.set(firstRunCompleted, forKey: Keys.firstRunCompleted)
        }
    }

    // MARK: - Capture Settings

    @Published var selectedAppBundleID: String? {
        didSet {
            defaults.set(selectedAppBundleID, forKey: Keys.selectedAppBundleID)
        }
    }

    // MARK: - Model Settings

    @Published var sttBackend: String {
        didSet {
            defaults.set(sttBackend, forKey: Keys.sttBackend)
        }
    }

    @Published var whisperModel: String {
        didSet {
            defaults.set(whisperModel, forKey: Keys.whisperModel)
        }
    }

    @Published var parakeetModel: String {
        didSet {
            defaults.set(parakeetModel, forKey: Keys.parakeetModel)
        }
    }

    @Published var llmModel: String {
        didSet {
            defaults.set(llmModel, forKey: Keys.llmModel)
        }
    }

    // Convenience alias for SettingsView
    var llmModelName: String {
        get { llmModel }
        set { llmModel = newValue }
    }

    // MARK: - Prompts

    @Published var chunkSummaryPrompt: String {
        didSet {
            defaults.set(chunkSummaryPrompt, forKey: Keys.chunkSummaryPrompt)
        }
    }

    @Published var finalSummaryPrompt: String {
        didSet {
            defaults.set(finalSummaryPrompt, forKey: Keys.finalSummaryPrompt)
        }
    }

    @Published var dataExtractionPrompt: String {
        didSet {
            defaults.set(dataExtractionPrompt, forKey: Keys.dataExtractionPrompt)
        }
    }

    // MARK: - Export Settings

    @Published var outputDir: String {
        didSet {
            defaults.set(outputDir, forKey: Keys.outputDir)
        }
    }

    @Published var csvExportPath: String {
        didSet {
            defaults.set(csvExportPath, forKey: Keys.csvExportPath)
        }
    }

    @Published var appendCSV: Bool {
        didSet {
            defaults.set(appendCSV, forKey: Keys.appendCSV)
        }
    }

    // Convenience alias for SettingsView
    var appendCsv: Bool {
        get { appendCSV }
        set { appendCSV = newValue }
    }

    // MARK: - Advanced Settings

    @Published var enableDebugLogging: Bool {
        didSet {
            defaults.set(enableDebugLogging, forKey: Keys.enableDebugLogging)
        }
    }

    @Published var allowMicFallback: Bool {
        didSet {
            defaults.set(allowMicFallback, forKey: Keys.allowMicFallback)
        }
    }

    // Convenience alias for SettingsView
    var enableMicFallback: Bool {
        get { allowMicFallback }
        set { allowMicFallback = newValue }
    }

    // Convenience alias for SettingsView
    var debugLogging: Bool {
        get { enableDebugLogging }
        set { enableDebugLogging = newValue }
    }

    // MARK: - Initialization

    private init() {
        // Load from defaults or use default values
        firstRunCompleted = defaults.bool(forKey: Keys.firstRunCompleted)
        selectedAppBundleID = defaults.string(forKey: Keys.selectedAppBundleID)

        // Models - Per spec §4.1 FR4
        sttBackend = defaults.string(forKey: Keys.sttBackend) ?? "whisper"  // whisper is default per spec
        whisperModel = defaults.string(forKey: Keys.whisperModel) ?? "turbo"  // turbo is a good default
        parakeetModel = defaults.string(forKey: Keys.parakeetModel) ?? "v3"  // v3 is latest
        llmModel = defaults.string(forKey: Keys.llmModel) ?? "qwen3:4b-instruct"  // per spec

        // Prompts (use defaults from spec)
        chunkSummaryPrompt = defaults.string(forKey: Keys.chunkSummaryPrompt) ?? Self.defaultChunkPrompt
        finalSummaryPrompt = defaults.string(forKey: Keys.finalSummaryPrompt) ?? Self.defaultFinalPrompt
        dataExtractionPrompt = defaults.string(forKey: Keys.dataExtractionPrompt) ?? Self.defaultDataExtractionPrompt

        // Export
        outputDir = defaults.string(forKey: Keys.outputDir) ?? "~/Documents/Meeting Summaries"
        csvExportPath = defaults.string(forKey: Keys.csvExportPath) ?? "~/Documents/Meeting Summaries/meetings.csv"
        appendCSV = defaults.object(forKey: Keys.appendCSV) as? Bool ?? true

        // Advanced
        enableDebugLogging = defaults.bool(forKey: Keys.enableDebugLogging)
        allowMicFallback = defaults.bool(forKey: Keys.allowMicFallback)
    }

    // MARK: - Reset to Defaults

    func resetPromptsToDefaults() {
        chunkSummaryPrompt = Self.defaultChunkPrompt
        finalSummaryPrompt = Self.defaultFinalPrompt
        dataExtractionPrompt = Self.defaultDataExtractionPrompt
    }

    // MARK: - Default Prompts

    static let defaultChunkPrompt = """
    Summarize this conversation segment in 2-3 concise paragraphs. Focus on:
    - Main discussion points and context
    - Key decisions or action items
    - Important information shared

    If contact/company/deal data is mentioned (names, roles, AUM, ticket sizes, products, strategies), note it briefly but do NOT format it as structured lists - that will be extracted separately.

    Transcript:
    {text}

    Summary:
    """

    static let defaultFinalPrompt = """
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

    static let defaultDataExtractionPrompt = """
    You are extracting structured data from meeting summaries. Review the summaries below and extract all mentioned information into the specified JSON format.

    If information is not mentioned or unclear, use null for that field.

    Summaries:
    {summaries_text}

    Extract the following information as JSON:
    """
}
