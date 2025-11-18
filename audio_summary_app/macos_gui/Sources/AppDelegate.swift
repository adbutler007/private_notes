// AppDelegate.swift
// Menu-bar app with NSStatusItem
// Per spec §4.1 FR1 - Status bar app with menu

import Cocoa
import SwiftUI
import ScreenCaptureKit
import UserNotifications

class AppDelegate: NSObject, NSApplicationDelegate {
    private var statusItem: NSStatusItem!
    private var menu: NSMenu!

    private let captureController = CaptureController()
    private let preferences = PreferencesManager.shared
    private let sessionManager = SessionManager.shared

    private var settingsWindow: NSWindow?
    private var wizardWindow: NSWindow?
    private var selectedApp: SCRunningApplication?
    
    private var engineProcess: Process?

    func applicationDidFinishLaunching(_ notification: Notification) {
        // Write to file to confirm this method is called
        try? "applicationDidFinishLaunching called at \(Date())\n".write(toFile: "/tmp/audio_summary_launch.txt", atomically: true, encoding: .utf8)

        print("=== Audio Summary starting ===")
        NSLog("Audio Summary starting...")
        
        // Start the backend engine
        startEngine()

        // Ensure app can present UI (even with LSUIElement)
        NSApp.setActivationPolicy(.accessory)
        print("Activation policy set to: accessory")

        // Request notification permission
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound]) { granted, error in
            if let error = error {
                NSLog("Notification permission error: \(error)")
            }
            NSLog("Notification permission granted: \(granted)")
        }

        // Create status bar item
        print("Setting up status bar...")
        NSLog("Setting up status bar...")
        setupStatusBar()
        print("Status bar setup complete. Icon: \(String(describing: statusItem.button?.image))")
        print("StatusItem exists: \(statusItem != nil), Button exists: \(statusItem.button != nil)")
        NSLog("Status bar setup complete. Icon: \(String(describing: statusItem.button?.image))")

        // Check if first run
        print("First run completed: \(preferences.firstRunCompleted)")
        NSLog("First run completed: \(preferences.firstRunCompleted)")
        if !preferences.firstRunCompleted {
            // Show first-run wizard
            print("Showing first-run wizard...")
            NSLog("Showing first-run wizard...")
            showFirstRunWizard()
            print("showFirstRunWizard() returned")
        } else {
            print("App ready - first run already completed")
            NSLog("App ready - first run already completed")
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
        print("App terminating, stopping engine...")
        engineProcess?.terminate()
    }

    // MARK: - Engine Management
    
    private func startEngine() {
        // Try to find uv in common locations
        let uvPaths = [
            "/opt/homebrew/bin/uv",  // Homebrew on Apple Silicon
            "/usr/local/bin/uv",     // Homebrew on Intel
            FileManager.default.homeDirectoryForCurrentUser.path + "/.local/bin/uv"  // User install
        ]
        
        guard let uvPath = uvPaths.first(where: { FileManager.default.fileExists(atPath: $0) }) else {
            print("[Engine] uv not found in common locations. Engine will not start automatically.")
            print("[Engine] User must start manually: cd ~/Projects/private_notes && uv run python -m audio_summary_app.engine.server")
            return
        }
        
        print("[Engine] Found uv at: \(uvPath)")
        
        // Find the project directory (assume it's in ~/Projects/private_notes)
        let projectPath = FileManager.default.homeDirectoryForCurrentUser.path + "/Projects/private_notes"
        
        guard FileManager.default.fileExists(atPath: projectPath + "/audio_summary_app") else {
            print("[Engine] Project not found at \(projectPath)")
            print("[Engine] Engine will not start automatically.")
            return
        }
        
        let process = Process()
        process.executableURL = URL(fileURLWithPath: uvPath)
        process.arguments = ["run", "python", "-m", "audio_summary_app.engine.server"]
        process.currentDirectoryURL = URL(fileURLWithPath: projectPath)
        
        // Redirect output to log files
        let logDir = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Logs/AudioSummary")
        try? FileManager.default.createDirectory(at: logDir, withIntermediateDirectories: true)
        
        let logFile = logDir.appendingPathComponent("engine.log")
        FileManager.default.createFile(atPath: logFile.path, contents: nil)
        
        if let fileHandle = FileHandle(forWritingAtPath: logFile.path) {
            process.standardOutput = fileHandle
            process.standardError = fileHandle
            print("[Engine] Logging to: \(logFile.path)")
        }
        
        do {
            try process.run()
            engineProcess = process
            print("[Engine] Started successfully (PID: \(process.processIdentifier))")
            
            // Give it a moment to start
            DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
                print("[Engine] Should be ready at http://127.0.0.1:8756")
            }
        } catch {
            print("[Engine] Failed to start: \(error)")
        }
    }

    // MARK: - Status Bar Setup

    private func setupStatusBar() {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)

        if let button = statusItem.button {
            // Use a microphone icon (system symbol)
            button.image = NSImage(systemSymbolName: "mic.fill", accessibilityDescription: "Audio Summary")
            button.image?.isTemplate = true
        }

        // Create menu
        menu = NSMenu()
        menu.delegate = self
        statusItem.menu = menu

        updateMenu()
    }

    // MARK: - Menu Updates

    private func updateMenu() {
        menu.removeAllItems()

        // Status indicator
        if case .recording = captureController.state {
            let recordingItem = NSMenuItem(title: "● Recording", action: nil, keyEquivalent: "")
            recordingItem.isEnabled = false
            menu.addItem(recordingItem)

            // Buffer status
            if !captureController.bufferStatus.isEmpty {
                let bufferItem = NSMenuItem(title: captureController.bufferStatus, action: nil, keyEquivalent: "")
                bufferItem.isEnabled = false
                menu.addItem(bufferItem)
            }

            menu.addItem(NSMenuItem.separator())

            // Stop Recording
            menu.addItem(NSMenuItem(title: "Stop Recording", action: #selector(stopRecording), keyEquivalent: "s"))

        } else if case .starting = captureController.state {
            let startingItem = NSMenuItem(title: "Starting...", action: nil, keyEquivalent: "")
            startingItem.isEnabled = false
            menu.addItem(startingItem)

        } else if case .stopping = captureController.state {
            let stoppingItem = NSMenuItem(title: "Stopping...", action: nil, keyEquivalent: "")
            stoppingItem.isEnabled = false
            menu.addItem(stoppingItem)

        } else if case .error(let message) = captureController.state {
            let errorItem = NSMenuItem(title: "Error: \(message)", action: nil, keyEquivalent: "")
            errorItem.isEnabled = false
            menu.addItem(errorItem)
            menu.addItem(NSMenuItem.separator())
            menu.addItem(NSMenuItem(title: "Start Recording", action: #selector(startRecording), keyEquivalent: "r"))

        } else {
            // Idle - Start Recording options
            menu.addItem(NSMenuItem(title: "Start Recording", action: #selector(startRecording), keyEquivalent: "r"))

            // Audio Input Device submenu (for BlackHole capture)
            let deviceMenu = NSMenu()
            let inputDevices = MicrophoneCaptureManager.getInputDevices()

            if inputDevices.isEmpty {
                let noDevicesItem = NSMenuItem(title: "No input devices found", action: nil, keyEquivalent: "")
                noDevicesItem.isEnabled = false
                deviceMenu.addItem(noDevicesItem)
            } else {
                for device in inputDevices {
                    let item = NSMenuItem(
                        title: device.name,
                        action: #selector(startRecordingFromDevice(_:)),
                        keyEquivalent: ""
                    )
                    item.representedObject = device
                    // Highlight BlackHole devices
                    if device.name.lowercased().contains("blackhole") {
                        item.title = "⭐ \(device.name)"
                    }
                    deviceMenu.addItem(item)
                }
            }

            let deviceItem = NSMenuItem(title: "Record from Device", action: nil, keyEquivalent: "")
            deviceItem.submenu = deviceMenu
            menu.addItem(deviceItem)
        }

        menu.addItem(NSMenuItem.separator())

        // Settings
        menu.addItem(NSMenuItem(title: "Settings...", action: #selector(showSettings), keyEquivalent: ","))

        // Recent Summaries
        let recentMenu = NSMenu()
        let recentSessions = sessionManager.getRecentSessions()

        if recentSessions.isEmpty {
            let emptyItem = NSMenuItem(title: "No recent summaries", action: nil, keyEquivalent: "")
            emptyItem.isEnabled = false
            recentMenu.addItem(emptyItem)
        } else {
            for session in recentSessions {
                let item = NSMenuItem(
                    title: session.displayName,
                    action: #selector(openSummary(_:)),
                    keyEquivalent: ""
                )
                item.representedObject = session
                recentMenu.addItem(item)
            }
        }

        let recentItem = NSMenuItem(title: "Recent Summaries", action: nil, keyEquivalent: "")
        recentItem.submenu = recentMenu
        menu.addItem(recentItem)

        menu.addItem(NSMenuItem.separator())

        // Quit
        menu.addItem(NSMenuItem(title: "Quit", action: #selector(quit), keyEquivalent: "q"))
    }

    // MARK: - Actions

    @objc private func startRecording() {
        Task {
            do {
                // Get shareable content
                let captureManager = ScreenCaptureManager()
                let content = try await captureManager.getShareableContent()

                // Find target apps
                let targetApps = captureManager.findTargetApps(in: content)

                guard !targetApps.isEmpty else {
                    await MainActor.run {
                        showAlert(
                            title: "No Apps Found",
                            message: "No Zoom or Teams apps are currently running. Please start Zoom or Teams and try again."
                        )
                    }
                    return
                }

                // If only one app, use it; otherwise show picker
                let appToCapture: SCRunningApplication
                if targetApps.count == 1 {
                    appToCapture = targetApps[0]
                } else {
                    // Show app picker
                    appToCapture = await selectApp(from: targetApps)
                }

                selectedApp = appToCapture

                // Start recording
                await captureController.startRecording(app: appToCapture)

            } catch {
                await MainActor.run {
                    showAlert(
                        title: "Failed to Start",
                        message: "Error: \(error.localizedDescription)\n\nMake sure Screen Recording permission is enabled in System Settings."
                    )
                }
            }
        }
    }

    @objc private func stopRecording() {
        Task {
            await captureController.stopRecording()
        }
    }

    @objc private func startRecordingFromDevice(_ sender: NSMenuItem) {
        guard let device = sender.representedObject as? AudioInputDevice else { return }

        Task {
            await captureController.startRecording(fromDevice: device)
        }
    }

    @objc private func showSettings() {
        if settingsWindow == nil {
            let settingsView = SettingsView()
                .environmentObject(preferences)

            let hostingController = NSHostingController(rootView: settingsView)
            let window = NSWindow(contentViewController: hostingController)
            window.title = "Audio Summary Settings"
            window.styleMask = [.titled, .closable, .resizable]
            window.setContentSize(NSSize(width: 600, height: 700))
            window.center()

            settingsWindow = window
        }

        settingsWindow?.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    @objc private func openSummary(_ sender: NSMenuItem) {
        guard let session = sender.representedObject as? SessionRecord else { return }
        sessionManager.openSummary(for: session)
    }

    @objc private func quit() {
        NSApplication.shared.terminate(nil)
    }

    // MARK: - App Selection

    private func selectApp(from apps: [SCRunningApplication]) async -> SCRunningApplication {
        // For now, return first app
        // TODO: Show SwiftUI picker dialog
        return apps[0]
    }

    // MARK: - First Run Wizard

    private func showFirstRunWizard() {
        print("showFirstRunWizard called")
        if wizardWindow == nil {
            print("Creating wizard window...")
            let wizardView = FirstRunWizard()
                .environmentObject(preferences)

            let hostingController = NSHostingController(rootView: wizardView)
            let window = NSWindow(contentViewController: hostingController)
            window.title = "Welcome to Audio Summary"
            window.styleMask = [.titled, .closable]
            window.setContentSize(NSSize(width: 600, height: 500))
            window.center()
            window.level = .floating  // Force window to top
            window.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]

            wizardWindow = window
            print("Wizard window created")
        }

        print("Making wizard window key and front...")
        wizardWindow?.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        print("Wizard window should be visible now")
    }

    // MARK: - Alerts

    private func showAlert(title: String, message: String) {
        let alert = NSAlert()
        alert.messageText = title
        alert.informativeText = message
        alert.alertStyle = .warning
        alert.addButton(withTitle: "OK")
        alert.runModal()
    }
}

// MARK: - NSMenuDelegate

extension AppDelegate: NSMenuDelegate {
    func menuWillOpen(_ menu: NSMenu) {
        updateMenu()
    }
}
