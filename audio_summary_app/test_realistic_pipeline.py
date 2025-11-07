#!/usr/bin/env python3
"""
Realistic Pipeline Test: Simulates actual recording flow

This test simulates the real production behavior:
- Transcribes audio in one go
- Splits transcript into 300-second chunks (5 minute chunks like production)
- Waits 10 seconds after each chunk is processed
- Waits 10 seconds after all chunks before final summary
- Tracks memory usage throughout
"""

import sys
import time
import psutil
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Tuple, List

sys.path.insert(0, str(Path(__file__).parent / "src"))

from audio_summary_app.config import Config
from audio_summary_app.transcript_buffer import TranscriptBuffer
from audio_summary_app.summarizer import MapReduceSummarizer
from parakeet_mlx import from_pretrained


def get_memory_usage() -> Dict[str, float]:
    """Get current process memory usage in MB"""
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    return {
        'rss_mb': mem_info.rss / 1024 / 1024,
        'vms_mb': mem_info.vms / 1024 / 1024,
    }


def transcribe_audio_file(audio_path: str) -> Tuple[str, float]:
    """Transcribe audio file using Parakeet"""
    print("="*80)
    print("TRANSCRIPTION PHASE (Parakeet)")
    print("="*80)
    print(f"Audio file: {audio_path}")
    print()

    model_path = "mlx-community/parakeet-tdt-0.6b-v3"
    print(f"Loading model: {model_path}...")
    model = from_pretrained(model_path)
    print("✓ Model loaded")
    print()

    print("Transcribing...")
    start = time.time()
    result = model.transcribe(audio_path)
    elapsed = time.time() - start

    transcript = result.text
    word_count = len(transcript.split())

    print(f"✓ Complete: {word_count:,} words in {elapsed:.1f}s")
    print()

    return transcript, elapsed


def split_by_time(
    transcript: str,
    chunk_duration_seconds: int = 300,
    words_per_minute: int = 150
) -> List[str]:
    """
    Split transcript into time-based chunks.

    Simulates the production chunking behavior where chunks are created
    based on elapsed recording time, not word count.
    """
    words = transcript.split()
    total_words = len(words)

    # Calculate words per chunk based on speaking rate and chunk duration
    words_per_chunk = int((chunk_duration_seconds / 60) * words_per_minute)

    chunks = []
    for i in range(0, total_words, words_per_chunk):
        chunk_words = words[i:i + words_per_chunk]
        chunks.append(' '.join(chunk_words))

    return chunks


def test_model_realistic(
    transcript: str,
    model_name: str,
    config: Config,
    chunk_delay_seconds: int = 10,
    final_delay_seconds: int = 10
) -> Dict:
    """
    Test model with realistic timing simulation.

    Args:
        transcript: Full transcript
        model_name: Ollama model name
        config: Configuration
        chunk_delay_seconds: Delay after each chunk (simulates streaming delay)
        final_delay_seconds: Delay before final summary (simulates user stopping)
    """
    print("="*80)
    print(f"REALISTIC PIPELINE TEST: {model_name}")
    print("="*80)
    print()

    mem_start = get_memory_usage()
    time_start = time.time()

    # Initialize components
    transcript_buffer = TranscriptBuffer(
        max_buffer_size=config.max_buffer_size,
        chunk_duration=config.chunk_duration  # 300 seconds = 5 minutes
    )

    summarizer = MapReduceSummarizer(
        model_name=model_name,
        summary_interval=config.summary_interval,
        chunk_summary_max_tokens=config.chunk_summary_max_tokens,
        final_summary_max_tokens=config.final_summary_max_tokens,
        chunk_summary_prompt=config.chunk_summary_prompt,
        final_summary_prompt=config.final_summary_prompt
    )

    # Split transcript into 5-minute chunks (like production)
    chunks = split_by_time(transcript, chunk_duration_seconds=300)
    print(f"Split into {len(chunks)} chunks (5 min each)")
    print()

    # Process each chunk with delays (simulates streaming)
    chunk_summaries = []
    chunk_times = []
    chunk_memories = []

    start_time = datetime.now()

    for i, chunk_text in enumerate(chunks, 1):
        print(f"[Chunk {i}/{len(chunks)}]")
        print(f"  Words: {len(chunk_text.split())}")

        # Calculate simulated timestamp
        elapsed_seconds = (i - 1) * 300
        chunk_timestamp = start_time + timedelta(seconds=elapsed_seconds)

        # Add to buffer
        transcript_buffer.add_segment(chunk_text, source="mixed")

        # Process chunk (like production does every 5 minutes)
        chunk_start = time.time()
        mem_before = get_memory_usage()

        summary = summarizer.summarize_chunk(chunk_text)
        summarizer.add_intermediate_summary(summary)

        chunk_time = time.time() - chunk_start
        mem_after = get_memory_usage()

        chunk_summaries.append(summary)
        chunk_times.append(chunk_time)
        chunk_memories.append(mem_after['rss_mb'])

        print(f"  Summary: {len(summary.split())} words ({chunk_time:.1f}s)")
        print(f"  Memory: {mem_after['rss_mb']:.1f}MB")

        # Simulate streaming delay (production waits for more audio)
        if i < len(chunks):
            print(f"  Waiting {chunk_delay_seconds}s (simulating streaming)...")
            time.sleep(chunk_delay_seconds)
        print()

    # Simulate user stopping recording
    print(f"[Recording Stopped]")
    print(f"  Waiting {final_delay_seconds}s before final summary...")
    time.sleep(final_delay_seconds)
    print()

    # Generate final summary
    print("[Final Summary]")
    final_start = time.time()
    mem_before_final = get_memory_usage()

    final_summary = summarizer.generate_final_summary(chunks=None)

    final_time = time.time() - final_start
    mem_after_final = get_memory_usage()

    print(f"  Summary: {len(final_summary.split())} words ({final_time:.1f}s)")
    print(f"  Memory: {mem_after_final['rss_mb']:.1f}MB")
    print()

    # Extract structured data
    print("[Structured Data Extraction]")
    data_start = time.time()
    mem_before_data = get_memory_usage()

    structured_data = summarizer.extract_structured_data(config.data_extraction_prompt)

    data_time = time.time() - data_start
    mem_after_data = get_memory_usage()

    print(f"  Extracted: {len(structured_data.get('contacts', []))} contacts, "
          f"{len(structured_data.get('companies', []))} companies, "
          f"{len(structured_data.get('deals', []))} deals")
    print(f"  Time: {data_time:.1f}s")
    print(f"  Memory: {mem_after_data['rss_mb']:.1f}MB")
    print()

    # Calculate total metrics
    total_time = time.time() - time_start
    mem_end = get_memory_usage()
    peak_memory = max(chunk_memories + [mem_after_final['rss_mb'], mem_after_data['rss_mb']])

    # Display final summary
    print("-"*80)
    print("FINAL SUMMARY:")
    print("-"*80)
    print(final_summary)
    print()

    # Display structured data highlights
    print("-"*80)
    print("STRUCTURED DATA:")
    print("-"*80)
    contacts = structured_data.get('contacts', [])
    companies = structured_data.get('companies', [])
    deals = structured_data.get('deals', [])

    if contacts:
        print(f"Contacts ({len(contacts)}):")
        for c in contacts[:3]:
            print(f"  - {c.get('name', 'N/A')} ({c.get('role', 'N/A')})")

    if companies:
        print(f"Companies ({len(companies)}):")
        for co in companies[:3]:
            print(f"  - {co.get('name', 'N/A')} (AUM: {co.get('aum', 'N/A')})")

    if deals:
        print(f"Deals ({len(deals)}):")
        for d in deals[:3]:
            print(f"  - Ticket: {d.get('ticket_size', 'N/A')}")
    print()

    # Summary metrics
    print("="*80)
    print("METRICS SUMMARY")
    print("="*80)
    print(f"Total pipeline time: {total_time:.1f}s")
    print(f"  Chunk processing: {sum(chunk_times):.1f}s ({len(chunks)} chunks)")
    print(f"  Final summary: {final_time:.1f}s")
    print(f"  Data extraction: {data_time:.1f}s")
    print(f"  Delays (simulated): {chunk_delay_seconds * (len(chunks) - 1) + final_delay_seconds}s")
    print()
    print(f"Memory usage:")
    print(f"  Start: {mem_start['rss_mb']:.1f}MB")
    print(f"  Peak: {peak_memory:.1f}MB")
    print(f"  End: {mem_end['rss_mb']:.1f}MB")
    print(f"  Delta: +{peak_memory - mem_start['rss_mb']:.1f}MB")
    print()

    return {
        'model_name': model_name,
        'total_time': total_time,
        'chunk_count': len(chunks),
        'chunk_times': chunk_times,
        'final_time': final_time,
        'data_time': data_time,
        'active_time': sum(chunk_times) + final_time + data_time,
        'delay_time': chunk_delay_seconds * (len(chunks) - 1) + final_delay_seconds,
        'start_memory_mb': mem_start['rss_mb'],
        'peak_memory_mb': peak_memory,
        'end_memory_mb': mem_end['rss_mb'],
        'memory_delta_mb': peak_memory - mem_start['rss_mb'],
        'final_summary_words': len(final_summary.split()),
        'contacts_extracted': len(contacts),
        'companies_extracted': len(companies),
        'deals_extracted': len(deals),
        'final_summary': final_summary,
        'structured_data': structured_data
    }


def compare_models(metrics_4b: Dict, metrics_1_7b: Dict):
    """Compare metrics from both models"""
    print()
    print("="*80)
    print("REALISTIC PIPELINE COMPARISON")
    print("="*80)
    print()

    print(f"QWEN3:4B (Current - 2.5GB):")
    print(f"  Total time: {metrics_4b['total_time']:.1f}s")
    print(f"    Active processing: {metrics_4b['active_time']:.1f}s")
    print(f"    Simulated delays: {metrics_4b['delay_time']:.1f}s")
    print(f"  Memory: {metrics_4b['start_memory_mb']:.1f}MB → {metrics_4b['peak_memory_mb']:.1f}MB (Δ +{metrics_4b['memory_delta_mb']:.1f}MB)")
    print(f"  Summary: {metrics_4b['final_summary_words']} words")
    print(f"  Entities: {metrics_4b['contacts_extracted']} contacts, "
          f"{metrics_4b['companies_extracted']} companies, "
          f"{metrics_4b['deals_extracted']} deals")
    print()

    print(f"QWEN3:1.7B (Smaller - 1.4GB):")
    print(f"  Total time: {metrics_1_7b['total_time']:.1f}s")
    print(f"    Active processing: {metrics_1_7b['active_time']:.1f}s")
    print(f"    Simulated delays: {metrics_1_7b['delay_time']:.1f}s")
    print(f"  Memory: {metrics_1_7b['start_memory_mb']:.1f}MB → {metrics_1_7b['peak_memory_mb']:.1f}MB (Δ +{metrics_1_7b['memory_delta_mb']:.1f}MB)")
    print(f"  Summary: {metrics_1_7b['final_summary_words']} words")
    print(f"  Entities: {metrics_1_7b['contacts_extracted']} contacts, "
          f"{metrics_1_7b['companies_extracted']} companies, "
          f"{metrics_1_7b['deals_extracted']} deals")
    print()

    print("DIFFERENCES:")
    active_diff = metrics_4b['active_time'] - metrics_1_7b['active_time']
    active_pct = (active_diff / metrics_4b['active_time']) * 100
    print(f"  Active processing time: {active_diff:+.1f}s ({active_pct:+.1f}%)")

    mem_diff = metrics_4b['memory_delta_mb'] - metrics_1_7b['memory_delta_mb']
    mem_pct = (mem_diff / metrics_4b['memory_delta_mb']) * 100 if metrics_4b['memory_delta_mb'] > 0 else 0
    print(f"  Memory delta: {mem_diff:+.1f}MB ({mem_pct:+.1f}%)")

    word_diff = metrics_4b['final_summary_words'] - metrics_1_7b['final_summary_words']
    word_pct = (word_diff / metrics_4b['final_summary_words']) * 100
    print(f"  Summary length: {word_diff:+d} words ({word_pct:+.1f}%)")

    contact_diff = metrics_4b['contacts_extracted'] - metrics_1_7b['contacts_extracted']
    print(f"  Contacts: {contact_diff:+d}")

    company_diff = metrics_4b['companies_extracted'] - metrics_1_7b['companies_extracted']
    print(f"  Companies: {company_diff:+d}")

    deal_diff = metrics_4b['deals_extracted'] - metrics_1_7b['deals_extracted']
    print(f"  Deals: {deal_diff:+d}")
    print()


def main():
    """Run realistic pipeline comparison"""
    print()
    print("="*80)
    print("REALISTIC PIPELINE COMPARISON: qwen3:4b vs qwen3:1.7b")
    print("Simulates actual recording with chunking and delays")
    print("="*80)
    print()

    # System info
    sys_mem = psutil.virtual_memory()
    print(f"System: {sys_mem.total / 1024**3:.1f}GB RAM, {sys_mem.available / 1024**3:.1f}GB available")
    print()

    # Transcribe audio once
    audio_path = "/Users/adambutler/Projects/private_notes/first_meeting.mp3"

    try:
        transcript, transcribe_time = transcribe_audio_file(audio_path)
        print(f"Transcript ready: {len(transcript.split())} words")
        print()
    except Exception as e:
        print(f"✗ Transcription failed: {e}")
        return 1

    # Initialize config
    config = Config()
    config.output_dir = "./test_summaries"

    # Test both models with realistic timing
    try:
        print()
        metrics_4b = test_model_realistic(
            transcript=transcript,
            model_name="qwen3:4b-instruct",
            config=config,
            chunk_delay_seconds=10,
            final_delay_seconds=10
        )
    except Exception as e:
        print(f"✗ qwen3:4b test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    try:
        print()
        metrics_1_7b = test_model_realistic(
            transcript=transcript,
            model_name="qwen3:1.7b",
            config=config,
            chunk_delay_seconds=10,
            final_delay_seconds=10
        )
    except Exception as e:
        print(f"✗ qwen3:1.7b test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Compare results
    compare_models(metrics_4b, metrics_1_7b)

    print("="*80)
    print("✓ REALISTIC COMPARISON COMPLETE")
    print("="*80)
    print()

    return 0


if __name__ == "__main__":
    try:
        exit(main())
    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user")
        exit(1)
