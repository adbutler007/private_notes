#!/usr/bin/env python3
"""
Test Parakeet MLX with a real audio file
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from audio_summary_app.config import Config
from parakeet_mlx import from_pretrained


def test_real_audio_file():
    """Test transcription of a real audio file"""
    audio_path = "/Users/adambutler/Projects/private_notes/first_meeting.mp3"

    print("="*60)
    print("PARAKEET MLX - REAL AUDIO FILE TEST")
    print("="*60)
    print(f"Audio file: {audio_path}")
    print()

    # Initialize Parakeet model
    config = Config()
    print(f"Loading model: {config.parakeet_model_path}")
    model = from_pretrained(config.parakeet_model_path)
    print("Model loaded successfully!")
    print()

    # Transcribe
    print("Transcribing... (this may take a moment)")
    print()

    result = model.transcribe(audio_path)

    print("="*60)
    print("TRANSCRIPTION RESULT")
    print("="*60)
    print(result.text)
    print()
    print("="*60)
    print(f"Total sentences: {len(result.sentences)}")
    print("="*60)

    # Show first few sentences with timestamps
    if result.sentences:
        print("\nFirst few sentences with timestamps:")
        for i, sentence in enumerate(result.sentences[:5]):
            print(f"{i+1}. [{sentence.start:.2f}s - {sentence.end:.2f}s] {sentence.text}")

    print("\n✅ Transcription completed successfully!")


if __name__ == "__main__":
    test_real_audio_file()
