"""
Process a pre-recorded audio file through the full pipeline
Simulates the streaming app but processes an audio file
"""

import numpy as np
from pathlib import Path
from datetime import datetime
import subprocess
import tempfile

from audio_summary_app.config import Config
from audio_summary_app.transcriber import StreamingTranscriber
from audio_summary_app.transcript_buffer import TranscriptBuffer
from audio_summary_app.summarizer import MapReduceSummarizer
import json
import csv

def process_audio_file(audio_path: str):
    """Process an audio file through the complete pipeline"""

    print("=" * 60)
    print("Audio File Processing Pipeline")
    print("=" * 60)
    print(f"Audio file: {audio_path}")

    # Load config
    config = Config()
    print(f"\nConfiguration loaded:")
    print(f"  - STT Model: {config.stt_model_path}")
    print(f"  - LLM Model: {config.llm_model_name}")
    print(f"  - Output dir: {config.output_dir}")

    # For file processing, we'll use MLX Whisper directly instead of simulating streaming
    # This is more efficient and produces the same quality results
    print(f"\nTranscribing audio file with MLX Whisper...")
    print("  (This replicates the same transcription quality as real-time)")
    import mlx_whisper

    # Convert model name to MLX format
    model_mapping = {
        "tiny": "mlx-community/whisper-tiny",
        "base": "mlx-community/whisper-tiny",
        "small": "mlx-community/whisper-small-mlx",
        "medium": "mlx-community/whisper-medium-mlx",
        "large": "mlx-community/whisper-large-v3-mlx",
        "large-v2": "mlx-community/whisper-large-v3-mlx",
        "large-v3": "mlx-community/whisper-large-v3-mlx",
        "large-v3-turbo": "mlx-community/whisper-large-v3-turbo",
        "turbo": "mlx-community/whisper-large-v3-turbo",
    }
    model_repo = model_mapping.get(config.stt_model_path, config.stt_model_path)

    result = mlx_whisper.transcribe(
        audio_path,
        path_or_hf_repo=model_repo
    )

    full_transcript_text = result['text'].strip()
    print(f"\n✓ Transcription complete")
    print(f"  - Model: {model_repo}")
    print(f"  - Transcript length: {len(full_transcript_text)} characters")

    # Print transcript
    print("\n" + "=" * 60)
    print("TRANSCRIPT")
    print("=" * 60)
    print(full_transcript_text)
    print("=" * 60)

    # Initialize summarization components
    print("\nInitializing summarization components...")

    summarizer = MapReduceSummarizer(
        model_name=config.llm_model_name,
        summary_interval=config.summary_interval,
        chunk_summary_max_tokens=config.chunk_summary_max_tokens,
        final_summary_max_tokens=config.final_summary_max_tokens,
        chunk_summary_prompt=config.chunk_summary_prompt,
        final_summary_prompt=config.final_summary_prompt
    )

    print("✓ Summarizer initialized")

    # Split transcript into chunks that simulate real-time processing
    # In real-time, we create a chunk summary every 5 minutes (300 seconds)
    # We'll break the transcript into reasonable chunks to simulate this
    print("\n" + "=" * 60)
    print("CHUNK SUMMARIZATION (simulating 5-minute rolling summaries)")
    print("=" * 60 + "\n")

    # Split transcript into roughly equal chunks
    # For a meeting, we'll assume ~3000 words = ~5 minutes of speaking
    words = full_transcript_text.split()
    words_per_chunk = 3000  # Approximate 5 minutes of speech
    num_chunks = max(1, len(words) // words_per_chunk + (1 if len(words) % words_per_chunk > 500 else 0))

    chunks_text = []
    chunk_size = len(words) // num_chunks
    for i in range(num_chunks):
        start_idx = i * chunk_size
        end_idx = start_idx + chunk_size if i < num_chunks - 1 else len(words)
        chunk_text = ' '.join(words[start_idx:end_idx])
        chunks_text.append(chunk_text)

    print(f"Processing {len(chunks_text)} chunk(s) (simulating rolling summaries)...\n")

    for i, chunk_text in enumerate(chunks_text, 1):
        word_count = len(chunk_text.split())
        print(f"[Chunk {i}/{len(chunks_text)}] Words: {word_count}")
        print(f"Generating chunk summary...")
        summary = summarizer.summarize_chunk(chunk_text)
        summarizer.add_intermediate_summary(summary)
        print(f"Summary: {summary}\n")
        print("-" * 60 + "\n")

    # Generate final summary
    print("Generating final summary...")
    final_summary = summarizer.generate_final_summary(chunks=None)
    print(f"\n{final_summary}\n")

    # Extract structured data
    print("=" * 60)
    print("STRUCTURED DATA EXTRACTION")
    print("=" * 60 + "\n")

    structured_data = summarizer.extract_structured_data(config.data_extraction_prompt)

    print("\nExtracted data:")
    print(json.dumps(structured_data, indent=2))

    # Save outputs
    print("\n" + "=" * 60)
    print("SAVING OUTPUTS")
    print("=" * 60 + "\n")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save summary
    summary_path = output_dir / f"summary_{timestamp}.txt"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(final_summary)
    print(f"✓ Summary saved: {summary_path}")

    # Save JSON
    json_path = output_dir / f"summary_{timestamp}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(structured_data, f, indent=2, ensure_ascii=False)
    print(f"✓ JSON saved: {json_path}")

    # Save to CSV
    csv_path = Path(config.csv_export_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = csv_path.exists()

    # Flatten data for CSV
    meeting_date = datetime.strptime(timestamp, "%Y%m%d_%H%M%S").strftime("%Y-%m-%d")
    meeting_time = datetime.strptime(timestamp, "%Y%m%d_%H%M%S").strftime("%H:%M:%S")

    contacts = structured_data.get('contacts', [])
    companies = structured_data.get('companies', [])
    deals = structured_data.get('deals', [])

    primary_contact = contacts[0] if contacts else {}
    primary_company = companies[0] if companies else {}
    primary_deal = deals[0] if deals else {}

    row = {
        'meeting_date': meeting_date,
        'meeting_time': meeting_time,
        'timestamp_file': timestamp,
        'contact_name': primary_contact.get('name', ''),
        'contact_role': primary_contact.get('role', ''),
        'contact_location': primary_contact.get('location', ''),
        'contact_is_decision_maker': primary_contact.get('is_decision_maker', ''),
        'contact_tenure': primary_contact.get('tenure_duration', ''),
        'company_name': primary_company.get('name', ''),
        'company_aum': primary_company.get('aum', ''),
        'company_icp': primary_company.get('icp_classification', ''),
        'company_location': primary_company.get('location', ''),
        'company_is_client': primary_company.get('is_client', ''),
        'company_competitor_products': ', '.join(primary_company.get('competitor_products', []) or []),
        'company_strategies_of_interest': ', '.join(primary_company.get('strategies_of_interest', []) or []),
        'deal_ticket_size': primary_deal.get('ticket_size', ''),
        'deal_products_of_interest': ', '.join(primary_deal.get('products_of_interest', []) or []),
        'total_contacts': len(contacts),
        'total_companies': len(companies),
        'total_deals': len(deals),
    }

    fieldnames = [
        'meeting_date', 'meeting_time', 'timestamp_file',
        'contact_name', 'contact_role', 'contact_location', 'contact_is_decision_maker', 'contact_tenure',
        'company_name', 'company_aum', 'company_icp', 'company_location', 'company_is_client',
        'company_competitor_products', 'company_strategies_of_interest',
        'deal_ticket_size', 'deal_products_of_interest',
        'total_contacts', 'total_companies', 'total_deals',
    ]

    with open(csv_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

    print(f"✓ CSV updated: {csv_path}")

    print("\n" + "=" * 60)
    print("PROCESSING COMPLETE")
    print("=" * 60)
    print(f"\nOutputs:")
    print(f"  - {summary_path}")
    print(f"  - {json_path}")
    print(f"  - {csv_path}")
    print()

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
    else:
        audio_file = "../first_meeting.mp3"

    process_audio_file(audio_file)
