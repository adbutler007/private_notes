"""
CLI Test Client for Audio Summary Engine

Tests the engine HTTP API by:
1. Reading an audio file (WAV)
2. Converting to float32 mono PCM
3. Posting chunks to /audio_chunk
4. Stopping session and retrieving summary

Usage:
    audio-summary-test-client --audio test.wav --backend parakeet
    audio-summary-test-client --audio call.wav --backend whisper --chunk-size 1.0
"""

import argparse
import base64
import struct
import sys
import time
import uuid
from pathlib import Path
from typing import Optional

import httpx
import numpy as np

from ..config import Config
from ..engine.audio_utils import encode_pcm_to_base64


def load_wav_file(audio_path: Path) -> tuple[np.ndarray, int]:
    """
    Load WAV file and convert to float32 mono PCM

    Args:
        audio_path: Path to WAV file

    Returns:
        Tuple of (audio_data, sample_rate)
    """
    try:
        import wave
    except ImportError:
        print("ERROR: wave module not available", file=sys.stderr)
        sys.exit(1)

    try:
        with wave.open(str(audio_path), 'rb') as wav_file:
            # Get WAV parameters
            n_channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            n_frames = wav_file.getnframes()

            print(f"Loading {audio_path}")
            print(f"  Channels: {n_channels}")
            print(f"  Sample width: {sample_width} bytes")
            print(f"  Sample rate: {sample_rate} Hz")
            print(f"  Frames: {n_frames}")
            print(f"  Duration: {n_frames / sample_rate:.2f} seconds")

            # Read frames
            frames = wav_file.readframes(n_frames)

            # Convert to numpy array based on sample width
            if sample_width == 1:  # 8-bit
                audio_data = np.frombuffer(frames, dtype=np.uint8)
                audio_data = (audio_data.astype(np.float32) - 128) / 128.0
            elif sample_width == 2:  # 16-bit
                audio_data = np.frombuffer(frames, dtype=np.int16)
                audio_data = audio_data.astype(np.float32) / 32768.0
            elif sample_width == 3:  # 24-bit
                # 24-bit requires special handling
                print("WARNING: 24-bit audio requires conversion", file=sys.stderr)
                audio_data = np.frombuffer(frames, dtype=np.uint8)
                audio_data = audio_data.reshape(-1, 3)
                # Convert to int32 and normalize
                audio_data = np.pad(audio_data, ((0, 0), (0, 1)), mode='constant')
                audio_data = audio_data.view(np.int32)
                audio_data = audio_data.astype(np.float32) / (2**23)
            elif sample_width == 4:  # 32-bit
                audio_data = np.frombuffer(frames, dtype=np.int32)
                audio_data = audio_data.astype(np.float32) / (2**31)
            else:
                print(f"ERROR: Unsupported sample width: {sample_width}", file=sys.stderr)
                sys.exit(1)

            # Convert to mono if stereo
            if n_channels == 2:
                print("  Converting stereo to mono...")
                audio_data = audio_data.reshape(-1, 2).mean(axis=1)
            elif n_channels > 2:
                print(f"  Converting {n_channels} channels to mono...")
                audio_data = audio_data.reshape(-1, n_channels).mean(axis=1)

            # Ensure float32 and in range [-1.0, 1.0]
            audio_data = audio_data.astype(np.float32)
            max_val = np.abs(audio_data).max()
            if max_val > 1.0:
                print(f"  Normalizing audio (peak: {max_val:.2f})...")
                audio_data = audio_data / max_val

            print(f"  Loaded: {len(audio_data)} samples, range: [{audio_data.min():.3f}, {audio_data.max():.3f}]")

            return audio_data, sample_rate

    except Exception as e:
        print(f"ERROR: Failed to load WAV file: {e}", file=sys.stderr)
        sys.exit(1)


def chunk_audio(audio_data: np.ndarray, sample_rate: int, chunk_duration: float):
    """
    Split audio into chunks of specified duration

    Args:
        audio_data: Audio samples
        sample_rate: Sample rate
        chunk_duration: Duration of each chunk in seconds

    Yields:
        Audio chunks as numpy arrays
    """
    chunk_size = int(chunk_duration * sample_rate)
    num_chunks = (len(audio_data) + chunk_size - 1) // chunk_size

    for i in range(num_chunks):
        start = i * chunk_size
        end = min((i + 1) * chunk_size, len(audio_data))
        yield audio_data[start:end]


def test_engine_api(
    audio_path: Path,
    backend: str,
    chunk_duration: float,
    engine_url: str,
    auth_token: Optional[str]
):
    """
    Test engine API with audio file

    Args:
        audio_path: Path to audio file
        backend: "whisper" or "parakeet"
        chunk_duration: Duration of each audio chunk in seconds
        engine_url: Base URL of engine (e.g., "http://127.0.0.1:8756")
        auth_token: Optional auth token for X-Engine-Token header
    """
    # Load audio file
    audio_data, sample_rate = load_wav_file(audio_path)

    # Create HTTP client
    headers = {}
    if auth_token:
        headers['X-Engine-Token'] = auth_token

    client = httpx.Client(base_url=engine_url, headers=headers, timeout=30.0)

    # 1. Test /health
    print("\n=== Testing /health ===")
    try:
        response = client.get("/health")
        response.raise_for_status()
        health_data = response.json()
        print(f"Engine version: {health_data['engine_version']}")
        print(f"API version: {health_data['api_version']}")
        print(f"STT backends: {health_data['stt_backends']}")
        print(f"LLM models: {health_data['llm_models']}")
    except Exception as e:
        print(f"ERROR: /health failed: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Start session
    print("\n=== Starting session ===")
    session_id = str(uuid.uuid4())
    print(f"Session ID: {session_id}")

    # Load config for prompts
    config = Config()

    start_request = {
        "session_id": session_id,
        "model": backend,
        "sample_rate": sample_rate,
        "user_settings": {
            "chunk_summary_prompt": config.chunk_summary_prompt,
            "final_summary_prompt": config.final_summary_prompt,
            "data_extraction_prompt": config.data_extraction_prompt,
            "llm_model_name": config.llm_model_name,
            "output_dir": config.output_dir,
            "csv_export_path": config.csv_export_path,
            "append_csv": True
        }
    }

    try:
        response = client.post("/start_session", json=start_request)
        response.raise_for_status()
        print("Session started successfully")
    except Exception as e:
        print(f"ERROR: /start_session failed: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)

    # 3. Send audio chunks
    print(f"\n=== Sending audio chunks (chunk duration: {chunk_duration}s) ===")
    chunk_count = 0
    total_duration = len(audio_data) / sample_rate

    for chunk in chunk_audio(audio_data, sample_rate, chunk_duration):
        chunk_count += 1
        timestamp = time.time()

        # Encode chunk to base64
        pcm_b64 = encode_pcm_to_base64(chunk)

        chunk_request = {
            "session_id": session_id,
            "timestamp": timestamp,
            "pcm_b64": pcm_b64,
            "sample_rate": sample_rate
        }

        try:
            response = client.post("/audio_chunk", json=chunk_request)
            response.raise_for_status()
            chunk_response = response.json()

            # Show progress
            progress = (chunk_count * chunk_duration) / total_duration * 100
            progress = min(progress, 100)
            print(f"Chunk {chunk_count}: {chunk_response['buffered_seconds']:.2f}s buffered, "
                  f"{chunk_response['queue_depth']} segments queued (progress: {progress:.0f}%)")

        except Exception as e:
            print(f"ERROR: /audio_chunk failed: {e}", file=sys.stderr)
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}", file=sys.stderr)
            sys.exit(1)

    print(f"Sent {chunk_count} chunks ({total_duration:.2f}s total)")

    # 4. Stop session
    print("\n=== Stopping session ===")
    stop_request = {
        "session_id": session_id
    }

    try:
        response = client.post("/stop_session", json=stop_request)
        response.raise_for_status()
        stop_response = response.json()

        print("Session stopped successfully")
        print(f"  Status: {stop_response['session_status']}")
        print(f"  Summary: {stop_response['summary_path']}")
        print(f"  Data: {stop_response['data_path']}")
        if stop_response['csv_path']:
            print(f"  CSV: {stop_response['csv_path']}")

        # Read and display summary
        if stop_response['summary_path']:
            summary_path = Path(stop_response['summary_path'])
            if summary_path.exists():
                print("\n=== Generated Summary ===")
                print(summary_path.read_text())

    except Exception as e:
        print(f"ERROR: /stop_session failed: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)

    client.close()
    print("\n=== Test completed successfully ===")


def main():
    """Main entry point for audio-summary-test-client command"""
    parser = argparse.ArgumentParser(
        description="Test Audio Summary Engine API with audio file"
    )
    parser.add_argument(
        "--audio",
        type=Path,
        required=True,
        help="Path to audio file (WAV format)"
    )
    parser.add_argument(
        "--backend",
        choices=["whisper", "parakeet"],
        default="parakeet",
        help="STT backend to use (default: parakeet)"
    )
    parser.add_argument(
        "--chunk-size",
        type=float,
        default=2.0,
        help="Duration of each audio chunk in seconds (default: 2.0)"
    )
    parser.add_argument(
        "--engine-url",
        default="http://127.0.0.1:8756",
        help="Base URL of engine API (default: http://127.0.0.1:8756)"
    )
    parser.add_argument(
        "--auth-token",
        help="Optional engine auth token (X-Engine-Token header)"
    )

    args = parser.parse_args()

    # Validate audio file exists
    if not args.audio.exists():
        print(f"ERROR: Audio file not found: {args.audio}", file=sys.stderr)
        sys.exit(1)

    # Run test
    test_engine_api(
        audio_path=args.audio,
        backend=args.backend,
        chunk_duration=args.chunk_size,
        engine_url=args.engine_url,
        auth_token=args.auth_token
    )


if __name__ == "__main__":
    main()
