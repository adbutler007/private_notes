#!/usr/bin/env python3
"""
Model Comparison Test: qwen3:4b vs qwen3:1.7b (with Memory Tracking)

Tests the complete pipeline (Parakeet transcription + summarization)
with both LLM models to compare output quality, speed, and memory usage.
"""

import sys
import time
import psutil
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple

sys.path.insert(0, str(Path(__file__).parent / "src"))

from audio_summary_app.config import Config
from audio_summary_app.summarizer import MapReduceSummarizer
from parakeet_mlx import from_pretrained


def get_memory_usage() -> Dict[str, float]:
    """Get current process memory usage in MB"""
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    return {
        'rss_mb': mem_info.rss / 1024 / 1024,  # Resident Set Size (physical memory)
        'vms_mb': mem_info.vms / 1024 / 1024,  # Virtual Memory Size
    }


def transcribe_audio_file(audio_path: str, model_path: str = "mlx-community/parakeet-tdt-0.6b-v3") -> Tuple[str, Dict]:
    """Transcribe audio file using Parakeet MLX and track memory"""
    print("="*80)
    print("TRANSCRIPTION PHASE")
    print("="*80)
    print(f"Audio file: {audio_path}")
    print(f"Model: {model_path}")
    print()

    mem_before = get_memory_usage()
    print(f"Memory before loading: {mem_before['rss_mb']:.1f}MB RSS")

    print("Loading Parakeet model...")
    load_start = time.time()
    model = from_pretrained(model_path)
    load_time = time.time() - load_start

    mem_after_load = get_memory_usage()
    mem_model = mem_after_load['rss_mb'] - mem_before['rss_mb']
    print(f"✓ Model loaded ({load_time:.1f}s)")
    print(f"  Memory after loading: {mem_after_load['rss_mb']:.1f}MB RSS")
    print(f"  Model memory: +{mem_model:.1f}MB")
    print()

    print("Transcribing audio...")
    transcribe_start = time.time()
    mem_before_transcribe = get_memory_usage()

    result = model.transcribe(audio_path)

    transcribe_time = time.time() - transcribe_start
    mem_after_transcribe = get_memory_usage()
    mem_peak = mem_after_transcribe['rss_mb']

    transcript = result.text
    word_count = len(transcript.split())

    print(f"✓ Transcription complete")
    print(f"  Time: {transcribe_time:.1f}s")
    print(f"  Words: {word_count:,}")
    print(f"  Sentences: {len(result.sentences)}")
    print(f"  Peak memory: {mem_peak:.1f}MB RSS")
    print()

    metrics = {
        'load_time': load_time,
        'transcribe_time': transcribe_time,
        'model_memory_mb': mem_model,
        'peak_memory_mb': mem_peak,
    }

    return transcript, metrics


def test_model(
    transcript: str,
    model_name: str,
    config: Config,
    output_suffix: str
) -> Tuple[str, Dict]:
    """Test summarization with a specific model and track memory"""
    print("="*80)
    print(f"TESTING MODEL: {model_name}")
    print("="*80)
    print()

    mem_start = get_memory_usage()
    print(f"Memory at start: {mem_start['rss_mb']:.1f}MB RSS")
    print()

    # Initialize summarizer with specific model
    summarizer = MapReduceSummarizer(
        model_name=model_name,
        summary_interval=config.summary_interval,
        chunk_summary_max_tokens=config.chunk_summary_max_tokens,
        final_summary_max_tokens=config.final_summary_max_tokens,
        chunk_summary_prompt=config.chunk_summary_prompt,
        final_summary_prompt=config.final_summary_prompt
    )

    word_count = len(transcript.split())
    print(f"Input transcript: {word_count:,} words")
    print()

    # Track memory for chunk summary
    print("Generating chunk summary...")
    chunk_start = time.time()
    mem_before_chunk = get_memory_usage()

    chunk_summary = summarizer.summarize_chunk(transcript)

    chunk_time = time.time() - chunk_start
    mem_after_chunk = get_memory_usage()
    mem_chunk_peak = mem_after_chunk['rss_mb']

    summarizer.add_intermediate_summary(chunk_summary)
    print(f"✓ Chunk summary: {len(chunk_summary.split())} words ({chunk_time:.1f}s)")
    print(f"  Peak memory: {mem_chunk_peak:.1f}MB RSS")
    print()

    # Track memory for final summary
    print("Generating final summary...")
    final_start = time.time()
    mem_before_final = get_memory_usage()

    final_summary = summarizer.generate_final_summary(chunks=None)

    final_time = time.time() - final_start
    mem_after_final = get_memory_usage()
    mem_final_peak = mem_after_final['rss_mb']

    print(f"✓ Final summary: {len(final_summary.split())} words ({final_time:.1f}s)")
    print(f"  Peak memory: {mem_final_peak:.1f}MB RSS")
    print()

    # Track memory for data extraction
    print("Extracting structured data...")
    data_start = time.time()
    mem_before_data = get_memory_usage()

    structured_data = summarizer.extract_structured_data(config.data_extraction_prompt)

    data_time = time.time() - data_start
    mem_after_data = get_memory_usage()
    mem_data_peak = mem_after_data['rss_mb']

    print(f"✓ Structured data extracted ({data_time:.1f}s)")
    print(f"  Peak memory: {mem_data_peak:.1f}MB RSS")
    print()

    # Calculate overall peak
    overall_peak = max(mem_chunk_peak, mem_final_peak, mem_data_peak)
    mem_delta = overall_peak - mem_start['rss_mb']

    print(f"MEMORY SUMMARY:")
    print(f"  Starting: {mem_start['rss_mb']:.1f}MB")
    print(f"  Peak: {overall_peak:.1f}MB")
    print(f"  Delta: +{mem_delta:.1f}MB")
    print()

    # Display summary
    print("-"*80)
    print("FINAL SUMMARY:")
    print("-"*80)
    print(final_summary)
    print()

    # Display structured data highlights
    print("-"*80)
    print("STRUCTURED DATA HIGHLIGHTS:")
    print("-"*80)
    contacts = structured_data.get('contacts', [])
    companies = structured_data.get('companies', [])
    deals = structured_data.get('deals', [])

    print(f"Contacts: {len(contacts)}")
    if contacts:
        print(f"  - {contacts[0].get('name', 'N/A')} ({contacts[0].get('role', 'N/A')})")

    print(f"Companies: {len(companies)}")
    if companies:
        print(f"  - {companies[0].get('name', 'N/A')} (AUM: {companies[0].get('aum', 'N/A')})")

    print(f"Deals: {len(deals)}")
    if deals:
        print(f"  - Ticket size: {deals[0].get('ticket_size', 'N/A')}")
    print()

    # Save outputs
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_path = output_dir / f"summary_{output_suffix}_{timestamp}.txt"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(final_summary)

    import json
    data_path = output_dir / f"data_{output_suffix}_{timestamp}.json"
    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(structured_data, f, indent=2, ensure_ascii=False)

    print(f"✓ Saved to:")
    print(f"  Summary: {summary_path}")
    print(f"  Data: {data_path}")
    print()

    # Collect metrics
    metrics = {
        'model_name': model_name,
        'input_words': word_count,
        'chunk_summary_words': len(chunk_summary.split()),
        'final_summary_words': len(final_summary.split()),
        'compression_ratio': word_count / len(final_summary.split()),
        'chunk_time': chunk_time,
        'final_time': final_time,
        'data_time': data_time,
        'total_time': chunk_time + final_time + data_time,
        'start_memory_mb': mem_start['rss_mb'],
        'peak_memory_mb': overall_peak,
        'memory_delta_mb': mem_delta,
        'contacts_extracted': len(contacts),
        'companies_extracted': len(companies),
        'deals_extracted': len(deals),
        'summary_path': str(summary_path),
        'data_path': str(data_path)
    }

    return final_summary, metrics


def compare_models(metrics_4b: Dict, metrics_1_7b: Dict, transcribe_metrics: Dict):
    """Compare metrics from both models"""
    print()
    print("="*80)
    print("MODEL COMPARISON: qwen3:4b vs qwen3:1.7b")
    print("="*80)
    print()

    print("TRANSCRIPTION (Parakeet):")
    print(f"  Model load time: {transcribe_metrics['load_time']:.1f}s")
    print(f"  Transcribe time: {transcribe_metrics['transcribe_time']:.1f}s")
    print(f"  Model memory: +{transcribe_metrics['model_memory_mb']:.1f}MB")
    print(f"  Peak memory: {transcribe_metrics['peak_memory_mb']:.1f}MB")
    print()

    print("QWEN3:4B (Current - 2.5GB model):")
    print(f"  Final summary: {metrics_4b['final_summary_words']} words")
    print(f"  Compression: {metrics_4b['compression_ratio']:.1f}x")
    print(f"  Processing time: {metrics_4b['total_time']:.1f}s")
    print(f"  Memory usage: {metrics_4b['start_memory_mb']:.1f}MB → {metrics_4b['peak_memory_mb']:.1f}MB (Δ +{metrics_4b['memory_delta_mb']:.1f}MB)")
    print(f"  Entities: {metrics_4b['contacts_extracted']} contacts, "
          f"{metrics_4b['companies_extracted']} companies, "
          f"{metrics_4b['deals_extracted']} deals")
    print()

    print("QWEN3:1.7B (Smaller - 1.4GB model):")
    print(f"  Final summary: {metrics_1_7b['final_summary_words']} words")
    print(f"  Compression: {metrics_1_7b['compression_ratio']:.1f}x")
    print(f"  Processing time: {metrics_1_7b['total_time']:.1f}s")
    print(f"  Memory usage: {metrics_1_7b['start_memory_mb']:.1f}MB → {metrics_1_7b['peak_memory_mb']:.1f}MB (Δ +{metrics_1_7b['memory_delta_mb']:.1f}MB)")
    print(f"  Entities: {metrics_1_7b['contacts_extracted']} contacts, "
          f"{metrics_1_7b['companies_extracted']} companies, "
          f"{metrics_1_7b['deals_extracted']} deals")
    print()

    print("DIFFERENCES:")
    word_diff = metrics_4b['final_summary_words'] - metrics_1_7b['final_summary_words']
    word_diff_pct = (word_diff / metrics_4b['final_summary_words']) * 100 if metrics_4b['final_summary_words'] > 0 else 0
    print(f"  Summary length: {word_diff:+d} words ({word_diff_pct:+.1f}%)")

    time_diff = metrics_4b['total_time'] - metrics_1_7b['total_time']
    time_diff_pct = (time_diff / metrics_4b['total_time']) * 100 if metrics_4b['total_time'] > 0 else 0
    print(f"  Processing time: {time_diff:+.1f}s ({time_diff_pct:+.1f}%)")

    mem_diff = metrics_4b['memory_delta_mb'] - metrics_1_7b['memory_delta_mb']
    mem_diff_pct = (mem_diff / metrics_4b['memory_delta_mb']) * 100 if metrics_4b['memory_delta_mb'] > 0 else 0
    print(f"  Memory delta: {mem_diff:+.1f}MB ({mem_diff_pct:+.1f}%)")

    contact_diff = metrics_4b['contacts_extracted'] - metrics_1_7b['contacts_extracted']
    print(f"  Contacts extracted: {contact_diff:+d}")

    company_diff = metrics_4b['companies_extracted'] - metrics_1_7b['companies_extracted']
    print(f"  Companies extracted: {company_diff:+d}")

    deal_diff = metrics_4b['deals_extracted'] - metrics_1_7b['deals_extracted']
    print(f"  Deals extracted: {deal_diff:+d}")
    print()

    print("SPEED & MEMORY COMPARISON:")
    if metrics_1_7b['total_time'] < metrics_4b['total_time']:
        speedup = metrics_4b['total_time'] / metrics_1_7b['total_time']
        print(f"  ✓ qwen3:1.7b is {speedup:.2f}x FASTER")
    else:
        slowdown = metrics_1_7b['total_time'] / metrics_4b['total_time']
        print(f"  ✗ qwen3:1.7b is {slowdown:.2f}x SLOWER")

    if metrics_1_7b['memory_delta_mb'] < metrics_4b['memory_delta_mb']:
        mem_saving = (1 - metrics_1_7b['memory_delta_mb'] / metrics_4b['memory_delta_mb']) * 100
        print(f"  ✓ qwen3:1.7b uses {mem_saving:.1f}% LESS memory")
    else:
        mem_increase = (metrics_1_7b['memory_delta_mb'] / metrics_4b['memory_delta_mb'] - 1) * 100
        print(f"  ✗ qwen3:1.7b uses {mem_increase:.1f}% MORE memory")
    print()


def main():
    """Run model comparison with memory tracking"""
    print()
    print("="*80)
    print("COMPLETE PIPELINE COMPARISON: qwen3:4b vs qwen3:1.7b")
    print("WITH MEMORY TRACKING")
    print("="*80)
    print()

    # Get system memory info
    sys_mem = psutil.virtual_memory()
    print(f"System Memory: {sys_mem.total / 1024**3:.1f}GB total, {sys_mem.available / 1024**3:.1f}GB available")
    print()

    # Use the provided audio file
    audio_path = "/Users/adambutler/Projects/private_notes/first_meeting.mp3"

    if not Path(audio_path).exists():
        print(f"✗ Audio file not found: {audio_path}")
        return 1

    # Step 1: Transcribe audio (once, reuse for both models)
    try:
        transcript, transcribe_metrics = transcribe_audio_file(audio_path)
    except Exception as e:
        print(f"✗ Transcription failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Initialize config
    config = Config()
    config.output_dir = "./test_summaries"

    # Step 2: Test qwen3:4b (current model)
    try:
        print()
        summary_4b, metrics_4b = test_model(
            transcript=transcript,
            model_name="qwen3:4b-instruct",
            config=config,
            output_suffix="qwen3_4b"
        )
    except Exception as e:
        print(f"✗ qwen3:4b test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Step 3: Test qwen3:1.7b (smaller model)
    try:
        print()
        summary_1_7b, metrics_1_7b = test_model(
            transcript=transcript,
            model_name="qwen3:1.7b",
            config=config,
            output_suffix="qwen3_1_7b"
        )
    except Exception as e:
        print(f"✗ qwen3:1.7b test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Step 4: Compare results
    compare_models(metrics_4b, metrics_1_7b, transcribe_metrics)

    print("="*80)
    print("✓ COMPARISON COMPLETE")
    print("="*80)
    print()
    print("Review outputs at:")
    print(f"  qwen3:4b: {metrics_4b['summary_path']}")
    print(f"  qwen3:1.7b: {metrics_1_7b['summary_path']}")
    print()

    return 0


if __name__ == "__main__":
    try:
        exit(main())
    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user")
        exit(1)
