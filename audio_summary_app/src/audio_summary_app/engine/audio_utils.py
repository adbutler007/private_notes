"""
Audio Utilities for Engine

Handles audio format conversions and validations per spec §4.2.2:
- Base64 encoding/decoding
- PCM format validation (float32 mono)
- Sample rate validation
- Range validation ([-1.0, 1.0])
"""

import base64
import struct
from typing import Tuple

import numpy as np


class AudioFormatError(Exception):
    """Raised when audio format is invalid"""

    pass


def decode_pcm_from_base64(pcm_b64: str, sample_rate: int) -> Tuple[np.ndarray, float]:
    """
    Decode base64-encoded float32 mono PCM to numpy array

    Per spec §4.2.2:
    - pcm_format: "f32_mono" (float32, mono)
    - sample_rate: provided per chunk
    - range: [-1.0, 1.0]

    Args:
        pcm_b64: Base64-encoded PCM data (float32 mono)
        sample_rate: Sample rate of the audio (for duration calculation)

    Returns:
        Tuple of (audio_array, duration_seconds)

    Raises:
        AudioFormatError: If audio format is invalid
    """
    try:
        # Decode base64
        pcm_bytes = base64.b64decode(pcm_b64)
    except Exception as e:
        raise AudioFormatError(f"Failed to decode base64: {e}")

    try:
        # Convert bytes to float32 array
        # Each float32 is 4 bytes
        num_samples = len(pcm_bytes) // 4

        if len(pcm_bytes) % 4 != 0:
            raise AudioFormatError(
                f"PCM data length ({len(pcm_bytes)} bytes) is not divisible by 4 (float32 size)"
            )

        # Unpack as little-endian float32
        audio_data = struct.unpack(f'<{num_samples}f', pcm_bytes)
        audio_array = np.array(audio_data, dtype=np.float32)

    except struct.error as e:
        raise AudioFormatError(f"Failed to unpack PCM data: {e}")
    except Exception as e:
        raise AudioFormatError(f"Failed to convert PCM to numpy array: {e}")

    # Validate range
    validate_audio_range(audio_array)

    # Calculate duration from capture sample rate (NOT model rate)
    # Per spec §4.2.2: derive durations from capture sample_rate
    duration = len(audio_array) / float(sample_rate)

    return audio_array, duration


def encode_pcm_to_base64(audio_array: np.ndarray) -> str:
    """
    Encode numpy float32 array to base64 PCM

    Args:
        audio_array: Numpy array of float32 audio samples

    Returns:
        Base64-encoded PCM string

    Raises:
        AudioFormatError: If audio format is invalid
    """
    if audio_array.dtype != np.float32:
        raise AudioFormatError(
            f"Audio array must be float32, got {audio_array.dtype}"
        )

    if audio_array.ndim != 1:
        raise AudioFormatError(
            f"Audio array must be 1D (mono), got {audio_array.ndim}D"
        )

    # Validate range
    validate_audio_range(audio_array)

    # Pack as little-endian float32
    pcm_bytes = struct.pack(f'<{len(audio_array)}f', *audio_array)

    # Encode to base64
    pcm_b64 = base64.b64encode(pcm_bytes).decode('utf-8')

    return pcm_b64


def validate_audio_range(audio_array: np.ndarray) -> None:
    """
    Validate that audio is in range [-1.0, 1.0]

    Per spec §4.2.2: audio range must be [-1.0, 1.0]

    Args:
        audio_array: Numpy array of audio samples

    Raises:
        AudioFormatError: If audio is out of range
    """
    if len(audio_array) == 0:
        return  # Empty audio is valid

    min_val = audio_array.min()
    max_val = audio_array.max()

    # Allow small tolerance for floating point errors
    tolerance = 1e-6

    if min_val < -1.0 - tolerance or max_val > 1.0 + tolerance:
        raise AudioFormatError(
            f"Audio range [{min_val:.4f}, {max_val:.4f}] exceeds allowed range [-1.0, 1.0]"
        )


def validate_sample_rate(sample_rate: int) -> None:
    """
    Validate that sample rate is reasonable

    Per spec §4.2.2: sample rate should be 8k-96k

    Args:
        sample_rate: Sample rate in Hz

    Raises:
        AudioFormatError: If sample rate is invalid
    """
    if not isinstance(sample_rate, int):
        raise AudioFormatError(
            f"Sample rate must be an integer, got {type(sample_rate)}"
        )

    if sample_rate < 8000 or sample_rate > 96000:
        raise AudioFormatError(
            f"Sample rate {sample_rate} Hz is outside valid range [8000, 96000]"
        )

    if sample_rate <= 0:
        raise AudioFormatError(f"Sample rate must be positive, got {sample_rate}")
