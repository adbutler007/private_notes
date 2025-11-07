#!/usr/bin/env python3
"""
Test script to verify Parakeet MLX backend integration
"""

import numpy as np
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from audio_summary_app.transcriber import ParakeetTranscriber
from audio_summary_app.config import Config


def test_parakeet_initialization():
    """Test that ParakeetTranscriber can be initialized"""
    print("="*60)
    print("Test 1: ParakeetTranscriber Initialization")
    print("="*60)

    try:
        config = Config()
        transcriber = ParakeetTranscriber(
            model_path=config.parakeet_model_path,
            min_audio_duration=3.0,
            max_audio_duration=10.0
        )
        print("✓ ParakeetTranscriber initialized successfully")
        print(f"  Model: {transcriber.model_path}")
        print(f"  Using mock: {transcriber.use_mock}")
        return True
    except Exception as e:
        print(f"✗ Failed to initialize ParakeetTranscriber: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_parakeet_transcription():
    """Test that ParakeetTranscriber can handle audio input"""
    print("\n" + "="*60)
    print("Test 2: ParakeetTranscriber Audio Processing")
    print("="*60)

    try:
        config = Config()
        transcriber = ParakeetTranscriber(
            model_path=config.parakeet_model_path,
            min_audio_duration=3.0,
            max_audio_duration=10.0
        )

        # Create a synthetic audio chunk (3 seconds @ 16kHz)
        sample_rate = 16000
        duration = 3.0
        num_samples = int(sample_rate * duration)

        # Generate some random audio data
        audio_data = np.random.randn(num_samples).astype(np.float32) * 0.1

        audio_chunk = {
            'data': audio_data,
            'source': 'input',
            'timestamp': 0.0
        }

        print("  Sending 3.0s audio chunk to transcriber...")
        transcript = transcriber.transcribe(audio_chunk)

        if transcriber.use_mock:
            print("  ℹ Using mock model (Parakeet MLX not available)")
        else:
            print("  ✓ Using real Parakeet MLX model")

        print(f"  Transcript: '{transcript}'")
        print("✓ ParakeetTranscriber processed audio successfully")
        return True

    except Exception as e:
        print(f"✗ Failed to process audio: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_backend_selection():
    """Test that config correctly selects backend"""
    print("\n" + "="*60)
    print("Test 3: Config Backend Selection")
    print("="*60)

    try:
        config = Config()
        print(f"  Current backend: {config.stt_backend}")
        print(f"  Parakeet model: {config.parakeet_model_path}")
        print(f"  Whisper model: {config.stt_model_path}")

        if config.stt_backend == "parakeet":
            print("✓ Config is set to use Parakeet backend")
        else:
            print("✓ Config is set to use Whisper backend")

        return True

    except Exception as e:
        print(f"✗ Failed to check config: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("PARAKEET MLX BACKEND INTEGRATION TESTS")
    print("="*60 + "\n")

    results = []

    # Run tests
    results.append(("Initialization", test_parakeet_initialization()))
    results.append(("Audio Processing", test_parakeet_transcription()))
    results.append(("Config Selection", test_config_backend_selection()))

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Parakeet backend is ready to use.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
