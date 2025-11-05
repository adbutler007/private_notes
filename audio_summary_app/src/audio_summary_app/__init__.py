"""
Audio Summary App
A privacy-focused desktop application that captures audio, transcribes it in real-time,
and generates intelligent summaries using on-device AI models.
"""

__version__ = "2.0.0"
__author__ = "Adam Butler"

from .config import Config, MODEL_SETUP_INSTRUCTIONS
from .audio_capture import AudioCaptureManager
from .transcriber import StreamingTranscriber
from .transcript_buffer import TranscriptBuffer
from .summarizer import MapReduceSummarizer
from . import ollama_manager

__all__ = [
    "Config",
    "MODEL_SETUP_INSTRUCTIONS",
    "AudioCaptureManager",
    "StreamingTranscriber",
    "TranscriptBuffer",
    "MapReduceSummarizer",
    "ollama_manager",
]
