// swift-tools-version: 5.9
// Audio Capture Prototype - Phase 2
// Swift Package for console app prototype using ScreenCaptureKit

import PackageDescription

let package = Package(
    name: "AudioCapturePrototype",
    platforms: [
        .macOS(.v13)  // Required for ScreenCaptureKit
    ],
    products: [
        .executable(
            name: "AudioCapturePrototype",
            targets: ["AudioCapturePrototype"]
        )
    ],
    dependencies: [],
    targets: [
        .executableTarget(
            name: "AudioCapturePrototype",
            dependencies: [],
            path: "Sources"
        )
    ]
)
