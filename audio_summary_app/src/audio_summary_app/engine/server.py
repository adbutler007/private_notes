"""
Audio Summary Engine - HTTP API Server

FastAPI-based HTTP server implementing the engine API per spec §4.2 (FR7).

Endpoints:
- GET /health - Health check with version info
- POST /start_session - Create new transcription session
- POST /audio_chunk - Add audio chunk to active session
- POST /stop_session - Stop session and generate summary

Security per spec NFR2:
- Binds only to 127.0.0.1
- Optional engine auth token via X-Engine-Token header
- No raw audio or transcripts in production logs

Error handling per spec §4.2.1:
- HTTP status codes: 200, 400, 401, 404, 409, 429, 500
- Unified error JSON structure with error_code
"""

import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List

import numpy as np
from fastapi import FastAPI, HTTPException, Header, Request, status, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from . import __version__, __api_version__
from .audio_utils import (
    decode_pcm_from_base64,
    validate_sample_rate,
    AudioFormatError
)
from .session_manager import (
    SessionManager,
    SessionConfig,
    SessionNotFoundError,
    SessionAlreadyActiveError,
    SessionError
)
from ..config import Config

# Configure logging
# Per spec NFR4: Log session metadata but not transcripts in production
logger = logging.getLogger("audio_summary_engine")


# Pydantic models for request/response validation

class HealthResponse(BaseModel):
    """Response for GET /health"""
    status: str = "ok"
    engine_version: str
    api_version: str
    stt_backends: List[str]
    llm_models: List[str]


class UserSettings(BaseModel):
    """User settings for session configuration"""
    chunk_summary_prompt: str
    final_summary_prompt: str
    data_extraction_prompt: Optional[str] = None
    llm_model_name: str = "qwen3:4b-instruct"
    output_dir: str = "~/Documents/Meeting Summaries"
    csv_export_path: str = "~/Documents/Meeting Summaries/meetings.csv"
    append_csv: bool = True


class StartSessionRequest(BaseModel):
    """Request body for POST /start_session"""
    session_id: str = Field(..., min_length=1)
    model: str = Field(..., pattern="^(whisper|parakeet)$")
    sample_rate: int = Field(..., gt=0)
    user_settings: UserSettings

    @field_validator('sample_rate')
    @classmethod
    def validate_sample_rate_value(cls, v):
        validate_sample_rate(v)
        return v


class StartSessionResponse(BaseModel):
    """Response for POST /start_session"""
    status: str = "ok"


class AudioChunkRequest(BaseModel):
    """Request body for POST /audio_chunk"""
    session_id: str = Field(..., min_length=1)
    timestamp: float
    pcm_b64: str = Field(..., min_length=1)
    sample_rate: int = Field(..., gt=0)

    @field_validator('sample_rate')
    @classmethod
    def validate_sample_rate_value(cls, v):
        validate_sample_rate(v)
        return v


class AudioChunkResponse(BaseModel):
    """Response for POST /audio_chunk"""
    status: str = "ok"
    buffered_seconds: float
    queue_depth: int


class StopSessionRequest(BaseModel):
    """Request body for POST /stop_session"""
    session_id: str = Field(..., min_length=1)


class StopSessionResponse(BaseModel):
    """Response for POST /stop_session"""
    status: str
    summary_path: Optional[str]
    data_path: Optional[str]
    csv_path: Optional[str]
    session_status: str


class ErrorResponse(BaseModel):
    """Unified error response per spec §4.2.1"""
    status: str = "error"
    error_code: str
    message: str
    details: dict = Field(default_factory=dict)


# Global state
session_manager: Optional[SessionManager] = None
engine_config: Optional[Config] = None
engine_auth_token: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown

    Startup:
    - Initialize session manager
    - Load config
    - Set up auth token (if enabled)

    Shutdown:
    - Clean up resources
    """
    global session_manager, engine_config, engine_auth_token

    # Startup
    logger.info("Starting Audio Summary Engine")
    logger.info(f"Engine version: {__version__}")
    logger.info(f"API version: {__api_version__}")

    # Load config
    engine_config = Config()
    logger.info(f"Loaded configuration: {engine_config}")

    # Runtime mode from environment
    runtime_mode = os.environ.get("ENGINE_MODE", "prod")
    logger.info(f"Runtime mode: {runtime_mode}")

    # Auth token (optional)
    engine_auth_token = os.environ.get("ENGINE_AUTH_TOKEN")
    if engine_auth_token:
        logger.info("Engine auth token: ENABLED")
    else:
        logger.info("Engine auth token: DISABLED")

    # Initialize session manager
    session_manager = SessionManager(
        runtime_mode=runtime_mode,
        allow_concurrent=False  # Per spec: single session only
    )

    logger.info("Engine startup complete")

    yield

    # Shutdown
    logger.info("Shutting down Audio Summary Engine")


# Create FastAPI app
app = FastAPI(
    title="Audio Summary Engine API",
    version=__version__,
    description="HTTP API for audio transcription and summarization",
    lifespan=lifespan
)


# Exception handlers per spec §4.2.1


@app.exception_handler(SessionNotFoundError)
async def session_not_found_handler(request: Request, exc: SessionNotFoundError):
    """Handle SessionNotFoundError -> 404"""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=ErrorResponse(
            error_code="SESSION_NOT_FOUND",
            message=str(exc),
            details={"hint": "Start a new session via /start_session"}
        ).model_dump()
    )


@app.exception_handler(SessionAlreadyActiveError)
async def session_already_active_handler(request: Request, exc: SessionAlreadyActiveError):
    """Handle SessionAlreadyActiveError -> 409"""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=ErrorResponse(
            error_code="SESSION_ALREADY_ACTIVE",
            message=str(exc),
            details={"hint": "Stop the existing session before starting a new one"}
        ).model_dump()
    )


@app.exception_handler(AudioFormatError)
async def audio_format_error_handler(request: Request, exc: AudioFormatError):
    """Handle AudioFormatError -> 400"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            error_code="INVALID_AUDIO_FORMAT",
            message=str(exc),
            details={}
        ).model_dump()
    )


@app.exception_handler(SessionError)
async def session_error_handler(request: Request, exc: SessionError):
    """Handle generic SessionError -> 500"""
    # Check if error message contains a specific error code
    error_msg = str(exc)
    if "STT_BACKEND_UNAVAILABLE" in error_msg:
        error_code = "STT_BACKEND_UNAVAILABLE"
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    else:
        error_code = "SESSION_ERROR"
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error_code=error_code,
            message=error_msg,
            details={}
        ).model_dump()
    )


# Auth token validation

def verify_auth_token(x_engine_token: Optional[str] = Header(None)):
    """
    Verify engine auth token if enabled

    Per spec NFR2: Optional engine auth token
    - Sent as X-Engine-Token header
    - Returns 401 UNAUTHORIZED if missing/invalid

    Args:
        x_engine_token: Token from X-Engine-Token header

    Raises:
        HTTPException: If token is required but missing/invalid
    """
    if engine_auth_token is not None:
        if x_engine_token != engine_auth_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse(
                    error_code="UNAUTHORIZED",
                    message="Invalid or missing engine auth token",
                    details={"hint": "Provide X-Engine-Token header"}
                ).model_dump()
            )


# API Endpoints


@app.get("/health", response_model=HealthResponse)
async def health():
    """
    Health check endpoint

    Per spec §4.2 FR7: Returns engine status and available backends/models

    Returns:
        HealthResponse with version info and available backends
    """
    return HealthResponse(
        status="ok",
        engine_version=__version__,
        api_version=__api_version__,
        stt_backends=["whisper", "parakeet"],
        llm_models=["qwen3:4b-instruct", "llama3.2:3b", "phi3:3.8b"]
    )


@app.post("/start_session", response_model=StartSessionResponse, dependencies=[Depends(verify_auth_token)])
async def start_session(request: StartSessionRequest):
    """
    Start a new transcription session

    Per spec §4.2 FR7:
    - If another session is active and concurrent sessions are not allowed, return 409
    - Initialize STT backend (Whisper/Parakeet) via factory
    - Initialize TranscriptBuffer
    - Initialize MapReduceSummarizer with provided prompts
    - Create output directories

    Args:
        request: Session configuration

    Returns:
        StartSessionResponse

    Raises:
        SessionAlreadyActiveError: If session already active (409)
        SessionError: If session creation fails (500)
    """
    logger.info(f"Starting session {request.session_id}")
    logger.info(f"  Model: {request.model}")
    logger.info(f"  Sample rate: {request.sample_rate} Hz")

    # Get model path from config
    if request.model == "whisper":
        stt_model_path = engine_config.stt_model_path
    else:  # parakeet
        stt_model_path = engine_config.parakeet_model_path

    # Build data extraction prompt from config if not provided
    data_extraction_prompt = (
        request.user_settings.data_extraction_prompt
        or engine_config.data_extraction_prompt
    )

    # Create session config
    session_config = SessionConfig(
        session_id=request.session_id,
        stt_backend=request.model,
        stt_model_path=stt_model_path,
        capture_sample_rate=request.sample_rate,
        llm_model_name=request.user_settings.llm_model_name,
        chunk_summary_prompt=request.user_settings.chunk_summary_prompt,
        final_summary_prompt=request.user_settings.final_summary_prompt,
        data_extraction_prompt=data_extraction_prompt,
        output_dir=request.user_settings.output_dir,
        csv_export_path=request.user_settings.csv_export_path,
        append_csv=request.user_settings.append_csv,
        chunk_duration=engine_config.chunk_duration,
        chunk_summary_max_tokens=engine_config.chunk_summary_max_tokens,
        final_summary_max_tokens=engine_config.final_summary_max_tokens,
        min_audio_duration=engine_config.stt_min_audio_duration,
        max_audio_duration=engine_config.stt_max_audio_duration
    )

    # Create session via session manager
    # This may raise SessionAlreadyActiveError or SessionError
    session_manager.create_session(session_config)

    logger.info(f"Session {request.session_id} started successfully")

    return StartSessionResponse(status="ok")


@app.post("/audio_chunk", response_model=AudioChunkResponse, dependencies=[Depends(verify_auth_token)])
async def audio_chunk(request: AudioChunkRequest):
    """
    Add audio chunk to active session

    Per spec §4.2 FR7:
    - Validate session_id (return 404 if not found)
    - Decode base64 to np.ndarray float32 1D
    - Validate sample_rate and audio range
    - Feed into active session's STT buffer
    - Track buffered_seconds and queue_depth for backpressure

    Args:
        request: Audio chunk data

    Returns:
        AudioChunkResponse with buffer status

    Raises:
        SessionNotFoundError: If session not found (404)
        AudioFormatError: If audio format is invalid (400)
    """
    # Get session (raises SessionNotFoundError if not found)
    session = session_manager.get_session(request.session_id)

    # Validate session status
    if session.status != "active":
        raise SessionNotFoundError(
            f"Session {request.session_id} is not active (status: {session.status})"
        )

    # Decode PCM from base64
    # This validates audio format and raises AudioFormatError if invalid
    audio_data, duration = decode_pcm_from_base64(
        request.pcm_b64,
        request.sample_rate
    )

    # Add audio chunk to session
    # This will transcribe and potentially trigger chunk summarization
    transcript = session.add_audio_chunk(
        audio_data,
        request.timestamp,
        request.sample_rate
    )

    # Get buffer stats for backpressure monitoring
    buffer_stats = session.transcript_buffer.get_buffer_stats()
    buffered_seconds = session.transcriber.buffer_duration
    queue_depth = buffer_stats.get('segment_count', 0)

    # Log transcript if produced (not in production mode per spec NFR4)
    if transcript and logger.level <= logging.DEBUG:
        logger.debug(f"Transcript: {transcript[:100]}...")

    # TODO: Implement backpressure (429 Too Many Requests) if queue exceeds threshold
    # Per spec §4.2: Engine may respond with 429 if internal queues exceed threshold

    return AudioChunkResponse(
        status="ok",
        buffered_seconds=buffered_seconds,
        queue_depth=queue_depth
    )


@app.post("/stop_session", response_model=StopSessionResponse, dependencies=[Depends(verify_auth_token)])
async def stop_session(request: StopSessionRequest):
    """
    Stop session and generate summary

    Per spec §4.2 FR7:
    1. Flush transcriber buffer
    2. Force finalize current chunk
    3. Check for low content (insufficient_content status)
    4. Generate final summary (REDUCE phase)
    5. Extract structured data
    6. Write summary.txt and data.json
    7. Append to CSV if enabled

    Args:
        request: Session ID to stop

    Returns:
        StopSessionResponse with file paths and status

    Raises:
        SessionNotFoundError: If session not found (404)
    """
    logger.info(f"Stopping session {request.session_id}")

    # Stop session via session manager
    # This orchestrates all the summary generation steps
    result = session_manager.stop_session(request.session_id)

    logger.info(f"Session {request.session_id} stopped")
    logger.info(f"  Status: {result['session_status']}")
    logger.info(f"  Summary: {result['summary_path']}")
    logger.info(f"  Data: {result['data_path']}")
    if result['csv_path']:
        logger.info(f"  CSV: {result['csv_path']}")

    return StopSessionResponse(**result)


# Main entry point for running the server


def main():
    """
    Main entry point for audio-summary-server command

    Per spec §4.2 FR7:
    - Bind to 127.0.0.1 ONLY (spec NFR2)
    - Default port: 8756
    - Configurable via environment variables
    """
    import uvicorn

    # Configuration from environment
    host = os.environ.get("ENGINE_HOST", "127.0.0.1")
    port = int(os.environ.get("ENGINE_PORT", "8756"))
    log_level = os.environ.get("ENGINE_LOG_LEVEL", "info").lower()

    # Security check per spec NFR2: MUST bind to 127.0.0.1
    if host != "127.0.0.1":
        print(f"ERROR: Engine must bind to 127.0.0.1 only (got: {host})", file=sys.stderr)
        print("Per spec NFR2: Binding to any other address is a configuration error", file=sys.stderr)
        sys.exit(1)

    print(f"Starting Audio Summary Engine")
    print(f"Version: {__version__}")
    print(f"API Version: {__api_version__}")
    print(f"Binding to: {host}:{port}")
    print(f"Log level: {log_level}")
    print()

    # Run server
    uvicorn.run(
        "audio_summary_app.engine.server:app",
        host=host,
        port=port,
        log_level=log_level,
        access_log=True
    )


if __name__ == "__main__":
    main()
