"""
Main CLI entry point for Audio Summary App
Can be run with: python -m audio_summary_app
"""

import threading
import queue
import time
from datetime import datetime
from pathlib import Path

from .audio_capture import AudioCaptureManager
from .transcript_buffer import TranscriptBuffer
from .summarizer import MapReduceSummarizer
from .transcriber import StreamingTranscriber, ParakeetTranscriber
from .config import Config


class AudioSummaryApp:
    def __init__(self, config: Config):
        self.config = config
        self.is_running = False
        self.is_recording = False

        # Core components
        self.audio_manager = AudioCaptureManager(
            sample_rate=config.sample_rate, channels=config.channels
        )

        self.transcript_buffer = TranscriptBuffer(
            max_buffer_size=config.max_buffer_size, chunk_duration=config.chunk_duration
        )

        self.summarizer = MapReduceSummarizer(
            model_name=config.llm_model_name,
            summary_interval=config.summary_interval,
            chunk_summary_max_tokens=config.chunk_summary_max_tokens,
            final_summary_max_tokens=config.final_summary_max_tokens,
            chunk_summary_prompt=config.chunk_summary_prompt,
            final_summary_prompt=config.final_summary_prompt
        )

        # Select transcription backend based on config
        if config.stt_backend == "parakeet":
            self.transcriber = ParakeetTranscriber(
                model_path=config.parakeet_model_path,
                min_audio_duration=config.stt_min_audio_duration,
                max_audio_duration=config.stt_max_audio_duration,
                sample_rate=config.sample_rate
            )
        else:  # whisper
            self.transcriber = StreamingTranscriber(
                model_path=config.stt_model_path,
                min_audio_duration=config.stt_min_audio_duration,
                max_audio_duration=config.stt_max_audio_duration,
                sample_rate=config.sample_rate
            )

        # Queues for threading
        self.audio_queue = queue.Queue()
        self.transcript_queue = queue.Queue()

        # Threads
        self.threads = []

    def start(self):
        """Start the application and all processing threads"""
        if self.is_running:
            print("App is already running")
            return

        self.is_running = True

        # Start worker threads
        transcription_thread = threading.Thread(
            target=self._transcription_worker, daemon=True
        )
        summary_thread = threading.Thread(target=self._summary_worker, daemon=True)

        transcription_thread.start()
        summary_thread.start()

        self.threads = [transcription_thread, summary_thread]

        print("\nAudio Summary App started.")
        print("Commands: start, stop, quit\n")

    def start_recording(self):
        """Start capturing and processing audio"""
        if self.is_recording:
            print("Already recording")
            return

        self.is_recording = True
        self.audio_manager.start_capture(self.audio_queue)
        self.audio_manager.enable_recording()
        print("Recording started...")

    def stop_recording(self):
        """Stop recording and generate final summary"""
        if not self.is_recording:
            print("Not currently recording")
            return

        print("\nStopping recording...")
        self.is_recording = False

        # Stop audio capture first
        self.audio_manager.disable_recording()
        self.audio_manager.stop_capture()

        # Wait for audio queue to be fully processed by transcription worker
        print("Waiting for transcription to complete...")
        max_wait_time = 60  # Maximum 60 seconds
        wait_start = time.time()

        while not self.audio_queue.empty() and (time.time() - wait_start) < max_wait_time:
            time.sleep(0.5)

        # Flush any remaining audio from transcriber's internal buffer
        # (audio that was accumulated but not yet transcribed)
        remaining_transcript = self.transcriber.flush_buffer()
        if remaining_transcript:
            print(remaining_transcript, end=" ", flush=True)
            self.transcript_queue.put(remaining_transcript)

        # Wait for transcript queue to be fully processed by summary worker
        print("\nWaiting for final transcripts to be added to buffer...")
        wait_start = time.time()

        while not self.transcript_queue.empty() and (time.time() - wait_start) < max_wait_time:
            time.sleep(0.5)

        # Give a final moment for any last processing
        time.sleep(1)

        # Generate final summary
        # IMPORTANT: Only use intermediate summaries (chunk summaries), not raw transcripts
        print("Generating final summary...")

        # If we have no intermediate summaries yet (recording was < 5 minutes),
        # create one from the current buffer
        if not self.summarizer.intermediate_summaries:
            chunks = self.transcript_buffer.get_all_chunks()
            if chunks:
                print("Recording was less than 5 minutes - creating final chunk summary...")
                # Summarize the content that was accumulated
                latest_chunk = chunks[-1]
                summary = self.summarizer.summarize_chunk(latest_chunk["text"])
                self.summarizer.add_intermediate_summary(summary)
                print("Chunk summary created.")
            else:
                print("No content to summarize")
                print("Recording stopped.")
                return

        # Now generate final summary from intermediate summaries
        final_summary = self.summarizer.generate_final_summary(chunks=None)
        summary_path = self._save_summary(final_summary)
        print(f"\nSummary saved to: {summary_path}")

        # Extract structured data from intermediate summaries
        print("\nExtracting structured data...")
        structured_data = self.summarizer.extract_structured_data(
            self.config.data_extraction_prompt
        )
        data_path = self._save_structured_data(structured_data, summary_path)
        print(f"Structured data saved to: {data_path}")

        # Append to CSV file
        self._append_to_csv(structured_data, summary_path)
        print(f"Data appended to CSV: {self.config.csv_export_path}")

        # Clear all data from memory (raw transcripts and chunk summaries)
        self.transcript_buffer.clear()
        self.summarizer.clear_intermediate_summaries()

        print("Recording stopped.")

    def stop(self):
        """Shutdown the application"""
        if self.is_recording:
            self.stop_recording()

        self.is_running = False
        self.audio_manager.stop_capture()

        # Wait for threads to finish
        for thread in self.threads:
            thread.join(timeout=2)

        print("Application stopped.")

    def _transcription_worker(self):
        """Worker thread: Convert audio to text"""
        while self.is_running:
            try:
                # Get audio chunk with timeout
                audio_chunk = self.audio_queue.get(timeout=1)

                # Transcribe
                transcript = self.transcriber.transcribe(audio_chunk)

                if transcript:
                    # Print with space separator for continuous text flow
                    print(transcript, end=" ", flush=True)
                    self.transcript_queue.put(transcript)

            except queue.Empty:
                continue
            except Exception as e:
                print(f"\nTranscription worker error: {e}")

    def _summary_worker(self):
        """Worker thread: Generate rolling summaries"""
        last_summary_time = time.time()

        while self.is_running:
            try:
                # Get transcript with timeout
                transcript = self.transcript_queue.get(timeout=1)

                # Add to buffer
                self.transcript_buffer.add_segment(transcript)

                # Check if it's time for a rolling summary
                current_time = time.time()
                if current_time - last_summary_time >= self.config.summary_interval:
                    chunks = self.transcript_buffer.get_all_chunks()
                    if chunks:
                        print("\n\n" + "="*60)
                        print("ROLLING SUMMARY")
                        print("="*60)
                        # Summarize the most recent chunk
                        latest_chunk = chunks[-1]
                        summary = self.summarizer.summarize_chunk(latest_chunk["text"])
                        self.summarizer.add_intermediate_summary(summary)
                        print(summary)
                        print("="*60 + "\n")

                        # PRIVACY: Clear raw transcripts from memory now that we have the summary
                        # Only the chunk summary is kept, raw transcript is discarded
                        self.transcript_buffer.clear()
                        print("[PRIVACY] Raw transcripts cleared from memory - only chunk summary retained")

                    last_summary_time = current_time

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Summary worker error: {e}")

    def _save_summary(self, summary: str) -> Path:
        """Save summary to file (ONLY time data is written to disk)"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"summary_{timestamp}.txt"
        filepath = output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(summary)

        return filepath

    def _save_structured_data(self, data: dict, summary_path: Path) -> Path:
        """Save structured data to JSON file alongside summary"""
        import json

        # Use the same timestamp as the summary file
        data_path = summary_path.with_suffix('.json')

        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return data_path

    def _append_to_csv(self, data: dict, summary_path: Path):
        """Append structured data to CSV file for tracking all meetings"""
        import csv
        from pathlib import Path

        csv_path = Path(self.config.csv_export_path)
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if file exists to determine if we need to write headers
        file_exists = csv_path.exists()

        # Flatten the structured data into rows
        # Each contact/company/deal combination becomes a row
        rows = []

        # Get meeting metadata
        timestamp = summary_path.stem.replace('summary_', '')
        meeting_date = datetime.strptime(timestamp, "%Y%m%d_%H%M%S").strftime("%Y-%m-%d")
        meeting_time = datetime.strptime(timestamp, "%Y%m%d_%H%M%S").strftime("%H:%M:%S")

        contacts = data.get('contacts', [])
        companies = data.get('companies', [])
        deals = data.get('deals', [])

        # If we have data, create rows
        # Strategy: Create one row per meeting with primary contact/company/deal
        # and additional columns for secondary entries
        if contacts or companies or deals:
            # Get primary (first) entries
            primary_contact = contacts[0] if contacts else {}
            primary_company = companies[0] if companies else {}
            primary_deal = deals[0] if deals else {}

            row = {
                'meeting_date': meeting_date,
                'meeting_time': meeting_time,
                'timestamp_file': timestamp,
                # Contact fields
                'contact_name': primary_contact.get('name', ''),
                'contact_role': primary_contact.get('role', ''),
                'contact_location': primary_contact.get('location', ''),
                'contact_is_decision_maker': primary_contact.get('is_decision_maker', ''),
                'contact_tenure': primary_contact.get('tenure_duration', ''),
                # Company fields
                'company_name': primary_company.get('name', ''),
                'company_aum': primary_company.get('aum', ''),
                'company_icp': primary_company.get('icp_classification', ''),
                'company_location': primary_company.get('location', ''),
                'company_is_client': primary_company.get('is_client', ''),
                'company_competitor_products': ', '.join(primary_company.get('competitor_products', []) or []),
                'company_strategies_of_interest': ', '.join(primary_company.get('strategies_of_interest', []) or []),
                # Deal fields
                'deal_ticket_size': primary_deal.get('ticket_size', ''),
                'deal_products_of_interest': ', '.join(primary_deal.get('products_of_interest', []) or []),
                # Additional info
                'total_contacts': len(contacts),
                'total_companies': len(companies),
                'total_deals': len(deals),
            }
            rows.append(row)
        else:
            # Empty row for meetings with no extracted data
            row = {
                'meeting_date': meeting_date,
                'meeting_time': meeting_time,
                'timestamp_file': timestamp,
                'contact_name': '',
                'contact_role': '',
                'contact_location': '',
                'contact_is_decision_maker': '',
                'contact_tenure': '',
                'company_name': '',
                'company_aum': '',
                'company_icp': '',
                'company_location': '',
                'company_is_client': '',
                'company_competitor_products': '',
                'company_strategies_of_interest': '',
                'deal_ticket_size': '',
                'deal_products_of_interest': '',
                'total_contacts': 0,
                'total_companies': 0,
                'total_deals': 0,
            }
            rows.append(row)

        # Define fieldnames (column headers)
        fieldnames = [
            'meeting_date',
            'meeting_time',
            'timestamp_file',
            'contact_name',
            'contact_role',
            'contact_location',
            'contact_is_decision_maker',
            'contact_tenure',
            'company_name',
            'company_aum',
            'company_icp',
            'company_location',
            'company_is_client',
            'company_competitor_products',
            'company_strategies_of_interest',
            'deal_ticket_size',
            'deal_products_of_interest',
            'total_contacts',
            'total_companies',
            'total_deals',
        ]

        # Write to CSV
        with open(csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            # Write header if file is new
            if not file_exists:
                writer.writeheader()

            # Write rows
            for row in rows:
                writer.writerow(row)


def main():
    """Main entry point for the application"""
    # Initialize configuration
    config = Config()

    print("=" * 60)
    print("Audio Summary App - Privacy-First Transcription & Summary")
    print("=" * 60)
    print(config)
    print("=" * 60)

    # Create and start app
    app = AudioSummaryApp(config)
    app.start()

    # CLI loop
    try:
        while True:
            command = input("> ").strip().lower()

            if command == "start":
                app.start_recording()
            elif command == "stop":
                app.stop_recording()
            elif command in ["quit", "exit", "q"]:
                break
            else:
                print("Unknown command")

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        app.stop()
        print("Goodbye!")


if __name__ == "__main__":
    main()
