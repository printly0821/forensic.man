"""
Adapters Module

Provides adapters for integrating different speech processing backends.
"""

from forensic.speech.adapters.whisper_streaming import (
    AdapterState,
    WhisperStreamingAdapter,
    WhisperStreamingConfig,
)

__all__ = [
    "WhisperStreamingAdapter",
    "WhisperStreamingConfig",
    "AdapterState",
]
