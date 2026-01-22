"""
Transcriber Factory Module

Provides unified factory interface for creating transcriber instances.
Supports automatic fallback and backend selection.

This factory implements the Protocol defined in SPEC-SPEECH-002.
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from enum import Enum
from pathlib import Path
from typing import Protocol

import numpy as np

from forensic.models.speech import SpeechSegment

logger = logging.getLogger(__name__)


class TranscriberType(str, Enum):
    """Available transcriber types."""

    AUTO = "auto"  # Automatic selection
    WHISPER = "whisper"  # faster-whisper backend
    STREAMING = "streaming"  # Whisper streaming adapter
    E2E = "e2e"  # E2E Chroma-style (future)


class TranscriberBackend(Protocol):
    """
    Protocol for transcriber backends.

    All transcriber implementations must conform to this protocol.
    """

    def transcribe(
        self,
        audio: Path | np.ndarray,
        language: str = "ko",
    ) -> list[SpeechSegment]:
        """
        Transcribe audio file.

        Args:
            audio: Path to audio file or audio array
            language: Language code (default: "ko")

        Returns:
            List of transcribed speech segments
        """
        ...

    def transcribe_streaming(
        self,
        audio: Path | np.ndarray,
        chunk_size: float = 5.0,
    ) -> Generator[SpeechSegment, None, None]:
        """
        Transcribe audio in chunks for streaming.

        Args:
            audio: Path to audio file or audio array
            chunk_size: Chunk size in seconds

        Yields:
            Speech segments as they are transcribed
        """
        ...


class TranscriberFactory:
    """
    Unified factory for creating transcriber instances.

    Supports automatic backend selection with fallback.
    Implements the REQ-E2E-005 requirement for unified interface.

    Example:
        factory = TranscriberFactory()
        transcriber = factory.create("whisper")
        segments = transcriber.transcribe(audio_path)

        # Or use auto selection
        transcriber = factory.create("auto")
    """

    def __init__(
        self,
        default_type: TranscriberType = TranscriberType.AUTO,
        device: str = "cuda",
        model_size: str = "large-v3",
    ) -> None:
        """
        Initialize the transcriber factory.

        Args:
            default_type: Default transcriber type
            device: Device to use (cuda or cpu)
            model_size: Model size for Whisper
        """
        self.default_type = default_type
        self.device = device
        self.model_size = model_size
        self._instances: dict[TranscriberType, object] = {}

    def _is_whisper_available(self) -> bool:
        """Check if faster-whisper is available."""
        try:
            import faster_whisper  # noqa: F401

            return True
        except ImportError:
            return False

    def _is_gpu_available(self) -> bool:
        """Check if GPU is available."""
        try:
            import torch

            return torch.cuda.is_available()
        except ImportError:
            return False

    def _create_whisper_transcriber(self) -> TranscriberBackend:
        """Create a Whisper transcriber instance."""
        from forensic.speech.transcriber import Transcriber

        transcriber = Transcriber(
            model_size=self.model_size,
            device=self.device if self._is_gpu_available() else "cpu",
            compute_type="float16" if self._is_gpu_available() else "int8",
        )
        transcriber.load_model()
        return transcriber  # type: ignore

    def _create_streaming_transcriber(self) -> TranscriberBackend:
        """Create a streaming transcriber instance."""
        from forensic.speech.adapters.whisper_streaming import (
            WhisperStreamingAdapter,
            WhisperStreamingConfig,
        )

        config = WhisperStreamingConfig(
            MODEL_SIZE=self.model_size,
            DEVICE=self.device if self._is_gpu_available() else "cpu",
            COMPUTE_TYPE="float16" if self._is_gpu_available() else "int8",
        )

        adapter = WhisperStreamingAdapter(config=config)
        adapter.initialize()
        return adapter  # type: ignore

    def _create_e2e_transcriber(self) -> TranscriberBackend:
        """Create an E2E transcriber instance (future)."""
        from forensic.speech.e2e import StreamingProcessor

        processor = StreamingProcessor()
        return processor  # type: ignore

    def _select_auto_backend(self) -> TranscriberType:
        """
        Automatically select the best available backend.

        Selection order:
        1. Streaming (if Whisper available)
        2. Whisper (if available)
        3. Raise error if nothing available

        Returns:
            Selected transcriber type
        """
        if self._is_whisper_available():
            logger.info("Auto-selected: streaming backend")
            return TranscriberType.STREAMING

        raise RuntimeError(
            "No transcriber backend available. Install faster-whisper: pip install faster-whisper"
        )

    def create(
        self,
        backend: str | TranscriberType = "auto",
    ) -> TranscriberBackend:
        """
        Create a transcriber instance.

        Args:
            backend: Backend type ("auto", "whisper", "streaming", "e2e")

        Returns:
            TranscriberBackend instance

        Raises:
            RuntimeError: If no backend is available
        """
        # Normalize backend type
        if isinstance(backend, str):
            try:
                backend = TranscriberType(backend)
            except ValueError as e:
                valid = [t.value for t in TranscriberType]
                raise ValueError(f"Invalid backend: {backend}. Valid options: {valid}") from e

        # Auto selection
        if backend == TranscriberType.AUTO:
            backend = self._select_auto_backend()

        # Check cache
        if backend in self._instances:
            logger.info(f"Using cached {backend.value} transcriber")
            return self._instances[backend]  # type: ignore

        # Create new instance
        logger.info(f"Creating {backend.value} transcriber...")

        if backend == TranscriberType.WHISPER:
            instance = self._create_whisper_transcriber()
        elif backend == TranscriberType.STREAMING:
            instance = self._create_streaming_transcriber()
        elif backend == TranscriberType.E2E:
            instance = self._create_e2e_transcriber()
        else:
            raise RuntimeError(f"Unsupported backend: {backend}")

        # Cache instance
        self._instances[backend] = instance
        logger.info(f"Created {backend.value} transcriber")

        return instance

    def create_with_fallback(
        self,
        preferred: str | TranscriberType = "streaming",
        fallback: str | TranscriberType = "whisper",
    ) -> TranscriberBackend:
        """
        Create a transcriber with automatic fallback.

        Args:
            preferred: Preferred backend type
            fallback: Fallback backend type

        Returns:
            TranscriberBackend instance

        Raises:
            RuntimeError: If neither backend is available
        """
        try:
            return self.create(preferred)
        except Exception as e:
            logger.warning(f"Failed to create {preferred}: {e}")
            logger.info(f"Falling back to {fallback}")
            return self.create(fallback)

    def get_available_backends(self) -> list[TranscriberType]:
        """
        Get list of available backends.

        Returns:
            List of available transcriber types
        """
        available = []

        if self._is_whisper_available():
            available.extend([TranscriberType.WHISPER, TranscriberType.STREAMING])

        return available

    def clear_cache(self) -> None:
        """Clear cached instances."""
        self._instances.clear()

    def get_info(self) -> dict[str, str | bool]:
        """
        Get factory information.

        Returns:
            Dictionary with factory info
        """
        return {
            "default_type": self.default_type.value,
            "device": self.device,
            "model_size": self.model_size,
            "gpu_available": self._is_gpu_available(),
            "whisper_available": self._is_whisper_available(),
            "available_backends": [t.value for t in self.get_available_backends()],
        }
