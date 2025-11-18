// swift-tools-version: 5.9
// Audio Summary GUI - Phase 3
// Menu-bar macOS app with SwiftUI

import PackageDescription

let package = Package(
    name: "AudioSummaryGUI",
    platforms: [
        .macOS(.v13)  // Required for ScreenCaptureKit
    ],
    products: [
        .executable(
            name: "AudioSummaryGUI",
            targets: ["AudioSummaryGUI"]
        )
    ],
    dependencies: [],
    targets: [
        .executableTarget(
            name: "AudioSummaryGUI",
            dependencies: [],
            path: "Sources"
        )
    ]
)
