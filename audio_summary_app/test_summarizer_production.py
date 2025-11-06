#!/usr/bin/env python3
"""
Production-Quality Summarizer Test

This script accurately emulates the real production pipeline:
1. Time-based chunking (not word count)
2. Natural buffer finalization based on elapsed time
3. Rolling summaries during "recording"
4. Final summary generation on "stop"

Tests both with and without intermediate summaries.
"""

import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple

from src.audio_summary_app.transcript_buffer import TranscriptBuffer
from src.audio_summary_app.summarizer import MapReduceSummarizer
from src.audio_summary_app.config import Config


# Realistic simulation parameters
WORDS_PER_MINUTE = 150  # Average speaking rate
SEGMENT_SIZE_WORDS = 50  # Transcriber outputs ~50 words at a time
SEGMENT_INTERVAL_SECONDS = (SEGMENT_SIZE_WORDS / WORDS_PER_MINUTE) * 60  # ~20 seconds per segment


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

    raise UnicodeDecodeError(f"Could not decode file with any common encoding")


def split_into_segments(text: str, words_per_segment: int = SEGMENT_SIZE_WORDS) -> List[str]:
    """
    Split transcript into realistic segments that a transcriber would produce.
    Each segment is approximately words_per_segment words.
    """
    words = text.split()
    segments = []

    for i in range(0, len(words), words_per_segment):
        segment = ' '.join(words[i:i + words_per_segment])
        segments.append(segment)

    return segments


def calculate_total_duration(word_count: int) -> float:
    """Calculate total duration in seconds based on word count"""
    return (word_count / WORDS_PER_MINUTE) * 60


def test_with_rolling_summaries(
    segments: List[str],
    config: Config,
    output_prefix: str = "rolling"
) -> Tuple[str, dict]:
    """
    Test Path A: WITH rolling summaries (normal recording behavior)

    Simulates the actual production flow:
    - Segments arrive with realistic timestamps
    - Buffer automatically finalizes chunks based on time
    - Rolling summaries generated at intervals
    - Final summary combines intermediate summaries
    """
    print("=" * 80)
    print("TEST PATH A: WITH ROLLING SUMMARIES (Production Flow)")
    print("=" * 80)
    print()

    # Initialize components
    transcript_buffer = TranscriptBuffer(
        max_buffer_size=config.max_buffer_size,
        chunk_duration=config.chunk_duration
    )

    summarizer = MapReduceSummarizer(
        model_name=config.llm_model_name,
        summary_interval=config.summary_interval
    )

    # Calculate expected behavior
    total_words = sum(len(seg.split()) for seg in segments)
    total_duration = calculate_total_duration(total_words)
    expected_chunks = int(total_duration / config.chunk_duration) + 1

    print(f"Transcript Analysis:")
    print(f"  Total words: {total_words:,}")
    print(f"  Total segments: {len(segments)}")
    print(f"  Estimated duration: {total_duration:.0f}s ({total_duration/60:.1f} minutes)")
    print(f"  Expected chunks: {expected_chunks} (at {config.chunk_duration}s per chunk)")
    print()

    # Simulate streaming transcription with realistic timestamps
    start_time = datetime.now()
    last_summary_time = time.time()
    rolling_summaries_generated = 0
    segments_processed = 0

    print("Simulating streaming transcription...")
    print()

    for i, segment in enumerate(segments, 1):
        # Calculate realistic timestamp for this segment
        elapsed_seconds = (i - 1) * SEGMENT_INTERVAL_SECONDS
        segment_timestamp = start_time + timedelta(seconds=elapsed_seconds)

        # Add segment to buffer (this is what the transcription worker does)
        # The buffer will automatically finalize chunks based on elapsed time
        transcript_buffer.add_segment(segment, source="mixed")
        segments_processed += 1

        # Print progress every 10 segments
        if i % 10 == 0:
            stats = transcript_buffer.get_buffer_stats()
            print(f"[Progress] Segment {i}/{len(segments)}: "
                  f"{stats['segment_count']} buffered, "
                  f"{stats['chunk_count']} chunks finalized")

        # Simulate the summary worker checking if it's time for rolling summary
        # This happens every summary_interval seconds of simulated time
        simulated_current_time = time.time() + elapsed_seconds
        if simulated_current_time - last_summary_time >= config.summary_interval:
            # Get all chunks (finalizes any pending chunk)
            chunks = transcript_buffer.get_all_chunks()

            if chunks:
                print()
                print("=" * 80)
                print(f"ROLLING SUMMARY #{rolling_summaries_generated + 1}")
                print("=" * 80)

                # Summarize the most recent chunk (MAP phase)
                latest_chunk = chunks[-1]
                chunk_words = len(latest_chunk['text'].split())
                print(f"Chunk {len(chunks)}: {chunk_words} words")
                print(f"Time range: {latest_chunk['start_time'].strftime('%H:%M:%S')} - "
                      f"{latest_chunk['end_time'].strftime('%H:%M:%S')}")
                print()

                summary = summarizer.summarize_chunk(latest_chunk['text'])
                summarizer.add_intermediate_summary(summary)
                rolling_summaries_generated += 1

                print(f"Summary ({len(summary.split())} words):")
                print(summary)
                print("=" * 80)
                print()

            last_summary_time = simulated_current_time

    # Final statistics
    print()
    print(f"Streaming complete: {segments_processed} segments processed")
    final_stats = transcript_buffer.get_buffer_stats()
    print(f"Final buffer state: {final_stats['segment_count']} segments, "
          f"{final_stats['chunk_count']} chunks")
    print(f"Rolling summaries generated: {rolling_summaries_generated}")
    print()

    # Generate final summary (REDUCE phase - this happens on "stop recording")
    print("=" * 80)
    print("GENERATING FINAL SUMMARY (REDUCE Phase)")
    print("=" * 80)
    print()

    chunks = transcript_buffer.get_all_chunks()
    print(f"Processing {len(chunks)} chunks with {len(summarizer.intermediate_summaries)} "
          f"intermediate summaries...")
    print()

    final_summary = summarizer.generate_final_summary(chunks)

    # Save summary
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"summary_{output_prefix}_{timestamp}.txt"
    filepath = output_dir / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(final_summary)

    print(final_summary)
    print()
    print("=" * 80)
    print(f"Summary saved to: {filepath}")
    print("=" * 80)

    # Collect metrics
    metrics = {
        'total_words': total_words,
        'total_segments': len(segments),
        'total_duration_seconds': total_duration,
        'chunks_created': len(chunks),
        'rolling_summaries': rolling_summaries_generated,
        'final_summary_words': len(final_summary.split()),
        'compression_ratio': total_words / len(final_summary.split()),
        'output_file': str(filepath)
    }

    # Clear buffers
    transcript_buffer.clear()
    summarizer.clear_intermediate_summaries()

    return final_summary, metrics


def test_without_rolling_summaries(
    segments: List[str],
    config: Config,
    output_prefix: str = "direct"
) -> Tuple[str, dict]:
    """
    Test Path B: WITHOUT rolling summaries (fallback path)

    Simulates scenario where:
    - Segments arrive and buffer fills
    - NO rolling summaries during recording
    - Final summary generates summaries directly from chunks
    """
    print()
    print("=" * 80)
    print("TEST PATH B: WITHOUT ROLLING SUMMARIES (Direct Path)")
    print("=" * 80)
    print()

    # Initialize components
    transcript_buffer = TranscriptBuffer(
        max_buffer_size=config.max_buffer_size,
        chunk_duration=config.chunk_duration
    )

    summarizer = MapReduceSummarizer(
        model_name=config.llm_model_name,
        summary_interval=config.summary_interval
    )

    # Calculate expected behavior
    total_words = sum(len(seg.split()) for seg in segments)
    total_duration = calculate_total_duration(total_words)

    print(f"Loading all segments directly into buffer...")
    print(f"  Total words: {total_words:,}")
    print(f"  Total segments: {len(segments)}")
    print()

    # Load all segments with realistic timestamps
    start_time = datetime.now()

    for i, segment in enumerate(segments):
        elapsed_seconds = i * SEGMENT_INTERVAL_SECONDS
        segment_timestamp = start_time + timedelta(seconds=elapsed_seconds)
        transcript_buffer.add_segment(segment, source="mixed")

    # Get stats
    stats = transcript_buffer.get_buffer_stats()
    print(f"Buffer loaded: {stats['segment_count']} segments, {stats['chunk_count']} chunks")
    print()

    # Generate final summary directly (NO intermediate summaries)
    print("=" * 80)
    print("GENERATING FINAL SUMMARY (Direct from Chunks)")
    print("=" * 80)
    print()

    chunks = transcript_buffer.get_all_chunks()
    print(f"Processing {len(chunks)} chunks directly (no intermediate summaries)...")
    print()

    final_summary = summarizer.generate_final_summary(chunks)

    # Save summary
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"summary_{output_prefix}_{timestamp}.txt"
    filepath = output_dir / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(final_summary)

    print(final_summary)
    print()
    print("=" * 80)
    print(f"Summary saved to: {filepath}")
    print("=" * 80)

    # Collect metrics
    metrics = {
        'total_words': total_words,
        'total_segments': len(segments),
        'total_duration_seconds': total_duration,
        'chunks_created': len(chunks),
        'rolling_summaries': 0,
        'final_summary_words': len(final_summary.split()),
        'compression_ratio': total_words / len(final_summary.split()),
        'output_file': str(filepath)
    }

    # Clear buffers
    transcript_buffer.clear()
    summarizer.clear_intermediate_summaries()

    return final_summary, metrics


def compare_results(metrics_a: dict, metrics_b: dict):
    """Compare results from both test paths"""
    print()
    print("=" * 80)
    print("COMPARISON: Rolling vs Direct Summarization")
    print("=" * 80)
    print()

    print("Path A (With Rolling Summaries):")
    print(f"  Chunks created: {metrics_a['chunks_created']}")
    print(f"  Rolling summaries: {metrics_a['rolling_summaries']}")
    print(f"  Final summary: {metrics_a['final_summary_words']} words")
    print(f"  Compression: {metrics_a['compression_ratio']:.1f}x")
    print()

    print("Path B (Without Rolling Summaries):")
    print(f"  Chunks created: {metrics_b['chunks_created']}")
    print(f"  Rolling summaries: {metrics_b['rolling_summaries']}")
    print(f"  Final summary: {metrics_b['final_summary_words']} words")
    print(f"  Compression: {metrics_b['compression_ratio']:.1f}x")
    print()

    print("Analysis:")
    print(f"  Chunk consistency: {'✓ Same' if metrics_a['chunks_created'] == metrics_b['chunks_created'] else '✗ Different'}")
    word_diff = abs(metrics_a['final_summary_words'] - metrics_b['final_summary_words'])
    print(f"  Summary length difference: {word_diff} words")
    compression_diff = abs(metrics_a['compression_ratio'] - metrics_b['compression_ratio'])
    print(f"  Compression difference: {compression_diff:.1f}x")
    print()


def main():
    """Main test execution"""
    import sys

    print("=" * 80)
    print("PRODUCTION-QUALITY SUMMARIZER TEST")
    print("=" * 80)
    print()

    # Load transcript
    default_path = "/Users/adambutler/Projects/private_notes/transcript.txt"
    transcript_path = sys.argv[1] if len(sys.argv) > 1 else default_path

    try:
        print(f"Loading transcript: {transcript_path}")
        full_transcript = load_transcript(transcript_path)
        print(f"✓ Loaded {len(full_transcript):,} characters")
        print()
    except Exception as e:
        print(f"✗ Error loading transcript: {e}")
        return 1

    # Split into realistic segments
    print("Preparing segments...")
    segments = split_into_segments(full_transcript, SEGMENT_SIZE_WORDS)
    print(f"✓ Created {len(segments)} segments (~{SEGMENT_SIZE_WORDS} words each)")
    print()

    # Initialize config
    config = Config()
    config.output_dir = "./test_summaries"

    print("Configuration:")
    print(f"  Chunk duration: {config.chunk_duration}s ({config.chunk_duration/60:.0f} min)")
    print(f"  Summary interval: {config.summary_interval}s ({config.summary_interval/60:.0f} min)")
    print(f"  Segment interval: {SEGMENT_INTERVAL_SECONDS:.1f}s")
    print(f"  Speaking rate: {WORDS_PER_MINUTE} words/min")
    print()

    # Test both paths
    try:
        # Path A: With rolling summaries (production flow)
        summary_a, metrics_a = test_with_rolling_summaries(segments, config, "rolling")

        # Path B: Without rolling summaries (fallback)
        summary_b, metrics_b = test_without_rolling_summaries(segments, config, "direct")

        # Compare results
        compare_results(metrics_a, metrics_b)

        print("=" * 80)
        print("✓ ALL TESTS COMPLETE")
        print("=" * 80)
        print()
        print("Output files:")
        print(f"  Rolling: {metrics_a['output_file']}")
        print(f"  Direct:  {metrics_b['output_file']}")
        print()

        return 0

    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
