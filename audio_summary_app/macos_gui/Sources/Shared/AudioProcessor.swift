// AudioProcessor.swift
// Audio conversion pipeline: CMSampleBuffer → float32 PCM → base64
// Per spec §4.2.2 - Audio Format Contract

import Foundation
import CoreMedia
import AVFoundation

enum AudioProcessorError: Error, LocalizedError {
    case invalidSampleBuffer
    case invalidAudioFormat
    case noAudioData
    case conversionFailed(String)

    var errorDescription: String? {
        switch self {
        case .invalidSampleBuffer:
            return "Invalid CMSampleBuffer"
        case .invalidAudioFormat:
            return "Unsupported audio format"
        case .noAudioData:
            return "No audio data in sample buffer"
        case .conversionFailed(let reason):
            return "Audio conversion failed: \(reason)"
        }
    }
}

class AudioProcessor {

    // MARK: - Main Conversion Pipeline

    /// Convert CMSampleBuffer to base64-encoded float32 mono PCM
    /// Per spec §4.2.2: float32, mono, range [-1.0, 1.0]
    static func convertToBase64PCM(_ sampleBuffer: CMSampleBuffer) throws -> (pcmB64: String, sampleRate: Int) {
        // Extract float32 samples
        let (samples, sampleRate, channelCount) = try extractFloat32Samples(sampleBuffer)

        // Convert to mono if stereo
        let monoSamples = channelCount > 1 ? stereoToMono(samples, channelCount: channelCount) : samples

        // Normalize to [-1.0, 1.0]
        let normalizedSamples = normalize(monoSamples)

        // Validate range
        try validateRange(normalizedSamples)

        // Encode to base64
        let pcmB64 = encodeToBase64(normalizedSamples)

        return (pcmB64, sampleRate)
    }

    // MARK: - Audio Extraction

    /// Extract float32 samples from CMSampleBuffer
    static func extractFloat32Samples(_ sampleBuffer: CMSampleBuffer) throws -> (samples: [Float], sampleRate: Int, channelCount: Int) {
        // Get audio buffer list
        guard let formatDescription = CMSampleBufferGetFormatDescription(sampleBuffer) else {
            throw AudioProcessorError.invalidSampleBuffer
        }

        guard let asbd = CMAudioFormatDescriptionGetStreamBasicDescription(formatDescription) else {
            throw AudioProcessorError.invalidAudioFormat
        }

        let sampleRate = Int(asbd.pointee.mSampleRate)
        let channelCount = Int(asbd.pointee.mChannelsPerFrame)
        let formatID = asbd.pointee.mFormatID
        let formatFlags = asbd.pointee.mFormatFlags

        // Ensure PCM format
        guard formatID == kAudioFormatLinearPCM else {
            throw AudioProcessorError.invalidAudioFormat
        }

        // Get audio buffer list
        var audioBufferList = AudioBufferList()
        var blockBuffer: CMBlockBuffer?

        let status = CMSampleBufferGetAudioBufferListWithRetainedBlockBuffer(
            sampleBuffer,
            bufferListSizeNeededOut: nil,
            bufferListOut: &audioBufferList,
            bufferListSize: MemoryLayout<AudioBufferList>.size,
            blockBufferAllocator: nil,
            blockBufferMemoryAllocator: nil,
            flags: 0,
            blockBufferOut: &blockBuffer
        )

        guard status == noErr else {
            throw AudioProcessorError.conversionFailed("Failed to get audio buffer list: \(status)")
        }

        // Extract samples based on format
        let audioBuffer = audioBufferList.mBuffers

        guard let dataPtr = audioBuffer.mData else {
            throw AudioProcessorError.noAudioData
        }

        let dataByteSize = Int(audioBuffer.mDataByteSize)

        // Check if float or integer format
        let isFloat = (formatFlags & kAudioFormatFlagIsFloat) != 0
        let bitDepth = Int(asbd.pointee.mBitsPerChannel)

        var samples: [Float]

        if isFloat {
            // Already float32
            if bitDepth == 32 {
                let floatPtr = dataPtr.assumingMemoryBound(to: Float.self)
                let frameCount = dataByteSize / MemoryLayout<Float>.size
                samples = Array(UnsafeBufferPointer(start: floatPtr, count: frameCount))
            } else {
                throw AudioProcessorError.invalidAudioFormat
            }
        } else {
            // Integer PCM - convert to float
            if bitDepth == 16 {
                // 16-bit int PCM
                let int16Ptr = dataPtr.assumingMemoryBound(to: Int16.self)
                let frameCount = dataByteSize / MemoryLayout<Int16>.size
                samples = (0..<frameCount).map { i in
                    Float(int16Ptr[i]) / Float(Int16.max)
                }
            } else if bitDepth == 32 {
                // 32-bit int PCM
                let int32Ptr = dataPtr.assumingMemoryBound(to: Int32.self)
                let frameCount = dataByteSize / MemoryLayout<Int32>.size
                samples = (0..<frameCount).map { i in
                    Float(int32Ptr[i]) / Float(Int32.max)
                }
            } else {
                throw AudioProcessorError.invalidAudioFormat
            }
        }

        return (samples, sampleRate, channelCount)
    }

    // MARK: - Audio Processing

    /// Convert stereo (or multi-channel) to mono by averaging channels
    static func stereoToMono(_ samples: [Float], channelCount: Int) -> [Float] {
        guard channelCount > 1 else { return samples }

        let frameCount = samples.count / channelCount
        var mono = [Float]()
        mono.reserveCapacity(frameCount)

        for frameIndex in 0..<frameCount {
            var sum: Float = 0.0
            for channel in 0..<channelCount {
                sum += samples[frameIndex * channelCount + channel]
            }
            mono.append(sum / Float(channelCount))
        }

        return mono
    }

    /// Normalize audio to [-1.0, 1.0] range
    static func normalize(_ samples: [Float]) -> [Float] {
        guard !samples.isEmpty else { return samples }

        let maxAbs = samples.map { abs($0) }.max() ?? 1.0

        // If already normalized, return as-is
        guard maxAbs > 1.0 else { return samples }

        // Normalize
        return samples.map { $0 / maxAbs }
    }

    /// Validate that all samples are in range [-1.0, 1.0]
    /// Per spec §4.2.2: audio range must be [-1.0, 1.0]
    static func validateRange(_ samples: [Float]) throws {
        guard !samples.isEmpty else { return }

        let tolerance: Float = 1e-6
        let minVal = samples.min() ?? 0.0
        let maxVal = samples.max() ?? 0.0

        if minVal < -1.0 - tolerance || maxVal > 1.0 + tolerance {
            throw AudioProcessorError.conversionFailed(
                "Audio range [\(minVal), \(maxVal)] exceeds allowed range [-1.0, 1.0]"
            )
        }
    }

    // MARK: - Base64 Encoding

    /// Encode float32 array to base64 string
    /// Per spec §4.2.2: pcm_b64 is base64-encoded float32 mono PCM
    static func encodeToBase64(_ samples: [Float]) -> String {
        let data = samples.withUnsafeBufferPointer { buffer in
            Data(buffer: buffer)
        }
        return data.base64EncodedString()
    }

    // MARK: - Utility Methods

    /// Get sample rate from CMSampleBuffer
    static func getSampleRate(_ sampleBuffer: CMSampleBuffer) -> Int? {
        guard let formatDescription = CMSampleBufferGetFormatDescription(sampleBuffer),
              let asbd = CMAudioFormatDescriptionGetStreamBasicDescription(formatDescription) else {
            return nil
        }
        return Int(asbd.pointee.mSampleRate)
    }

    /// Get channel count from CMSampleBuffer
    static func getChannelCount(_ sampleBuffer: CMSampleBuffer) -> Int? {
        guard let formatDescription = CMSampleBufferGetFormatDescription(sampleBuffer),
              let asbd = CMAudioFormatDescriptionGetStreamBasicDescription(formatDescription) else {
            return nil
        }
        return Int(asbd.pointee.mChannelsPerFrame)
    }
}
