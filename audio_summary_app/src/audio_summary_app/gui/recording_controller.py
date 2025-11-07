"""
Recording Controller
Manages audio recording, transcription, and summarization in background thread
Uses the existing architecture from __main__.py
"""

from PyQt6.QtCore import QObject, pyqtSignal, QThread
from pathlib import Path
from datetime import datetime
import json
import csv
import queue
import threading
import time

from ..config import Config
from ..audio_capture import AudioCaptureManager
from ..transcriber import StreamingTranscriber, ParakeetTranscriber
from ..transcript_buffer import TranscriptBuffer
from ..summarizer import MapReduceSummarizer


class RecordingWorker(QObject):
    """Worker that runs recording in a separate thread"""

    finished = pyqtSignal(str)  # Emits summary path when done
    error = pyqtSignal(str)
    status_update = pyqtSignal(str)

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.should_stop = False

        # Initialize components (matching __main__.py architecture)
        self.audio_manager = AudioCaptureManager(
            sample_rate=config.sample_rate,
            channels=config.channels
        )

        self.transcript_buffer = TranscriptBuffer(
            max_buffer_size=config.max_buffer_size,
            chunk_duration=config.chunk_duration
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
                max_audio_duration=config.stt_max_audio_duration
            )
        else:  # whisper
            self.transcriber = StreamingTranscriber(
                model_path=config.stt_model_path,
                min_audio_duration=config.stt_min_audio_duration,
                max_audio_duration=config.stt_max_audio_duration
            )

        # Queues for threading
        self.audio_queue = queue.Queue()
        self.transcript_queue = queue.Queue()

    def run(self):
        """Run the recording session"""
        try:
            self.status_update.emit("Initializing recording...")

            # Start worker threads
            transcription_thread = threading.Thread(
                target=self._transcription_worker, daemon=True
            )
            summary_thread = threading.Thread(
                target=self._summary_worker, daemon=True
            )

            transcription_thread.start()
            summary_thread.start()

            # Start recording
            self.audio_manager.start_capture(self.audio_queue)
            self.audio_manager.enable_recording()
            self.status_update.emit("Recording started")

            # Keep recording until stop is called
            while not self.should_stop:
                time.sleep(0.1)

            # Stop recording
            self.audio_manager.disable_recording()
            self.audio_manager.stop_capture()
            self.status_update.emit("Processing final chunk...")

            # Wait for queues to finish processing
            time.sleep(2)  # Give threads time to finish processing

            # Force finalize the current chunk and summarize it
            # This ensures short meetings (< 5 min) and final chunks are summarized
            final_chunk_text = self.transcript_buffer.force_finalize_chunk()
            if final_chunk_text:
                self.status_update.emit("Summarizing final chunk...")
                chunk_summary = self.summarizer.summarize_chunk(final_chunk_text)
                self.summarizer.add_intermediate_summary(chunk_summary)

            # Generate final summary
            self.status_update.emit("Generating final summary...")
            final_summary = self.summarizer.generate_final_summary()

            # Extract structured data
            self.status_update.emit("Extracting structured data...")
            structured_data = self.summarizer.extract_structured_data(
                self.config.data_extraction_prompt
            )

            # Save outputs with auto-naming
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path(self.config.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate folder name from extracted data
            folder_name = self._generate_folder_name(structured_data, timestamp)
            meeting_folder = output_dir / folder_name
            meeting_folder.mkdir(parents=True, exist_ok=True)

            # Save summary
            summary_path = meeting_folder / "summary.txt"
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(final_summary)

            # Save JSON
            json_path = meeting_folder / "data.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(structured_data, f, indent=2, ensure_ascii=False)

            # Append to CSV
            self._append_to_csv(structured_data, timestamp)

            self.status_update.emit("Complete!")
            self.finished.emit(str(summary_path))

        except Exception as e:
            self.error.emit(str(e))

    def _transcription_worker(self):
        """Worker thread for transcription (from __main__.py)"""
        while not self.should_stop:
            try:
                # Get audio from queue (non-blocking with timeout)
                try:
                    audio_chunk = self.audio_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                # Transcribe
                text = self.transcriber.transcribe(audio_chunk)

                if text:
                    # Add to transcript buffer
                    self.transcript_buffer.add(text)

                    # Check if we should summarize this chunk
                    if self.transcript_buffer.should_summarize():
                        chunk_text = self.transcript_buffer.get_chunk_for_summary()
                        if chunk_text:
                            self.status_update.emit("Creating chunk summary...")
                            chunk_summary = self.summarizer.summarize_chunk(chunk_text)
                            self.summarizer.add_intermediate_summary(chunk_summary)

            except Exception as e:
                if not self.should_stop:
                    print(f"Transcription error: {e}")

    def _summary_worker(self):
        """Worker thread for summarization (placeholder)"""
        while not self.should_stop:
            time.sleep(1)

    def stop(self):
        """Signal the worker to stop"""
        self.should_stop = True

    def _generate_folder_name(self, data: dict, timestamp: str) -> str:
        """
        Generate a meaningful folder name from extracted data
        Format: YYYY-MM-DD Company Name - Contact Name
        Fallback: YYYY-MM-DD Meeting HHMMSS
        """
        import re

        # Get date from timestamp
        date_obj = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
        date_str = date_obj.strftime("%Y-%m-%d")
        time_str = date_obj.strftime("%H%M%S")

        # Extract company and contact
        contacts = data.get('contacts', [])
        companies = data.get('companies', [])

        company_name = ""
        contact_name = ""

        if companies and companies[0].get('name'):
            company_name = companies[0]['name']

        if contacts and contacts[0].get('name'):
            contact_name = contacts[0]['name']

        # Sanitize names (remove invalid characters for folder names)
        def sanitize(name):
            # Remove or replace invalid characters
            name = re.sub(r'[<>:"/\\|?*]', '', name)
            # Replace multiple spaces with single space
            name = re.sub(r'\s+', ' ', name)
            # Trim
            return name.strip()

        # Build folder name
        if company_name and contact_name:
            folder_name = f"{date_str} {sanitize(company_name)} - {sanitize(contact_name)}"
        elif company_name:
            folder_name = f"{date_str} {sanitize(company_name)}"
        elif contact_name:
            folder_name = f"{date_str} {sanitize(contact_name)}"
        else:
            folder_name = f"{date_str} Meeting {time_str}"

        return folder_name

    def _append_to_csv(self, data: dict, timestamp: str):
        """Append structured data to CSV file"""
        csv_path = Path(self.config.csv_export_path)
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        file_exists = csv_path.exists()

        # Flatten data
        meeting_date = datetime.strptime(timestamp, "%Y%m%d_%H%M%S").strftime("%Y-%m-%d")
        meeting_time = datetime.strptime(timestamp, "%Y%m%d_%H%M%S").strftime("%H:%M:%S")

        contacts = data.get('contacts', [])
        companies = data.get('companies', [])
        deals = data.get('deals', [])

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

        fieldnames = list(row.keys())

        with open(csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)


class RecordingController(QObject):
    """
    Controls recording sessions
    Manages worker thread and signals
    """

    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    summary_ready = pyqtSignal(str)  # Emits path to summary
    error = pyqtSignal(str)
    status_update = pyqtSignal(str)

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.is_recording = False
        self.worker = None
        self.thread = None

    def start_recording(self):
        """Start a recording session"""
        if self.is_recording:
            return

        self.is_recording = True

        # Create worker and thread
        self.worker = RecordingWorker(self.config)
        self.thread = QThread()
        self.worker.moveToThread(self.thread)

        # Connect signals
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_recording_finished)
        self.worker.error.connect(self.on_error)
        self.worker.status_update.connect(self.status_update.emit)

        # Start thread
        self.thread.start()
        self.recording_started.emit()

    def stop_recording(self):
        """Stop the current recording session"""
        if not self.is_recording or self.worker is None:
            return

        # Signal worker to stop
        self.worker.stop()

    def on_recording_finished(self, summary_path: str):
        """Called when recording finishes"""
        self.is_recording = False

        # Cleanup thread
        if self.thread:
            self.thread.quit()
            self.thread.wait()
            self.thread = None
        self.worker = None

        self.recording_stopped.emit()
        self.summary_ready.emit(summary_path)

    def on_error(self, error_msg: str):
        """Called when an error occurs"""
        self.is_recording = False

        # Cleanup thread
        if self.thread:
            self.thread.quit()
            self.thread.wait()
            self.thread = None
        self.worker = None

        self.recording_stopped.emit()
        self.error.emit(error_msg)
