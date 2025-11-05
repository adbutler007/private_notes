"""
Demo mode for Audio Summary App
Simulates a recording session without requiring audio hardware
Useful for testing the workflow and verifying installation
"""

import time
from pathlib import Path
from datetime import datetime

from .transcript_buffer import TranscriptBuffer
from .summarizer import MapReduceSummarizer
from .config import Config


def simulate_recording_session():
    """
    Simulate a recording session with mock transcripts
    Demonstrates the full workflow without audio hardware
    """
    print("=" * 70)
    print("Audio Summary App - DEMO MODE")
    print("=" * 70)
    print("This demo simulates a recording session without audio hardware.")
    print("It will create mock transcripts and generate a summary.\n")

    # Initialize components
    config = Config()
    config.output_dir = "./demo_output"  # Use separate directory for demo

    transcript_buffer = TranscriptBuffer(
        max_buffer_size=config.max_buffer_size, chunk_duration=config.chunk_duration
    )

    summarizer = MapReduceSummarizer(
        model_name=config.llm_model_name, summary_interval=30  # Shorter for demo
    )

    # Mock transcript segments (simulating a meeting)
    mock_transcripts = [
        "Welcome everyone to today's project sync meeting.",
        "Let's start with a quick round of updates from each team.",
        "The backend team has completed the API integration work.",
        "We're now working on optimizing the database queries for better performance.",
        "The frontend team finished the new dashboard UI last week.",
        "We received positive feedback from the design review.",
        "However, we need to address some accessibility concerns that were raised.",
        "The QA team found a few edge cases that need fixing.",
        "We're targeting end of week for the bug fix deployment.",
        "Moving on to next sprint planning.",
        "Our main focus will be the user authentication redesign.",
        "We also need to tackle the performance issues in the reporting module.",
        "The product team wants to prioritize the mobile responsive updates.",
        "Let's discuss resource allocation for these initiatives.",
        "I think we should dedicate two engineers to the auth work.",
        "The reporting performance can be handled by one person.",
        "Mobile responsiveness might need the full frontend team.",
        "Let's sync again mid-week to check on progress.",
        "Any blockers or concerns we should discuss now?",
        "Alright, thanks everyone. Let's have a productive week.",
    ]

    print("Starting mock recording session...\n")

    # Simulate transcription coming in over time
    for i, transcript in enumerate(mock_transcripts):
        # Simulate time passing
        time.sleep(0.5)

        print(f"[{i+1:02d}] {transcript}")

        # Add to buffer
        transcript_buffer.add_segment(transcript)

        # Generate rolling summary every 10 segments (simulating time interval)
        if (i + 1) % 10 == 0:
            print("\n" + "=" * 70)
            print("ROLLING SUMMARY")
            print("=" * 70)

            chunks = transcript_buffer.get_all_chunks()
            if chunks:
                latest_chunk = chunks[-1]
                summary = summarizer.summarize_chunk(latest_chunk["text"])
                summarizer.add_intermediate_summary(summary)
                print(f"{summary}")

            print("=" * 70 + "\n")

    # Generate final summary
    print("\n" + "=" * 70)
    print("GENERATING FINAL SUMMARY")
    print("=" * 70)

    chunks = transcript_buffer.get_all_chunks()
    final_summary = summarizer.generate_final_summary(chunks)

    # Save summary
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"demo_summary_{timestamp}.txt"
    filepath = output_dir / filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(final_summary)

    print("\n" + final_summary)
    print("\n" + "=" * 70)
    print(f"Demo summary saved to: {filepath}")
    print("=" * 70)

    # Show privacy comparison
    print("\n")
    show_privacy_comparison()


def show_privacy_comparison():
    """Show what gets saved vs what doesn't"""
    print("=" * 70)
    print("PRIVACY & DATA PERSISTENCE")
    print("=" * 70)
    print()

    print("❌ NEVER SAVED TO DISK:")
    print("   - Raw audio data (streamed, never written)")
    print("   - Audio recordings (never created)")
    print("   - Individual transcript segments")
    print("   - Intermediate/rolling summaries")
    print()

    print("✅ SAVED TO DISK:")
    print("   - Final summary only (text file, 2-5 KB)")
    print("   - Location: ./demo_output/ (or ./summaries/ in real use)")
    print()

    print("💾 MEMORY USAGE:")
    print("   - Audio: Streamed through, never stored")
    print("   - Transcripts: Circular buffer (auto-discards old)")
    print("   - Summaries: Accumulated until final save, then cleared")
    print()

    print("🔒 SECURITY FEATURES:")
    print("   - All AI processing on-device (no cloud)")
    print("   - No network calls during operation")
    print("   - Complete user control over what's saved")
    print("   - Memory cleared after each session")
    print()


def main():
    """Entry point for demo"""
    show_privacy_comparison()
    input("Press Enter to run demo...")
    simulate_recording_session()


if __name__ == "__main__":
    main()
