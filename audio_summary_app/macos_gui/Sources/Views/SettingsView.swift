// SettingsView.swift
// Settings window with 5 sections
// Per spec §4.1 FR4 - Settings Window

import SwiftUI
import ScreenCaptureKit

struct SettingsView: View {
    @EnvironmentObject var preferences: PreferencesManager

    @State private var showingResetConfirmation = false

    var body: some View {
        TabView {
            CaptureSettingsView()
                .environmentObject(preferences)
                .tabItem {
                    Label("Capture", systemImage: "video.fill")
                }

            ModelsSettingsView()
                .environmentObject(preferences)
                .tabItem {
                    Label("Models", systemImage: "cpu")
                }

            PromptsSettingsView()
                .environmentObject(preferences)
                .tabItem {
                    Label("Prompts", systemImage: "text.alignleft")
                }

            ExportSettingsView()
                .environmentObject(preferences)
                .tabItem {
                    Label("Export", systemImage: "square.and.arrow.up")
                }

            AdvancedSettingsView()
                .environmentObject(preferences)
                .tabItem {
                    Label("Advanced", systemImage: "gearshape.2")
                }
        }
        .padding(20)
        .frame(width: 600, height: 700)
    }
}

// MARK: - Capture Settings

struct CaptureSettingsView: View {
    @EnvironmentObject var preferences: PreferencesManager

    var body: some View {
        Form {
            Section(header: Text("Capture Source").font(.headline)) {
                Text("Target Application")
                    .font(.subheadline)
                    .foregroundColor(.secondary)

                Text("Currently capturing from: Zoom or Microsoft Teams")
                    .padding(.vertical, 4)

                Button("Re-run First-Time Setup Wizard") {
                    preferences.firstRunCompleted = false
                    // Trigger wizard restart
                    NSApp.keyWindow?.close()
                }
                .padding(.top, 8)
            }
        }
        .formStyle(.grouped)
    }
}

// MARK: - Models Settings

struct ModelsSettingsView: View {
    @EnvironmentObject var preferences: PreferencesManager

    private let sttBackends = ["whisper", "parakeet"]
    // Per spec §4.1 FR4 - Whisper model dropdown
    private let whisperModels = ["tiny", "small", "medium", "large", "turbo"]
    // Per spec §4.1 FR4 - Parakeet model dropdown (version names)
    private let parakeetModels = ["v3", "v2"]

    var body: some View {
        Form {
            Section(header: Text("Speech-to-Text").font(.headline)) {
                Picker("STT Backend:", selection: $preferences.sttBackend) {
                    ForEach(sttBackends, id: \.self) { backend in
                        Text(backend.capitalized).tag(backend)
                    }
                }
                .pickerStyle(.segmented)

                if preferences.sttBackend == "whisper" {
                    Picker("Whisper Model:", selection: $preferences.whisperModel) {
                        ForEach(whisperModels, id: \.self) { model in
                            Text(model).tag(model)
                        }
                    }
                } else {
                    Picker("Parakeet Model:", selection: $preferences.parakeetModel) {
                        ForEach(parakeetModels, id: \.self) { model in
                            Text(model).tag(model)
                        }
                    }
                }
            }

            Section(header: Text("Summarization LLM").font(.headline)) {
                TextField("LLM Model Name:", text: $preferences.llmModelName)
                    .textFieldStyle(.roundedBorder)

                Text("Example: qwen3:4b-instruct, llama3.2:3b, phi3:3.8b")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
        .formStyle(.grouped)
    }
}

// MARK: - Prompts Settings

struct PromptsSettingsView: View {
    @EnvironmentObject var preferences: PreferencesManager

    @State private var showingResetConfirmation = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                // Chunk Summary Prompt
                VStack(alignment: .leading, spacing: 8) {
                    Text("Chunk Summary Prompt")
                        .font(.headline)

                    Text("Used to summarize each ~30-second audio segment")
                        .font(.caption)
                        .foregroundColor(.secondary)

                    TextEditor(text: $preferences.chunkSummaryPrompt)
                        .font(.system(.body, design: .monospaced))
                        .frame(height: 150)
                        .border(Color.gray.opacity(0.3), width: 1)
                }

                // Final Summary Prompt
                VStack(alignment: .leading, spacing: 8) {
                    Text("Final Summary Prompt")
                        .font(.headline)

                    Text("Used to create the final summary from all chunk summaries")
                        .font(.caption)
                        .foregroundColor(.secondary)

                    TextEditor(text: $preferences.finalSummaryPrompt)
                        .font(.system(.body, design: .monospaced))
                        .frame(height: 150)
                        .border(Color.gray.opacity(0.3), width: 1)
                }

                // Data Extraction Prompt
                VStack(alignment: .leading, spacing: 8) {
                    Text("Data Extraction Prompt")
                        .font(.headline)

                    Text("Used to extract structured data (contacts, companies, etc.)")
                        .font(.caption)
                        .foregroundColor(.secondary)

                    TextEditor(text: $preferences.dataExtractionPrompt)
                        .font(.system(.body, design: .monospaced))
                        .frame(height: 150)
                        .border(Color.gray.opacity(0.3), width: 1)
                }

                // Reset Button
                Button("Reset Prompts to Defaults") {
                    showingResetConfirmation = true
                }
                .padding(.top, 8)
                .alert("Reset Prompts?", isPresented: $showingResetConfirmation) {
                    Button("Cancel", role: .cancel) { }
                    Button("Reset", role: .destructive) {
                        preferences.resetPromptsToDefaults()
                    }
                } message: {
                    Text("This will reset all prompts to their default values. Your custom prompts will be lost.")
                }
            }
            .padding()
        }
    }
}

// MARK: - Export Settings

struct ExportSettingsView: View {
    @EnvironmentObject var preferences: PreferencesManager

    var body: some View {
        Form {
            Section(header: Text("Output Directories").font(.headline)) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Summaries Directory:")
                        .font(.subheadline)

                    HStack {
                        TextField("", text: $preferences.outputDir)
                            .textFieldStyle(.roundedBorder)

                        Button("Choose...") {
                            selectDirectory(current: preferences.outputDir) { newPath in
                                preferences.outputDir = newPath
                            }
                        }
                    }
                }
                .padding(.vertical, 4)

                VStack(alignment: .leading, spacing: 8) {
                    Text("CSV Export Path:")
                        .font(.subheadline)

                    HStack {
                        TextField("", text: $preferences.csvExportPath)
                            .textFieldStyle(.roundedBorder)

                        Button("Choose...") {
                            selectFile(current: preferences.csvExportPath) { newPath in
                                preferences.csvExportPath = newPath
                            }
                        }
                    }
                }
                .padding(.vertical, 4)

                Toggle("Append to existing CSV", isOn: $preferences.appendCsv)
                    .padding(.vertical, 4)
            }
        }
        .formStyle(.grouped)
    }

    private func selectDirectory(current: String, completion: @escaping (String) -> Void) {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        panel.canCreateDirectories = true
        panel.directoryURL = URL(fileURLWithPath: NSString(string: current).expandingTildeInPath)

        if panel.runModal() == .OK {
            if let url = panel.url {
                let path = url.path.replacingOccurrences(of: NSHomeDirectory(), with: "~")
                completion(path)
            }
        }
    }

    private func selectFile(current: String, completion: @escaping (String) -> Void) {
        let panel = NSSavePanel()
        panel.allowedContentTypes = [.commaSeparatedText]
        panel.canCreateDirectories = true
        panel.nameFieldStringValue = "meetings.csv"

        let currentPath = NSString(string: current).expandingTildeInPath
        panel.directoryURL = URL(fileURLWithPath: currentPath).deletingLastPathComponent()

        if panel.runModal() == .OK {
            if let url = panel.url {
                let path = url.path.replacingOccurrences(of: NSHomeDirectory(), with: "~")
                completion(path)
            }
        }
    }
}

// MARK: - Advanced Settings

struct AdvancedSettingsView: View {
    @EnvironmentObject var preferences: PreferencesManager

    var body: some View {
        Form {
            Section(header: Text("Debugging").font(.headline)) {
                Toggle("Enable Debug Logging", isOn: $preferences.debugLogging)
                    .padding(.vertical, 4)

                if preferences.debugLogging {
                    Text("Debug logs will be written to Console.app")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }

            Section(header: Text("Fallback Options").font(.headline)) {
                Toggle("Enable Microphone Fallback", isOn: $preferences.enableMicFallback)
                    .padding(.vertical, 4)

                Text("If enabled, the app will use your microphone when screen capture is unavailable. This captures your voice only, not other participants.")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
        .formStyle(.grouped)
    }
}
