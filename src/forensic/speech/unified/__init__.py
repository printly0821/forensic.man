"""
Unified Transcriber Module

Provides a unified factory interface for creating transcriber instances.
Supports multiple backends with automatic fallback.

Backends:
- whisper: faster-whisper based transcription
- streaming: Streaming adapter with Chroma-style interface
- auto: Automatic backend selection
"""

from forensic.speech.unified.transcriber_factory import (
    TranscriberBackend,
    TranscriberFactory,
    TranscriberType,
)

__all__ = [
    "TranscriberFactory",
    "TranscriberType",
    "TranscriberBackend",
]
