"""
Audio Summary Engine - HTTP API Service

This package implements the HTTP API server for the Audio Summary engine,
exposing endpoints for session management and audio processing.

Per spec §3.1: The engine owns audio ingestion, STT, transcript buffering,
summarization, and data persistence.
"""

__version__ = "1.0.0"
__api_version__ = "1"
