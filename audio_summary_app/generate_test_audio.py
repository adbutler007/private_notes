"""
Generate a simple test audio file for engine testing

Creates a 10-second WAV file with:
- 16kHz sample rate
- 16-bit PCM
- Mono channel
- Simple sine wave tone (440 Hz - A4 note)

This simulates speech audio for testing the engine pipeline.
"""

import wave
import struct
import math

def generate_test_wav(output_path: str, duration: float = 10.0, sample_rate: int = 16000):
    """
    Generate test WAV file

    Args:
        output_path: Path to output WAV file
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
    """
    # Parameters
    frequency = 440.0  # A4 note
    amplitude = 0.3  # 30% amplitude (stays in range [-1, 1])

    # Generate samples
    num_samples = int(duration * sample_rate)
    samples = []

    for i in range(num_samples):
        # Generate sine wave
        t = i / sample_rate
        value = amplitude * math.sin(2 * math.pi * frequency * t)

        # Convert to 16-bit PCM
        pcm_value = int(value * 32767)
        samples.append(pcm_value)

    # Write WAV file
    with wave.open(output_path, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)

        # Pack samples as 16-bit signed integers
        packed_samples = struct.pack('<' + 'h' * len(samples), *samples)
        wav_file.writeframes(packed_samples)

    print(f"Generated test audio: {output_path}")
    print(f"  Duration: {duration}s")
    print(f"  Sample rate: {sample_rate} Hz")
    print(f"  Samples: {num_samples}")
    print(f"  Format: 16-bit PCM mono")


if __name__ == "__main__":
    generate_test_wav("test_audio.wav", duration=10.0, sample_rate=16000)
