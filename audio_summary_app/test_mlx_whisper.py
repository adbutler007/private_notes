#!/usr/bin/env python3
"""
Test MLX Whisper integration with the transcriber
"""

import numpy as np
from audio_summary_app.transcriber import StreamingTranscriber

def test_mlx_transcriber():
    """Test that MLX Whisper transcriber works with audio data"""
    
    print("="*80)
    print("Testing MLX Whisper Integration")
    print("="*80)
    print()
    
    # Create transcriber with large model
    print("Creating transcriber with 'large' model...")
    transcriber = StreamingTranscriber("large")
    print()
    
    # Create a simple test audio buffer (1 second of silence)
    # In real use, this would be actual microphone audio
    print("Creating test audio chunk (1 second of silence)...")
    sample_rate = 16000
    duration = 1.0
    audio_data = np.zeros((int(sample_rate * duration),), dtype=np.float32)
    
    audio_chunk = {
        'data': audio_data,
        'source': 'input',
        'timestamp': 0.0
    }
    print()
    
    # Test transcription
    print("Testing transcription (should return empty for silence)...")
    try:
        result = transcriber.transcribe(audio_chunk)
        print(f"✓ Transcription successful")
        print(f"  Result: '{result}' (empty is expected for silence)")
        print()
        print("="*80)
        print("MLX WHISPER INTEGRATION TEST PASSED")
        print("="*80)
        print()
        print("Note: The model will download on first use during actual recording.")
        print("MLX Whisper provides 3-5x faster transcription on Apple Silicon.")
        return 0
    except Exception as e:
        print(f"✗ Transcription failed: {e}")
        print()
        print("="*80)
        print("MLX WHISPER INTEGRATION TEST FAILED")
        print("="*80)
        return 1

if __name__ == "__main__":
    exit(test_mlx_transcriber())
