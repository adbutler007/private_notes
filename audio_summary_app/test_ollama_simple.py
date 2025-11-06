#!/usr/bin/env python3
"""
Simple Ollama Model Test
Just test the LLM with a 500-word sample to verify it's working correctly
"""

from pathlib import Path
from src.audio_summary_app.summarizer import MapReduceSummarizer
from src.audio_summary_app.config import Config


def load_transcript(transcript_path: str) -> str:
    """Load transcript with encoding detection"""
    transcript_file = Path(transcript_path)
    if not transcript_file.exists():
        raise FileNotFoundError(f"Transcript not found: {transcript_path}")

    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    for encoding in encodings:
        try:
            with open(transcript_file, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue

    raise UnicodeDecodeError(f"Could not decode file")


def main():
    print("=" * 80)
    print("SIMPLE OLLAMA MODEL TEST")
    print("=" * 80)
    print()

    # Load transcript
    transcript_path = "/Users/adambutler/Projects/private_notes/transcript.txt"
    print(f"Loading transcript: {transcript_path}")

    try:
        full_transcript = load_transcript(transcript_path)
        print(f"✓ Loaded {len(full_transcript):,} characters")
        print()
    except Exception as e:
        print(f"✗ Error: {e}")
        return 1

    # Extract first 500 words
    words = full_transcript.split()
    sample_text = ' '.join(words[:500])

    print(f"Sample text:")
    print(f"  Words: {len(sample_text.split())}")
    print(f"  Characters: {len(sample_text)}")
    print()
    print("First 200 characters:")
    print(sample_text[:200] + "...")
    print()
    print("=" * 80)
    print()

    # Initialize summarizer
    print("Initializing summarizer with Ollama...")
    config = Config()

    try:
        summarizer = MapReduceSummarizer(
            model_name=config.llm_model_name,
            summary_interval=config.summary_interval
        )
        print(f"✓ Summarizer initialized")
        print(f"  Model: {config.llm_model_name}")
        print(f"  LLM Type: {type(summarizer.llm).__name__}")
        print()
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")
        return 1

    # Generate summary
    print("=" * 80)
    print("GENERATING SUMMARY")
    print("=" * 80)
    print()

    try:
        print("Sending to Ollama... (this may take 10-30 seconds)")
        summary = summarizer.summarize_chunk(sample_text)

        print()
        print("✓ Summary generated!")
        print()
        print("=" * 80)
        print("RESULT")
        print("=" * 80)
        print()
        print(summary)
        print()
        print("=" * 80)
        print()

        # Stats
        print("Statistics:")
        print(f"  Input: {len(sample_text.split())} words")
        print(f"  Output: {len(summary.split())} words")
        print(f"  Compression: {len(sample_text.split()) / len(summary.split()):.1f}x")
        print()

        # Check if it's actually a summary (not just mock or error)
        if "Error" in summary or len(summary.split()) < 10:
            print("⚠ Warning: Summary seems too short or contains errors")
            return 1

        print("✓ TEST PASSED")
        return 0

    except Exception as e:
        print(f"✗ Error generating summary: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
