#!/usr/bin/env python3
"""
Test script to emulate the buffered stream from transcriber and test the summarizer
with a real transcript file.
"""

import time
from pathlib import Path
from datetime import datetime

from src.audio_summary_app.transcript_buffer import TranscriptBuffer
from src.audio_summary_app.summarizer import MapReduceSummarizer
from src.audio_summary_app.config import Config


def chunk_text(text: str, chunk_size: int = 200) -> list[str]:
    """
    Split text into chunks of approximately chunk_size words,
    simulating how transcripts would arrive in real-time.
    """
    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size):
        chunk = ' '.join(words[i:i + chunk_size])
        chunks.append(chunk)

    return chunks


def simulate_transcription_stream(transcript_path: str, delay: float = 0.5):
    """
    Simulate the buffered stream that the summarizer would receive from the transcriber.

    Args:
        transcript_path: Path to the transcript file
        delay: Delay between chunks in seconds (simulates real-time transcription)
    """
    print("=" * 80)
    print("Audio Summary App - Transcription Stream Simulation")
    print("=" * 80)
    print()

    # Read the transcript
    transcript_file = Path(transcript_path)
    if not transcript_file.exists():
        print(f"Error: Transcript file not found: {transcript_path}")
        return

    print(f"Loading transcript from: {transcript_path}")

    # Try different encodings
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    full_transcript = None

    for encoding in encodings:
        try:
            with open(transcript_file, 'r', encoding=encoding) as f:
                full_transcript = f.read()
            print(f"Successfully loaded with encoding: {encoding}")
            break
        except UnicodeDecodeError:
            continue

    if full_transcript is None:
        print("Error: Could not decode file with any common encoding")
        return

    print(f"Total transcript length: {len(full_transcript)} characters")
    print(f"Total word count: {len(full_transcript.split())} words")
    print()

    # Initialize components
    config = Config()
    config.output_dir = "./test_summaries"
    config.summary_interval = 60  # Generate summary every 60 seconds for testing

    transcript_buffer = TranscriptBuffer(
        max_buffer_size=config.max_buffer_size,
        chunk_duration=config.chunk_duration
    )

    summarizer = MapReduceSummarizer(
        model_name=config.llm_model_name,
        summary_interval=config.summary_interval
    )

    # Split transcript into chunks (simulating real-time arrival)
    # Each chunk represents ~30-60 seconds of transcription
    chunks = chunk_text(full_transcript, chunk_size=150)

    print(f"Split into {len(chunks)} chunks for simulation")
    print(f"Simulating transcription with {delay}s delay between chunks...")
    print("=" * 80)
    print()

    last_summary_time = time.time()
    chunk_summaries = []

    # Simulate streaming transcription
    for i, chunk in enumerate(chunks, 1):
        # Print progress
        print(f"\n[Chunk {i}/{len(chunks)}] Received transcript chunk:")
        print(f"  Words: {len(chunk.split())}")
        print(f"  Preview: {chunk[:100]}...")

        # Add to buffer (this is what the transcriber does)
        transcript_buffer.add_segment(chunk)

        # Check buffer stats
        stats = transcript_buffer.get_buffer_stats()
        print(f"  Buffer stats: {stats['segment_count']} segments, {stats['total_chars']} chars")

        # Check if it's time for a rolling summary (simulating the summary worker)
        current_time = time.time()
        if current_time - last_summary_time >= config.summary_interval:
            print("\n" + "=" * 80)
            print("GENERATING ROLLING SUMMARY")
            print("=" * 80)

            # Get all chunks from buffer
            buffer_chunks = transcript_buffer.get_all_chunks()

            if buffer_chunks:
                # Summarize the most recent chunk
                latest_chunk = buffer_chunks[-1]
                print(f"Summarizing chunk with {len(latest_chunk['text'].split())} words...")

                summary = summarizer.summarize_chunk(latest_chunk['text'])
                summarizer.add_intermediate_summary(summary)
                chunk_summaries.append(summary)

                print(f"\n[Rolling Summary {len(chunk_summaries)}]:")
                print(summary)
                print("=" * 80)

            last_summary_time = current_time

        # Simulate delay (real-time transcription)
        time.sleep(delay)

    # Generate final summary (this happens when user clicks "stop")
    print("\n\n" + "=" * 80)
    print("GENERATING FINAL SUMMARY")
    print("=" * 80)
    print()

    # Get all chunks from buffer
    final_chunks = transcript_buffer.get_all_chunks()

    print(f"Processing {len(final_chunks)} chunks for final summary...")
    print()

    # Generate final summary
    final_summary = summarizer.generate_final_summary(final_chunks)

    # Save summary
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"summary_{timestamp}.txt"
    filepath = output_dir / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(final_summary)

    # Display results
    print(final_summary)
    print()
    print("=" * 80)
    print(f"Summary saved to: {filepath}")
    print("=" * 80)
    print()

    # Print statistics
    print("STATISTICS:")
    print(f"  Original transcript: {len(full_transcript.split())} words")
    print(f"  Final summary: {len(final_summary.split())} words")
    print(f"  Compression ratio: {len(full_transcript.split()) / len(final_summary.split()):.1f}x")
    print(f"  Rolling summaries generated: {len(chunk_summaries)}")
    print()

    # Clear buffers (this happens when recording stops)
    transcript_buffer.clear()
    summarizer.clear_intermediate_summaries()
    print("Buffers cleared (memory freed)")


def main():
    """Main entry point"""
    import sys

    # Default to transcript.txt in parent directory
    default_path = "/Users/adambutler/Projects/private_notes/transcript.txt"

    if len(sys.argv) > 1:
        transcript_path = sys.argv[1]
    else:
        transcript_path = default_path

    # Run simulation
    try:
        simulate_transcription_stream(transcript_path, delay=0.2)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
