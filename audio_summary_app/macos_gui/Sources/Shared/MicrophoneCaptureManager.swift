// MicrophoneCaptureManager.swift
// Microphone capture fallback when ScreenCaptureKit is unavailable
// Per spec §4.1 FR4 Advanced - Mic fallback option

import Foundation
import AVFoundation
import CoreMedia
import CoreAudio

enum MicrophoneCaptureError: Error, LocalizedError {
    case permissionDenied
    case noMicrophoneAvailable
    case deviceNotFound(String)
    case audioEngineFailure(String)

    var errorDescription: String? {
        switch self {
        case .permissionDenied:
            return "Microphone permission denied"
        case .noMicrophoneAvailable:
            return "No microphone device available"
        case .deviceNotFound(let name):
            return "Audio device not found: \(name)"
        case .audioEngineFailure(let reason):
            return "Audio engine failure: \(reason)"
        }
    }
}

/// Represents an audio input device
struct AudioInputDevice: Identifiable, Hashable {
    let id: AudioDeviceID
    let name: String
    let uid: String

    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }

    static func == (lhs: AudioInputDevice, rhs: AudioInputDevice) -> Bool {
        lhs.id == rhs.id
    }
}

class MicrophoneCaptureManager: NSObject {

    private var audioEngine: AVAudioEngine?
    private var inputNode: AVAudioInputNode?

    var onAudioCaptured: ((CMSampleBuffer, Int) -> Void)?

    // MARK: - Device Enumeration

    /// Get all available audio input devices
    static func getInputDevices() -> [AudioInputDevice] {
        var devices: [AudioInputDevice] = []

        var propertyAddress = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDevices,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )

        var dataSize: UInt32 = 0
        var status = AudioObjectGetPropertyDataSize(
            AudioObjectID(kAudioObjectSystemObject),
            &propertyAddress,
            0,
            nil,
            &dataSize
        )

        guard status == noErr else { return devices }

        let deviceCount = Int(dataSize) / MemoryLayout<AudioDeviceID>.size
        var deviceIDs = [AudioDeviceID](repeating: 0, count: deviceCount)

        status = AudioObjectGetPropertyData(
            AudioObjectID(kAudioObjectSystemObject),
            &propertyAddress,
            0,
            nil,
            &dataSize,
            &deviceIDs
        )

        guard status == noErr else { return devices }

        for deviceID in deviceIDs {
            // Check if device has input channels
            var inputChannelsAddress = AudioObjectPropertyAddress(
                mSelector: kAudioDevicePropertyStreamConfiguration,
                mScope: kAudioDevicePropertyScopeInput,
                mElement: kAudioObjectPropertyElementMain
            )

            var bufferListSize: UInt32 = 0
            status = AudioObjectGetPropertyDataSize(
                deviceID,
                &inputChannelsAddress,
                0,
                nil,
                &bufferListSize
            )

            if status == noErr && bufferListSize > 0 {
                // Allocate raw memory of the correct size
                let bufferListRawPtr = UnsafeMutableRawPointer.allocate(
                    byteCount: Int(bufferListSize),
                    alignment: MemoryLayout<AudioBufferList>.alignment
                )
                defer { bufferListRawPtr.deallocate() }
                
                // Bind to AudioBufferList for API call
                let bufferListPtr = bufferListRawPtr.bindMemory(to: AudioBufferList.self, capacity: 1)

                status = AudioObjectGetPropertyData(
                    deviceID,
                    &inputChannelsAddress,
                    0,
                    nil,
                    &bufferListSize,
                    bufferListPtr
                )

                if status == noErr {
                    var totalChannels: UInt32 = 0
                    
                    // Iterate over buffers safely using the AudioBufferList helper
                    let buffers = UnsafeMutableAudioBufferListPointer(bufferListPtr)
                    for buffer in buffers {
                        totalChannels += buffer.mNumberChannels
                    }

                    if totalChannels > 0 {
                        // Get device name
                        var nameAddress = AudioObjectPropertyAddress(
                            mSelector: kAudioDevicePropertyDeviceNameCFString,
                            mScope: kAudioObjectPropertyScopeGlobal,
                            mElement: kAudioObjectPropertyElementMain
                        )

                        var nameRef: Unmanaged<CFString>?
                        var nameSize = UInt32(MemoryLayout<Unmanaged<CFString>?>.size)

                        status = AudioObjectGetPropertyData(
                            deviceID,
                            &nameAddress,
                            0,
                            nil,
                            &nameSize,
                            &nameRef
                        )

                        let deviceName: String
                        if status == noErr, let retainedValue = nameRef?.takeRetainedValue() {
                            deviceName = retainedValue as String
                        } else {
                            deviceName = "Unknown Device"
                        }

                        // Get device UID
                        var uidAddress = AudioObjectPropertyAddress(
                            mSelector: kAudioDevicePropertyDeviceUID,
                            mScope: kAudioObjectPropertyScopeGlobal,
                            mElement: kAudioObjectPropertyElementMain
                        )

                        var uidRef: Unmanaged<CFString>?
                        var uidSize = UInt32(MemoryLayout<Unmanaged<CFString>?>.size)

                        status = AudioObjectGetPropertyData(
                            deviceID,
                            &uidAddress,
                            0,
                            nil,
                            &uidSize,
                            &uidRef
                        )

                        let deviceUID: String
                        if status == noErr, let retainedValue = uidRef?.takeRetainedValue() {
                            deviceUID = retainedValue as String
                        } else {
                            deviceUID = ""
                        }

                        devices.append(AudioInputDevice(
                            id: deviceID,
                            name: deviceName,
                            uid: deviceUID
                        ))
                    }
                }
            }
        }

        return devices
    }

    /// Find BlackHole device if available
    static func findBlackHoleDevice() -> AudioInputDevice? {
        return getInputDevices().first { device in
            device.name.lowercased().contains("blackhole")
        }
    }

    /// Set the system's default input device
    private func setDefaultInputDevice(_ deviceID: AudioDeviceID) -> Bool {
        var mutableDeviceID = deviceID
        var propertyAddress = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDefaultInputDevice,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )

        let status = AudioObjectSetPropertyData(
            AudioObjectID(kAudioObjectSystemObject),
            &propertyAddress,
            0,
            nil,
            UInt32(MemoryLayout<AudioDeviceID>.size),
            &mutableDeviceID
        )

        return status == noErr
    }

    // MARK: - Microphone Access

    /// Check if microphone permission is granted
    func checkMicrophonePermission() async -> Bool {
        #if os(macOS)
        if #available(macOS 14.0, *) {
            return await AVCaptureDevice.requestAccess(for: .audio)
        } else {
            // For macOS 13.x, use legacy API
            let status = AVCaptureDevice.authorizationStatus(for: .audio)
            if status == .authorized {
                return true
            } else if status == .notDetermined {
                return await AVCaptureDevice.requestAccess(for: .audio)
            } else {
                return false
            }
        }
        #else
        return false
        #endif
    }

    // MARK: - Capture Control

    /// Start capturing from the default microphone
    func startCapture() async throws {
        try await startCapture(fromDevice: nil)
    }

    /// Start capturing from a specific audio input device
    /// - Parameter device: The device to capture from, or nil for system default
    func startCapture(fromDevice device: AudioInputDevice?) async throws {
        // Verify permission
        let hasPermission = await checkMicrophonePermission()
        guard hasPermission else {
            throw MicrophoneCaptureError.permissionDenied
        }

        // If a specific device is requested, set it as default
        // (AVAudioEngine uses the system default input device)
        var previousDefaultDevice: AudioDeviceID?
        if let device = device {
            // Save current default to restore later if needed
            previousDefaultDevice = getCurrentDefaultInputDevice()

            if !setDefaultInputDevice(device.id) {
                throw MicrophoneCaptureError.deviceNotFound(device.name)
            }
            print("[MicCapture] Set input device to: \(device.name)")
        }

        // Initialize audio engine
        let engine = AVAudioEngine()
        audioEngine = engine

        let input = engine.inputNode
        inputNode = input

        // Get input format
        let inputFormat = input.inputFormat(forBus: 0)

        guard inputFormat.sampleRate > 0 else {
            // Restore previous default if we changed it
            if let prevDevice = previousDefaultDevice {
                _ = setDefaultInputDevice(prevDevice)
            }
            throw MicrophoneCaptureError.noMicrophoneAvailable
        }

        // Set up desired format: 48kHz, mono, float32
        // Note: We'll capture at native rate and convert
        let sampleRate = inputFormat.sampleRate
        let channelCount = inputFormat.channelCount

        print("[MicCapture] Input format: \(sampleRate) Hz, \(channelCount) channels")

        // Install tap on input node
        input.installTap(onBus: 0, bufferSize: 4096, format: inputFormat) { [weak self] buffer, time in
            guard let self = self else { return }

            // Convert AVAudioPCMBuffer to CMSampleBuffer
            if let sampleBuffer = self.convertToCMSampleBuffer(buffer) {
                self.onAudioCaptured?(sampleBuffer, Int(sampleRate))
            }
        }

        // Start engine
        do {
            try engine.start()
            print("[MicCapture] ✅ Capture started from \(device?.name ?? "default device")")
        } catch {
            // Restore previous default if we changed it
            if let prevDevice = previousDefaultDevice {
                _ = setDefaultInputDevice(prevDevice)
            }
            throw MicrophoneCaptureError.audioEngineFailure(error.localizedDescription)
        }
    }

    /// Get the current default input device ID
    private func getCurrentDefaultInputDevice() -> AudioDeviceID? {
        var propertyAddress = AudioObjectPropertyAddress(
            mSelector: kAudioHardwarePropertyDefaultInputDevice,
            mScope: kAudioObjectPropertyScopeGlobal,
            mElement: kAudioObjectPropertyElementMain
        )

        var deviceID: AudioDeviceID = 0
        var dataSize = UInt32(MemoryLayout<AudioDeviceID>.size)

        let status = AudioObjectGetPropertyData(
            AudioObjectID(kAudioObjectSystemObject),
            &propertyAddress,
            0,
            nil,
            &dataSize,
            &deviceID
        )

        return status == noErr ? deviceID : nil
    }

    /// Stop capturing
    func stopCapture() async {
        inputNode?.removeTap(onBus: 0)
        audioEngine?.stop()
        audioEngine = nil
        inputNode = nil
        print("Microphone capture stopped")
    }

    // MARK: - Audio Conversion

    /// Convert AVAudioPCMBuffer to CMSampleBuffer
    private func convertToCMSampleBuffer(_ buffer: AVAudioPCMBuffer) -> CMSampleBuffer? {
        guard let channelData = buffer.floatChannelData else {
            return nil
        }

        let frameCount = Int(buffer.frameLength)
        let channelCount = Int(buffer.format.channelCount)
        let sampleRate = buffer.format.sampleRate

        // Create interleaved float array
        var samples = [Float](repeating: 0, count: frameCount * channelCount)

        for frame in 0..<frameCount {
            for channel in 0..<channelCount {
                samples[frame * channelCount + channel] = channelData[channel][frame]
            }
        }

        // Create CMSampleBuffer from float data
        var formatDescription: CMAudioFormatDescription?

        var asbd = AudioStreamBasicDescription(
            mSampleRate: sampleRate,
            mFormatID: kAudioFormatLinearPCM,
            mFormatFlags: kAudioFormatFlagIsFloat | kAudioFormatFlagIsPacked,
            mBytesPerPacket: UInt32(MemoryLayout<Float>.size * channelCount),
            mFramesPerPacket: 1,
            mBytesPerFrame: UInt32(MemoryLayout<Float>.size * channelCount),
            mChannelsPerFrame: UInt32(channelCount),
            mBitsPerChannel: 32,
            mReserved: 0
        )

        let status = CMAudioFormatDescriptionCreate(
            allocator: kCFAllocatorDefault,
            asbd: &asbd,
            layoutSize: 0,
            layout: nil,
            magicCookieSize: 0,
            magicCookie: nil,
            extensions: nil,
            formatDescriptionOut: &formatDescription
        )

        guard status == noErr, let formatDesc = formatDescription else {
            print("Failed to create format description: \(status)")
            return nil
        }

        // Create block buffer
        var blockBuffer: CMBlockBuffer?
        let dataSize = samples.count * MemoryLayout<Float>.size

        let blockStatus = samples.withUnsafeBytes { bytes in
            CMBlockBufferCreateWithMemoryBlock(
                allocator: kCFAllocatorDefault,
                memoryBlock: nil,
                blockLength: dataSize,
                blockAllocator: kCFAllocatorDefault,
                customBlockSource: nil,
                offsetToData: 0,
                dataLength: dataSize,
                flags: 0,
                blockBufferOut: &blockBuffer
            )
        }

        guard blockStatus == noErr, let block = blockBuffer else {
            print("Failed to create block buffer: \(blockStatus)")
            return nil
        }

        // Copy data to block buffer
        _ = samples.withUnsafeBytes { bytes in
            CMBlockBufferReplaceDataBytes(
                with: bytes.baseAddress!,
                blockBuffer: block,
                offsetIntoDestination: 0,
                dataLength: dataSize
            )
        }

        // Create sample buffer
        var sampleBuffer: CMSampleBuffer?

        let sampleStatus = CMAudioSampleBufferCreateWithPacketDescriptions(
            allocator: kCFAllocatorDefault,
            dataBuffer: block,
            dataReady: true,
            makeDataReadyCallback: nil,
            refcon: nil,
            formatDescription: formatDesc,
            sampleCount: frameCount,
            presentationTimeStamp: CMTime(value: 0, timescale: Int32(sampleRate)),
            packetDescriptions: nil,
            sampleBufferOut: &sampleBuffer
        )

        guard sampleStatus == noErr else {
            print("Failed to create sample buffer: \(sampleStatus)")
            return nil
        }

        return sampleBuffer
    }
}
