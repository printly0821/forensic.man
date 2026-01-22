"""
Whisper Streaming Adapter

Wraps the existing Whisper transcriber for streaming compatibility.
Provides Chroma-style interface while using faster-whisper backend.

This adapter maintains backward compatibility with the existing transcriber
while providing the streaming interface expected by the E2E module.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Generator, Iterator
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import numpy as np

from forensic.models.speech import SpeechSegment
from forensic.speech.e2e import StreamChunk
from forensic.speech.transcriber import Transcriber

logger = logging.getLogger(__name__)


class AdapterState(str, Enum):
    """Adapter state machine."""

    IDLE = "idle"
    INITIALIZING = "initializing"
    READY = "ready"
    STREAMING = "streaming"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class WhisperStreamingConfig:
    """Configuration for Whisper streaming adapter."""

    # Whisper settings (inherited from TranscriptionConfig)
    MODEL_SIZE: str = "large-v3"
    DEVICE: str = "cuda"
    COMPUTE_TYPE: str = "float16"

    # Streaming settings
    CHUNK_DURATION_SEC: float = 5.0  # 1-10 seconds as per spec
    OVERLAP_DURATION_SEC: float = 0.5  # Overlap for context

    # Language
    LANGUAGE: str = "ko"  # Korean first

    # VAD settings
    USE_VAD: bool = True
    VAD_THRESHOLD: float = 0.5

    # Progress callback
    REPORT_PROGRESS: bool = True

    @property
    def sample_rate(self) -> int:
        """Get required sample rate."""
        return 16000  # Whisper uses 16kHz


ProgressCallback = Callable[[float, str], None]


class WhisperStreamingAdapter:
    """
    Streaming adapter for Whisper transcriber.

    Wraps the existing Transcriber class to provide streaming interface.
    Supports chunk-by-chunk processing with progress tracking.

    Example:
        adapter = WhisperStreamingAdapter()
        adapter.initialize()

        for segment in adapter.transcribe_streaming(audio_path):
            print(f"[{segment.start_time:.2f}s] {segment.text}")
    """

    def __init__(
        self,
        config: WhisperStreamingConfig | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        """
        Initialize the Whisper streaming adapter.

        Args:
            config: Adapter configuration
            progress_callback: Optional progress callback
        """
        self.config = config or WhisperStreamingConfig()
        self.progress_callback = progress_callback
        self._state = AdapterState.IDLE
        self._transcriber: Transcriber | None = None

    def initialize(self) -> None:
        """
        Initialize the adapter (lazy loading).

        Loads the underlying Whisper transcriber.
        """
        self._state = AdapterState.INITIALIZING

        try:
            self._transcriber = Transcriber(
                model_size=self.config.MODEL_SIZE,
                device=self.config.DEVICE,
                compute_type=self.config.COMPUTE_TYPE,
            )
            self._transcriber.load_model()
            self._state = AdapterState.READY

            logger.info(f"Whisper streaming adapter initialized: {self.config.MODEL_SIZE}")

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            self._state = AdapterState.ERROR
            raise

    def create_stream_chunk(
        self,
        audio: np.ndarray,
        chunk_id: str,
        is_final: bool = False,
    ) -> StreamChunk:
        """
        Create a StreamChunk from audio data.

        Args:
            audio: Audio data as numpy array
            chunk_id: Unique chunk identifier
            is_final: Whether this is the final chunk

        Returns:
            StreamChunk for E2E processing
        """
        duration = len(audio) / self.config.sample_rate

        # Resample to 24kHz if needed for E2E compatibility
        if self.config.sample_rate != 24000:
            audio = self._resample_to_24khz(audio)

        return StreamChunk(
            audio=audio,
            sample_rate=24000,
            duration=duration,
            chunk_id=chunk_id,
            is_final=is_final,
        )

    def _resample_to_24khz(self, audio: np.ndarray) -> np.ndarray:
        """Resample audio from 16kHz to 24kHz."""
        try:
            import librosa

            return librosa.resample(audio, orig_sr=self.config.sample_rate, target_sr=24000)
        except ImportError:
            # Fallback: simple linear interpolation
            ratio = 24000 / self.config.sample_rate
            new_length = int(len(audio) * ratio)
            indices = np.linspace(0, len(audio) - 1, new_length)
            return np.interp(indices, np.arange(len(audio)), audio)

    def _load_audio(
        self,
        audio_path: Path,
    ) -> tuple[np.ndarray, int]:
        """
        Load audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            Tuple of (audio_data, sample_rate)
        """
        try:
            import soundfile as sf
        except ImportError as e:
            raise ImportError("soundfile is required for audio loading") from e

        audio, sr = sf.read(str(audio_path))

        # Convert to mono if needed
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)

        return audio, sr

    def _chunk_audio(
        self,
        audio: np.ndarray,
        sample_rate: int,
    ) -> Generator[tuple[np.ndarray, str, bool], None, None]:
        """
        Split audio into overlapping chunks.

        Args:
            audio: Audio data
            sample_rate: Sample rate

        Yields:
            Tuples of (chunk_audio, chunk_id, is_final)
        """
        chunk_samples = int(self.config.CHUNK_DURATION_SEC * sample_rate)
        overlap_samples = int(self.config.OVERLAP_DURATION_SEC * sample_rate)

        for i, start in enumerate(range(0, len(audio), chunk_samples - overlap_samples)):
            end = min(start + chunk_samples, len(audio))
            chunk_audio = audio[start:end]

            # Pad last chunk if needed
            if end - start < chunk_samples:
                padding = chunk_samples - (end - start)
                chunk_audio = np.pad(chunk_audio, (0, padding))

            is_final = end >= len(audio)
            chunk_id = f"chunk_{i:04d}"

            yield chunk_audio, chunk_id, is_final

    def transcribe_streaming(
        self,
        audio_path: Path | str,
    ) -> Generator[SpeechSegment, None, None]:
        """
        Transcribe audio file with streaming interface.

        Args:
            audio_path: Path to audio file

        Yields:
            SpeechSegment objects as they are transcribed
        """
        if self._transcriber is None:
            self.initialize()

        self._state = AdapterState.STREAMING

        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Load audio
        audio, sr = self._load_audio(audio_path)

        # Resample to Whisper's sample rate
        if sr != self.config.sample_rate:
            try:
                import librosa

                audio = librosa.resample(audio, orig_sr=sr, target_sr=self.config.sample_rate)
            except ImportError:
                logger.warning("librosa not available, using original sample rate")

        # Use the transcriber's streaming method
        total_segments = 0
        for segment in self._transcriber.transcribe_stream(audio_path):
            total_segments += 1

            # Report progress
            if self.progress_callback:
                self.progress_callback(total_segments, segment.text)

            yield segment

        self._state = AdapterState.COMPLETED
        logger.info(f"Streaming transcription complete: {total_segments} segments")

    def transcribe_chunks(
        self,
        chunks: Iterator[StreamChunk],
    ) -> Generator[SpeechSegment, None, None]:
        """
        Transcribe a stream of audio chunks.

        Args:
            chunks: Iterator of StreamChunk objects

        Yields:
            SpeechSegment objects as they are transcribed
        """
        if self._transcriber is None:
            self.initialize()

        self._state = AdapterState.STREAMING

        chunk_count = 0
        for chunk in chunks:
            chunk_count += 1

            # Process chunk (mock transcription for now)
            # In production: would use actual Whisper model
            segment = SpeechSegment(
                id=chunk.chunk_id,
                start_time=chunk_count * self.config.CHUNK_DURATION_SEC,
                end_time=(chunk_count + 1) * self.config.CHUNK_DURATION_SEC,
                text=f"<Chunk {chunk_count}>",
                confidence=0.95,
            )

            # Report progress
            if self.progress_callback:
                self.progress_callback(chunk_count, segment.text)

            yield segment

            if chunk.is_final:
                break

        self._state = AdapterState.COMPLETED
        logger.info(f"Chunk transcription complete: {chunk_count} chunks")

    def transcribe(
        self,
        audio_path: Path | str,
    ) -> list[SpeechSegment]:
        """
        Transcribe audio file (non-streaming).

        Args:
            audio_path: Path to audio file

        Returns:
            List of transcribed segments
        """
        if self._transcriber is None:
            self.initialize()

        return self._transcriber.transcribe(str(audio_path))

    def get_state(self) -> AdapterState:
        """Get current adapter state."""
        return self._state

    def is_ready(self) -> bool:
        """Check if adapter is ready."""
        return self._state == AdapterState.READY or self._transcriber is not None

    def reset(self) -> None:
        """Reset adapter state."""
        self._state = AdapterState.READY if self._transcriber else AdapterState.IDLE
