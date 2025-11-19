"""
Session Manager for Audio Summary Engine

Manages active transcription sessions with per-session state:
- STT backend (Whisper or Parakeet)
- Transcript buffer
- MapReduce summarizer
- Configuration

Per spec §FR6, §FR7: Sessions are created via /start_session and tracked until /stop_session.
Only one concurrent session is allowed by default (spec §4.2, /start_session).
"""

import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass, field

import numpy as np

from ..transcriber import StreamingTranscriber, ParakeetTranscriber
from ..transcript_buffer import TranscriptBuffer
from ..summarizer import MapReduceSummarizer
from ..config import Config


class SessionError(Exception):
    """Raised when session operations fail"""

    pass


class SessionNotFoundError(SessionError):
    """Raised when session ID is not found"""

    pass


class SessionAlreadyActiveError(SessionError):
    """Raised when trying to create a session while one is already active"""

    pass


@dataclass
class SessionConfig:
    """Per-session configuration"""

    session_id: str
    stt_backend: str  # "whisper" or "parakeet"
    stt_model_path: str  # Model path/repo
    capture_sample_rate: int  # Incoming audio sample rate
    llm_model_name: str
    chunk_summary_prompt: str
    final_summary_prompt: str
    data_extraction_prompt: str
    output_dir: str
    csv_export_path: str
    append_csv: bool
    chunk_duration: int  # Seconds per chunk for map-reduce
    chunk_summary_max_tokens: int
    final_summary_max_tokens: int
    min_audio_duration: float  # STT buffer minimum
    max_audio_duration: float  # STT buffer maximum


@dataclass
class Session:
    """Active transcription session"""

    config: SessionConfig
    transcriber: Any  # StreamingTranscriber or ParakeetTranscriber
    transcript_buffer: TranscriptBuffer
    summarizer: MapReduceSummarizer
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "active"  # "active", "stopped", "processing"
    audio_chunks_received: int = 0
    total_audio_duration: float = 0.0

    def add_audio_chunk(self, audio_data: np.ndarray, timestamp: float, sample_rate: int) -> str:
        """
        Add audio chunk to session and transcribe

        Args:
            audio_data: Numpy array of float32 mono PCM
            timestamp: Timestamp of chunk
            sample_rate: Sample rate of chunk

        Returns:
            Transcribed text (may be empty if buffering)
        """
        # Create audio chunk dict for transcriber
        audio_chunk = {
            'data': audio_data,
            'source': 'capture',  # From ScreenCaptureKit or mic
            'timestamp': timestamp,
            'sample_rate': sample_rate
        }

        # Track metrics
        self.audio_chunks_received += 1
        chunk_duration = len(audio_data) / float(sample_rate)
        self.total_audio_duration += chunk_duration

        # Transcribe (may buffer and return empty string)
        transcript = self.transcriber.transcribe(audio_chunk)

        if transcript:
            # Add to transcript buffer
            self.transcript_buffer.add(transcript, source='capture')

            # Check if we should summarize this chunk
            if self.transcript_buffer.should_summarize():
                chunk_text = self.transcript_buffer.get_chunk_for_summary()
                if chunk_text:
                    # MAP phase: Summarize this chunk
                    chunk_summary = self.summarizer.summarize_chunk(chunk_text)
                    if chunk_summary:
                        self.summarizer.add_intermediate_summary(chunk_summary)

        return transcript


class SessionManager:
    """
    Manages active transcription sessions

    Per spec §4.2: Only one concurrent session is allowed by default.
    """

    def __init__(self, runtime_mode: str = "prod", allow_concurrent: bool = False):
        """
        Args:
            runtime_mode: "prod" or "dev" (per spec §4.2.3)
                         In "prod" mode, mock backends are not allowed
            allow_concurrent: If True, allow multiple concurrent sessions
        """
        self.runtime_mode = runtime_mode
        self.allow_concurrent = allow_concurrent
        self.sessions: Dict[str, Session] = {}
        self.lock = threading.Lock()

        print(f"[SessionManager] Runtime mode: {runtime_mode}")
        if allow_concurrent:
            print("[SessionManager] Concurrent sessions: ENABLED")
        else:
            print("[SessionManager] Concurrent sessions: DISABLED (single session only)")

    def create_session(self, session_config: SessionConfig) -> Session:
        """
        Create a new transcription session

        Per spec §4.2 /start_session:
        - If another session is active and concurrent sessions are not allowed, raise SessionAlreadyActiveError
        - Initialize STT backend via factory
        - Initialize TranscriptBuffer
        - Initialize MapReduceSummarizer with prompts

        Args:
            session_config: Configuration for the session

        Returns:
            Created session

        Raises:
            SessionAlreadyActiveError: If a session is already active (when allow_concurrent=False)
            SessionError: If session creation fails
        """
        with self.lock:
            # Check for existing active sessions
            if not self.allow_concurrent:
                active_sessions = [s for s in self.sessions.values() if s.status == "active"]
                if active_sessions:
                    raise SessionAlreadyActiveError(
                        f"Session already active: {active_sessions[0].config.session_id}"
                    )

            # Check if session ID already exists
            if session_config.session_id in self.sessions:
                raise SessionError(
                    f"Session ID {session_config.session_id} already exists"
                )

            # Create STT backend via factory
            transcriber = self._create_transcriber(session_config)

            # Create transcript buffer
            transcript_buffer = TranscriptBuffer(
                max_buffer_size=2000,  # From Config
                chunk_duration=session_config.chunk_duration
            )

            # Create summarizer
            summarizer = MapReduceSummarizer(
                model_name=session_config.llm_model_name,
                summary_interval=session_config.chunk_duration,
                chunk_summary_max_tokens=session_config.chunk_summary_max_tokens,
                final_summary_max_tokens=session_config.final_summary_max_tokens,
                chunk_summary_prompt=session_config.chunk_summary_prompt,
                final_summary_prompt=session_config.final_summary_prompt
            )

            # Create session
            session = Session(
                config=session_config,
                transcriber=transcriber,
                transcript_buffer=transcript_buffer,
                summarizer=summarizer
            )

            # Store session
            self.sessions[session_config.session_id] = session

            print(f"[SessionManager] Created session {session_config.session_id}")
            print(f"  STT backend: {session_config.stt_backend}")
            print(f"  Model: {session_config.stt_model_path}")
            print(f"  Capture rate: {session_config.capture_sample_rate} Hz")
            print(f"  LLM: {session_config.llm_model_name}")

            return session

    def _create_transcriber(self, config: SessionConfig):
        """
        Create STT backend via factory

        Per spec §4.2.3: Create transcriber based on backend selection
        In "prod" mode, mock backends are not allowed

        Args:
            config: Session configuration

        Returns:
            Transcriber instance (StreamingTranscriber or ParakeetTranscriber)

        Raises:
            SessionError: If backend is invalid or unavailable
        """
        backend = config.stt_backend.lower()

        if backend == "whisper":
            transcriber = StreamingTranscriber(
                model_path=config.stt_model_path,
                min_audio_duration=config.min_audio_duration,
                max_audio_duration=config.max_audio_duration,
                capture_sample_rate=config.capture_sample_rate
            )

            # In prod mode, check if using mock
            if self.runtime_mode == "prod" and transcriber.use_mock:
                raise SessionError(
                    "STT_BACKEND_UNAVAILABLE: MLX Whisper is not available and mock backends are not allowed in production mode"
                )

        elif backend == "parakeet":
            transcriber = ParakeetTranscriber(
                model_path=config.stt_model_path,
                min_audio_duration=config.min_audio_duration,
                max_audio_duration=config.max_audio_duration,
                capture_sample_rate=config.capture_sample_rate
            )

            # In prod mode, check if using mock
            if self.runtime_mode == "prod" and transcriber.use_mock:
                raise SessionError(
                    "STT_BACKEND_UNAVAILABLE: Parakeet MLX is not available and mock backends are not allowed in production mode"
                )

        else:
            raise SessionError(
                f"Invalid STT backend: {backend}. Must be 'whisper' or 'parakeet'"
            )

        return transcriber

    def get_session(self, session_id: str) -> Session:
        """
        Get session by ID

        Args:
            session_id: Session ID

        Returns:
            Session

        Raises:
            SessionNotFoundError: If session not found
        """
        with self.lock:
            session = self.sessions.get(session_id)
            if not session:
                raise SessionNotFoundError(f"Session {session_id} not found")
            return session

    def stop_session(self, session_id: str) -> Dict[str, Any]:
        """
        Stop session and generate final summary

        Per spec §4.2 /stop_session:
        1. Flush transcriber buffer
        2. Force finalize current chunk
        3. Check for low content
        4. Generate final summary
        5. Extract structured data
        6. Write files
        7. Append to CSV

        Args:
            session_id: Session ID

        Returns:
            Dictionary with summary_path, data_path, csv_path, session_status

        Raises:
            SessionNotFoundError: If session not found
        """
        session = self.get_session(session_id)

        with self.lock:
            if session.status == "stopped":
                # Idempotent: already stopped
                return {
                    "status": "already_stopped",
                    "summary_path": None,
                    "data_path": None,
                    "csv_path": None,
                    "session_status": "stopped"
                }

            # Mark as processing
            session.status = "processing"

        print(f"[SessionManager] Stopping session {session_id}")

        # 1. Flush transcriber buffer
        final_transcript = session.transcriber.flush_buffer()
        if final_transcript:
            session.transcript_buffer.add(final_transcript, source='capture')

        # 2. Force finalize current chunk
        final_chunk_text = session.transcript_buffer.force_finalize_chunk()
        if final_chunk_text:
            chunk_summary = session.summarizer.summarize_chunk(final_chunk_text)
            if chunk_summary:
                session.summarizer.add_intermediate_summary(chunk_summary)

        # 3. Check for low content
        session_status = "completed"
        if not session.summarizer.intermediate_summaries:
            # Low content analysis
            full_transcript = session.transcript_buffer.get_full_transcript()
            word_count = len(full_transcript.split())
            char_count = len(full_transcript)

            if char_count < 50 or word_count < 10:
                session_status = "insufficient_content"
                final_summary = "No usable call audio was captured from the target app. Please check your capture configuration."
                structured_data = {"contacts": [], "companies": [], "deals": []}
            else:
                # Has some content but no intermediate summaries - create one from full transcript
                chunk_summary = session.summarizer.summarize_chunk(full_transcript)
                if chunk_summary:
                    session.summarizer.add_intermediate_summary(chunk_summary)
                final_summary = session.summarizer.generate_final_summary()
                structured_data = session.summarizer.extract_structured_data(
                    session.config.data_extraction_prompt
                )
        else:
            # 4. Generate final summary
            final_summary = session.summarizer.generate_final_summary()

            # 5. Extract structured data
            structured_data = session.summarizer.extract_structured_data(
                session.config.data_extraction_prompt
            )

        # 6. Write files
        output_dir = Path(session.config.output_dir).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_path = output_dir / f"summary_{timestamp}.txt"
        data_path = output_dir / f"data_{timestamp}.json"

        # Write summary
        summary_path.write_text(final_summary)
        print(f"[SessionManager] Wrote summary: {summary_path}")

        # Write structured data
        import json
        data_path.write_text(json.dumps(structured_data, indent=2))
        print(f"[SessionManager] Wrote data: {data_path}")

        # 7. Append to CSV (if enabled)
        csv_path = None
        if session.config.append_csv:
            csv_path = self._append_to_csv(session, structured_data, timestamp)

        # Mark as stopped
        with self.lock:
            session.status = "stopped"

        return {
            "status": "ok",
            "summary_path": str(summary_path),
            "data_path": str(data_path),
            "csv_path": str(csv_path) if csv_path else None,
            "session_status": session_status
        }

    def _append_to_csv(self, session: Session, structured_data: Dict, timestamp: str) -> Optional[Path]:
        """Append session data to CSV export file"""
        import csv

        csv_path = Path(session.config.csv_export_path).expanduser()
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if file exists to determine if we need headers
        file_exists = csv_path.exists()

        try:
            with open(csv_path, 'a', newline='') as f:
                # Flatten structured data for CSV
                row = {
                    'timestamp': timestamp,
                    'session_id': session.config.session_id,
                    'duration_seconds': session.total_audio_duration,
                    'audio_chunks': session.audio_chunks_received,
                }

                # Add first contact/company/deal if available
                if structured_data.get('contacts'):
                    contact = structured_data['contacts'][0]
                    row['contact_name'] = contact.get('name')
                    row['contact_role'] = contact.get('role')

                if structured_data.get('companies'):
                    company = structured_data['companies'][0]
                    row['company_name'] = company.get('name')
                    row['company_aum'] = company.get('aum')

                if structured_data.get('deals'):
                    deal = structured_data['deals'][0]
                    row['ticket_size'] = deal.get('ticket_size')

                writer = csv.DictWriter(f, fieldnames=row.keys())
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)

            print(f"[SessionManager] Appended to CSV: {csv_path}")
            return csv_path

        except Exception as e:
            print(f"[SessionManager] Failed to write CSV: {e}")
            return None

    def list_sessions(self) -> Dict[str, str]:
        """
        List all sessions and their status

        Returns:
            Dictionary mapping session_id to status
        """
        with self.lock:
            return {sid: s.status for sid, s in self.sessions.items()}

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """
        Get statistics for a session

        Args:
            session_id: Session ID

        Returns:
            Dictionary with session statistics
        """
        session = self.get_session(session_id)

        with self.lock:
            buffer_stats = session.transcript_buffer.get_buffer_stats()

            return {
                'session_id': session_id,
                'status': session.status,
                'created_at': session.created_at.isoformat(),
                'audio_chunks_received': session.audio_chunks_received,
                'total_audio_duration': session.total_audio_duration,
                'buffer_stats': buffer_stats,
                'intermediate_summaries': len(session.summarizer.intermediate_summaries)
            }
