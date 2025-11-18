"""
Streaming Transcriber
Converts audio to text using on-device speech-to-text model
Uses MLX Whisper or Parakeet MLX for optimized Apple Silicon inference
Audio is processed but never saved
"""

import numpy as np
from typing import Dict, Optional
import threading
import mlx_whisper


class StreamingTranscriber:
    """
    Real-time speech-to-text transcription using local models
    Supports both input (mic) and output (system audio) transcription
    """
    
    def __init__(self, model_path: str = "base.en", min_audio_duration: float = 2.0, max_audio_duration: float = 10.0, capture_sample_rate: int = 16000):
        """
        Args:
            model_path: Whisper model size (tiny, base, small, medium, large, large-v2, large-v3)
                       MLX Whisper will automatically optimize for Apple Silicon
            min_audio_duration: Minimum seconds of audio to accumulate before transcribing
            max_audio_duration: Maximum seconds to accumulate (prevents excessive latency)
            capture_sample_rate: Sample rate of incoming audio (will be resampled if needed)
        """
        # Convert standard model names to MLX community format
        # Available models: tiny, small-mlx, medium-mlx, large-v3-mlx, large-v3-turbo
        model_mapping = {
            "tiny": "mlx-community/whisper-tiny",
            "base": "mlx-community/whisper-tiny",  # Base -> tiny (base not available in MLX)
            "small": "mlx-community/whisper-small-mlx",
            "medium": "mlx-community/whisper-medium-mlx",
            "large": "mlx-community/whisper-large-v3-mlx",
            "large-v2": "mlx-community/whisper-large-v3-mlx",
            "large-v3": "mlx-community/whisper-large-v3-mlx",
            "large-v3-turbo": "mlx-community/whisper-large-v3-turbo",  # Faster variant
            "turbo": "mlx-community/whisper-large-v3-turbo",
        }

        # Handle .en suffixes (e.g., "base.en" -> "base")
        model_key = model_path.split('.')[0] if '.' in model_path else model_path

        # Get the MLX model repo
        if model_key in model_mapping:
            self.model_repo = model_mapping[model_key]
        else:
            # If not in mapping, assume it's already a full repo path
            self.model_repo = model_path

        # Lock for thread safety
        self.lock = threading.Lock()

        # Audio buffer for accumulating small chunks
        self.audio_buffer = []
        self.buffer_duration = 0.0
        # Use provided durations (defaults from config)
        # Whisper performs better with longer audio segments (2-5 seconds)
        self.min_audio_duration = min_audio_duration
        self.max_audio_duration = max_audio_duration
        self.sample_rate = capture_sample_rate  # Use capture rate for duration calcs

        # Test that MLX Whisper is available
        self.use_mock = not self._test_mlx_available()

        if not self.use_mock:
            print(f"[STT] Using MLX Whisper model: {self.model_repo}")
            print("[STT] Optimized for Apple Silicon (M-series chips)")
            print("[STT] Using on-device transcription (no data sent to cloud)")
        
    def _test_mlx_available(self):
        """
        Test if MLX Whisper is available and working
        """
        try:
            import mlx_whisper
            return True
        except Exception as e:
            print(f"[STT] MLX Whisper not available: {e}")
            print(f"[STT] Falling back to mock model for testing")
            return False
        
    def transcribe(self, audio_chunk: Dict) -> str:
        """
        Transcribe an audio chunk to text
        
        Args:
            audio_chunk: Dictionary containing audio data and metadata
                {
                    'data': numpy array of audio samples,
                    'source': 'input' or 'output',
                    'timestamp': timestamp
                }
                
        Returns:
            Transcribed text (empty string if no speech detected)
        """
        with self.lock:
            audio_data = audio_chunk['data']
            
            # Add to buffer
            self.audio_buffer.append(audio_data)

            # Calculate duration based on configured sample rate
            chunk_duration = len(audio_data) / float(self.sample_rate)
            self.buffer_duration += chunk_duration

            # Only transcribe if we have enough audio (but not too much)
            # - Min: 3 seconds (gives Whisper better context, reduces word cutoffs)
            # - Max: 10 seconds (prevents excessive latency)
            if self.buffer_duration < self.min_audio_duration:
                # Debug: Show we're accumulating audio
                if len(self.audio_buffer) == 1:  # First chunk
                    max_amp = np.max(np.abs(audio_data)) if len(audio_data) > 0 else 0
                    print(f"[STT] Accumulating audio... (buffer: {self.buffer_duration:.2f}s/{self.min_audio_duration:.0f}s, amplitude: {max_amp:.4f})", end="\r", flush=True)
                return ""

            # If we've accumulated too much, force transcription to avoid excessive latency
            if self.buffer_duration > self.max_audio_duration:
                print(f"\n[STT] Max buffer reached ({self.buffer_duration:.1f}s), transcribing now...", end="", flush=True)
                
            # Concatenate buffer
            full_audio = np.concatenate(self.audio_buffer, axis=0)

            # Flatten if needed (convert from (N, 1) to (N,))
            if full_audio.ndim > 1:
                full_audio = full_audio.flatten()

            # Debug: Show we're transcribing
            max_amp = np.max(np.abs(full_audio)) if len(full_audio) > 0 else 0
            print(f"\n[STT] Transcribing {self.buffer_duration:.2f}s (amplitude: {max_amp:.4f})...", end="", flush=True)
                
            try:
                # Transcribe the audio
                # NOTE: Audio is processed but never saved to disk

                # Check if using mock model
                if self.use_mock:
                    mock = MockWhisperModel("")
                    segments = mock.transcribe(full_audio)
                    transcript = " ".join(segment['text'] for segment in segments)
                else:
                    # MLX Whisper transcription
                    # Ensure audio is float32 and in [-1, 1] range
                    audio_float = full_audio.astype(np.float32)
                    if audio_float.max() > 1.0 or audio_float.min() < -1.0:
                        audio_float = audio_float / np.abs(audio_float).max()

                    # Transcribe with MLX Whisper
                    # MLX Whisper will download the model on first use
                    result = mlx_whisper.transcribe(
                        audio_float,
                        path_or_hf_repo=self.model_repo
                    )
                    transcript = result['text']

                # Clear buffer (audio discarded from memory, never saved)
                self.audio_buffer.clear()
                self.buffer_duration = 0.0

                return transcript.strip()

            except Exception as e:
                print(f"[STT] Transcription error: {e}")
                # Clear buffer on error
                self.audio_buffer.clear()
                self.buffer_duration = 0.0
                return ""

    def flush_buffer(self) -> str:
        """
        Flush any remaining audio in the buffer and transcribe it.
        Called when stopping recording to ensure no audio is lost.

        Returns:
            Transcribed text from remaining buffer (empty string if buffer is empty)
        """
        with self.lock:
            # If there's no audio in buffer, return empty
            if not self.audio_buffer or self.buffer_duration == 0:
                return ""

            print(f"\n[STT] Flushing remaining {self.buffer_duration:.2f}s from buffer...", end="", flush=True)

            # Concatenate buffer
            full_audio = np.concatenate(self.audio_buffer, axis=0)

            # Flatten if needed
            if full_audio.ndim > 1:
                full_audio = full_audio.flatten()

            try:
                # Check if using mock model
                if self.use_mock:
                    mock = MockWhisperModel("")
                    segments = mock.transcribe(full_audio)
                    transcript = " ".join(segment['text'] for segment in segments)
                else:
                    # MLX Whisper transcription
                    audio_float = full_audio.astype(np.float32)
                    if audio_float.max() > 1.0 or audio_float.min() < -1.0:
                        audio_float = audio_float / np.abs(audio_float).max()

                    result = mlx_whisper.transcribe(
                        audio_float,
                        path_or_hf_repo=self.model_repo
                    )
                    transcript = result['text']

                # Clear buffer
                self.audio_buffer.clear()
                self.buffer_duration = 0.0

                return transcript.strip()

            except Exception as e:
                print(f"\n[STT] Error flushing buffer: {e}")
                self.audio_buffer.clear()
                self.buffer_duration = 0.0
                return ""

    def transcribe_file(self, audio_path: str) -> str:
        """
        Transcribe a complete audio file (for testing/debugging only)
        Not used in main streaming application
        """
        # This would load and transcribe an entire file
        # Kept separate from streaming to show the distinction
        raise NotImplementedError("File transcription not used in streaming app")


class MockWhisperModel:
    """
    Mock Whisper model for prototype demonstration
    Replace with actual faster-whisper in production
    """
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.sample_transcripts = [
            "Let me check the documentation for that.",
            "I think we should prioritize the backend work first.",
            "The deadline is next Friday, so we have about a week.",
            "Can you send me the link to that repository?",
            "I'll follow up with the team later today.",
            "That sounds like a good approach to solve the problem.",
            "We need to consider the performance implications.",
            "Let's schedule a meeting to discuss this further.",
            "I agree with your assessment of the situation.",
            "Could you clarify what you mean by that?"
        ]
        self.counter = 0
        
    def transcribe(self, audio: np.ndarray) -> list:
        """
        Simulate transcription
        In production, this would call the actual Whisper model
        """
        import time
        
        # Simulate processing time
        time.sleep(0.3)
        
        # Return mock transcript
        transcript = self.sample_transcripts[self.counter % len(self.sample_transcripts)]
        self.counter += 1
        
        return [{'text': transcript}]


# Note: The StreamingTranscriber now uses MLX Whisper by default
# Optimized for Apple Silicon (M-series chips) - 3-5x faster than PyTorch Whisper
# The model will auto-download on first use and is cached locally
# Supports: tiny, base, small, medium, large, large-v2, large-v3
# Recommended: large for M4 Mac with 32GB RAM (best accuracy with fast performance)


class ParakeetTranscriber:
    """
    Real-time speech-to-text transcription using NVIDIA Parakeet TDT models
    Optimized for Apple Silicon using MLX framework
    ~2x faster than Whisper with better accuracy (6.05% WER)
    Supports both input (mic) and output (system audio) transcription
    """

    def __init__(self, model_path: str = "mlx-community/parakeet-tdt-0.6b-v3", min_audio_duration: float = 2.0, max_audio_duration: float = 10.0, sample_rate: int = 16000):
        """
        Args:
            model_path: Parakeet model repo (default: mlx-community/parakeet-tdt-0.6b-v3)
                       Available models:
                       - mlx-community/parakeet-tdt-0.6b-v2 (600M params, industry-leading accuracy)
                       - mlx-community/parakeet-tdt-0.6b-v3 (600M params, latest version)
            min_audio_duration: Minimum seconds of audio to accumulate before transcribing
            max_audio_duration: Maximum seconds to accumulate (prevents excessive latency)
        """
        self.model_path = model_path

        # Lock for thread safety
        self.lock = threading.Lock()

        # Audio buffer for accumulating small chunks
        self.audio_buffer = []
        self.buffer_duration = 0.0
        self.min_audio_duration = min_audio_duration
        self.max_audio_duration = max_audio_duration
        self.sample_rate = sample_rate

        # Test that Parakeet MLX is available
        self.use_mock = not self._test_parakeet_available()

        # Lazy-load the model on first use
        self.model = None
        self.streaming_context = None

        if not self.use_mock:
            print(f"[STT] Using Parakeet MLX model: {self.model_path}")
            print("[STT] NVIDIA Parakeet TDT - ~2x faster than Whisper")
            print("[STT] Optimized for Apple Silicon (M-series chips)")
            print("[STT] Using on-device transcription (no data sent to cloud)")

    def _test_parakeet_available(self):
        """
        Test if Parakeet MLX is available and working
        """
        try:
            from parakeet_mlx import from_pretrained
            return True
        except Exception as e:
            print(f"[STT] Parakeet MLX not available: {e}")
            print(f"[STT] Falling back to mock model for testing")
            return False

    def _load_model(self):
        """
        Lazy-load the Parakeet model on first use
        """
        if self.model is None and not self.use_mock:
            print(f"[STT] Loading Parakeet model: {self.model_path}")
            from parakeet_mlx import from_pretrained
            self.model = from_pretrained(self.model_path)
            # Create streaming context for real-time transcription
            # context_size: (left_context, right_context) in number of frames
            # 256 frames ≈ 5 seconds of context
            self.streaming_context = self.model.transcribe_stream(context_size=(256, 256))
            self.streaming_context.__enter__()  # Start streaming context
            print("[STT] Model loaded successfully (streaming mode enabled)")

    def transcribe(self, audio_chunk: Dict) -> str:
        """
        Transcribe an audio chunk to text

        Args:
            audio_chunk: Dictionary containing audio data and metadata
                {
                    'data': numpy array of audio samples,
                    'source': 'input' or 'output',
                    'timestamp': timestamp
                }

        Returns:
            Transcribed text (empty string if no speech detected)
        """
        with self.lock:
            audio_data = audio_chunk['data']

            # Add to buffer
            self.audio_buffer.append(audio_data)

            # Calculate duration based on configured sample rate
            chunk_duration = len(audio_data) / float(self.sample_rate)
            self.buffer_duration += chunk_duration

            # Only transcribe if we have enough audio
            if self.buffer_duration < self.min_audio_duration:
                if len(self.audio_buffer) == 1:  # First chunk
                    max_amp = np.max(np.abs(audio_data)) if len(audio_data) > 0 else 0
                    print(f"[STT] Accumulating audio... (buffer: {self.buffer_duration:.2f}s/{self.min_audio_duration:.0f}s, amplitude: {max_amp:.4f})", end="\r", flush=True)
                return ""

            # If we've accumulated too much, force transcription
            if self.buffer_duration > self.max_audio_duration:
                print(f"\n[STT] Max buffer reached ({self.buffer_duration:.1f}s), transcribing now...", end="", flush=True)

            # Concatenate buffer
            full_audio = np.concatenate(self.audio_buffer, axis=0)

            # Flatten if needed
            if full_audio.ndim > 1:
                full_audio = full_audio.flatten()

            # Debug: Show we're transcribing
            max_amp = np.max(np.abs(full_audio)) if len(full_audio) > 0 else 0
            print(f"\n[STT] Transcribing {self.buffer_duration:.2f}s (amplitude: {max_amp:.4f})...", end="", flush=True)

            try:
                # Check if using mock model
                if self.use_mock:
                    mock = MockWhisperModel("")
                    segments = mock.transcribe(full_audio)
                    transcript = " ".join(segment['text'] for segment in segments)
                else:
                    # Lazy-load model
                    self._load_model()

                    # Parakeet MLX streaming transcription
                    # Ensure audio is float32 and in [-1, 1] range
                    audio_float = full_audio.astype(np.float32)
                    if audio_float.max() > 1.0 or audio_float.min() < -1.0:
                        audio_float = audio_float / np.abs(audio_float).max()

                    # Convert numpy array to MLX array for Parakeet
                    import mlx.core as mx
                    audio_mlx = mx.array(audio_float)

                    # Add audio to streaming context
                    self.streaming_context.add_audio(audio_mlx)
                    # Get current transcription result
                    result = self.streaming_context.result
                    transcript = result.text

                # Clear buffer
                self.audio_buffer.clear()
                self.buffer_duration = 0.0

                return transcript.strip()

            except Exception as e:
                print(f"[STT] Transcription error: {e}")
                # Clear buffer on error
                self.audio_buffer.clear()
                self.buffer_duration = 0.0
                return ""

    def flush_buffer(self) -> str:
        """
        Flush any remaining audio in the buffer and transcribe it.
        Called when stopping recording to ensure no audio is lost.

        Returns:
            Transcribed text from remaining buffer (empty string if buffer is empty)
        """
        with self.lock:
            # If there's no audio in buffer, return empty
            if not self.audio_buffer or self.buffer_duration == 0:
                return ""

            print(f"\n[STT] Flushing remaining {self.buffer_duration:.2f}s from buffer...", end="", flush=True)

            # Concatenate buffer
            full_audio = np.concatenate(self.audio_buffer, axis=0)

            # Flatten if needed
            if full_audio.ndim > 1:
                full_audio = full_audio.flatten()

            try:
                # Check if using mock model
                if self.use_mock:
                    mock = MockWhisperModel("")
                    segments = mock.transcribe(full_audio)
                    transcript = " ".join(segment['text'] for segment in segments)
                else:
                    # Lazy-load model
                    self._load_model()

                    # Parakeet MLX streaming transcription
                    audio_float = full_audio.astype(np.float32)
                    if audio_float.max() > 1.0 or audio_float.min() < -1.0:
                        audio_float = audio_float / np.abs(audio_float).max()

                    # Convert numpy array to MLX array for Parakeet
                    import mlx.core as mx
                    audio_mlx = mx.array(audio_float)

                    # Add remaining audio to streaming context
                    self.streaming_context.add_audio(audio_mlx)
                    # Get final transcription result
                    result = self.streaming_context.result
                    transcript = result.text

                # Clear buffer
                self.audio_buffer.clear()
                self.buffer_duration = 0.0

                return transcript.strip()

            except Exception as e:
                print(f"\n[STT] Error flushing buffer: {e}")
                self.audio_buffer.clear()
                self.buffer_duration = 0.0
                return ""

    def transcribe_file(self, audio_path: str) -> str:
        """
        Transcribe a complete audio file (for testing/debugging only)
        Not used in main streaming application
        """
        raise NotImplementedError("File transcription not used in streaming app")
