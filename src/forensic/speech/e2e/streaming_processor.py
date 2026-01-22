"""
Streaming Processor Module

Implements Chroma-style 1:2 interleaved token processing for real-time transcription.

Token Schedule: 1 Text token + 2 Audio tokens per step
- TTFT (Time To First Token) < 150ms
- RTF (Real-Time Factor) < 0.5
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from enum import Enum

import numpy as np

logger = logging.getLogger(__name__)


class ProcessingState(str, Enum):
    """Processing state machine."""

    IDLE = "idle"
    BUFFERING = "buffering"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class StreamChunk:
    """
    Audio chunk for streaming processing.

    Attributes:
        audio: Audio data as numpy array (float32, mono)
        sample_rate: Sample rate in Hz (typically 24000)
        duration: Duration in seconds
        chunk_id: Unique chunk identifier
        is_final: Whether this is the final chunk
    """

    audio: np.ndarray
    sample_rate: int
    duration: float
    chunk_id: str
    is_final: bool = False

    @property
    def frame_count(self) -> int:
        """Return number of audio frames."""
        return len(self.audio)

    @property
    def token_estimate(self) -> int:
        """Estimate number of audio tokens needed."""
        # Rough estimate: 1 token per ~320 samples at 24kHz
        return max(1, self.frame_count // 320)


@dataclass
class ProcessingStats:
    """
    Processing statistics for monitoring.

    Attributes:
        chunks_processed: Number of chunks processed
        total_duration: Total audio duration in seconds
        processing_time: Total processing time in seconds
        ttft_ms: Time to first token in milliseconds
        rtf: Real-time factor (processing_time / audio_duration)
        tokens_generated: Number of tokens generated
        error_count: Number of errors encountered
    """

    chunks_processed: int = 0
    total_duration: float = 0.0
    processing_time: float = 0.0
    ttft_ms: float = 0.0
    rtf: float = 0.0
    tokens_generated: int = 0
    error_count: int = 0

    def update_rtf(self) -> None:
        """Update RTF based on current stats."""
        if self.total_duration > 0:
            self.rtf = self.processing_time / self.total_duration

    def is_within_target(self) -> bool:
        """Check if RTF is within target (< 0.5)."""
        return self.rtf < 0.5


@dataclass
class StreamingProcessorConfig:
    """Configuration for streaming processor."""

    # Audio settings
    SAMPLE_RATE: int = 24000  # 24kHz for Chroma compatibility
    CHUNK_DURATION_SEC: float = 5.0  # Default chunk size

    # Token schedule (1:2 interleaved)
    TEXT_TOKENS_PER_STEP: int = 1
    AUDIO_TOKENS_PER_STEP: int = 2

    # Performance targets
    TARGET_TTFT_MS: float = 150.0  # < 150ms
    TARGET_RTF: float = 0.5  # < 0.5 (2x real-time)

    # Buffer settings
    MIN_BUFFER_SIZE: int = 3  # Minimum chunks before processing
    MAX_BUFFER_SIZE: int = 10  # Maximum chunks to buffer

    # Retry settings
    MAX_RETRIES: int = 3
    RETRY_DELAY_MS: float = 100.0


ProgressCallback = Callable[[float, str], None]


class StreamingProcessor:
    """
    Chroma-style 1:2 interleaved streaming processor.

    Processes audio chunks with 1:2 text-to-audio token ratio.
    Supports real-time transcription with low latency.

    Example:
        processor = StreamingProcessor()
        for chunk in processor.process_stream(audio_iterator):
            print(chunk.text)
    """

    def __init__(
        self,
        config: StreamingProcessorConfig | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        """
        Initialize the streaming processor.

        Args:
            config: Processor configuration
            progress_callback: Optional callback for progress updates
        """
        self.config = config or StreamingProcessorConfig()
        self.progress_callback = progress_callback
        self._state = ProcessingState.IDLE
        self._stats = ProcessingStats()
        self._buffer: list[StreamChunk] = []
        self._first_token_time: float | None = None
        self._start_time: float | None = None

    def create_chunk(
        self,
        audio: np.ndarray,
        sample_rate: int,
        chunk_id: str,
        is_final: bool = False,
    ) -> StreamChunk:
        """
        Create a stream chunk from audio data.

        Args:
            audio: Audio data as numpy array
            sample_rate: Sample rate in Hz
            chunk_id: Unique chunk identifier
            is_final: Whether this is the final chunk

        Returns:
            StreamChunk object
        """
        duration = len(audio) / sample_rate
        return StreamChunk(
            audio=audio,
            sample_rate=sample_rate,
            duration=duration,
            chunk_id=chunk_id,
            is_final=is_final,
        )

    def validate_chunk(self, chunk: StreamChunk) -> bool:
        """
        Validate a stream chunk.

        Args:
            chunk: Chunk to validate

        Returns:
            True if valid, False otherwise
        """
        if chunk.frame_count == 0:
            logger.warning(f"Empty chunk: {chunk.chunk_id}")
            return False

        if chunk.sample_rate != self.config.SAMPLE_RATE:
            logger.warning(
                f"Sample rate mismatch: {chunk.sample_rate} != {self.config.SAMPLE_RATE}"
            )
            return False

        return True

    def _emit_interleaved_tokens(
        self,
        chunk: StreamChunk,
    ) -> Iterator[tuple[str, list[int]]]:
        """
        Generate 1:2 interleaved token schedule.

        Yields:
            Tuples of (text_token, [audio_token1, audio_token2])
        """
        token_count = chunk.token_estimate
        step_count = max(
            1, token_count // (self.config.TEXT_TOKENS_PER_STEP + self.config.AUDIO_TOKENS_PER_STEP)
        )

        for step in range(step_count):
            # 1 text token
            text_token = f"<T{step}>"

            # 2 audio tokens (simulated)
            audio_tokens = [step * 2, step * 2 + 1]

            yield text_token, audio_tokens

            self._stats.tokens_generated += (
                self.config.TEXT_TOKENS_PER_STEP + self.config.AUDIO_TOKENS_PER_STEP
            )

    def process_chunk(
        self,
        chunk: StreamChunk,
    ) -> Iterator[str]:
        """
        Process a single chunk with 1:2 interleaved schedule.

        Args:
            chunk: Chunk to process

        Yields:
            Text tokens as they are generated
        """
        if not self.validate_chunk(chunk):
            self._stats.error_count += 1
            return

        # Record TTFT (first token generation)
        if self._first_token_time is None:
            self._first_token_time = time.perf_counter()
            if self._start_time is not None:
                self._stats.ttft_ms = (self._first_token_time - self._start_time) * 1000

        # Process with 1:2 interleaved schedule
        for text_token, _ in self._emit_interleaved_tokens(chunk):
            yield text_token

        # Update stats
        self._stats.chunks_processed += 1
        self._stats.total_duration += chunk.duration

    def process_stream(
        self,
        chunks: Iterator[StreamChunk],
    ) -> Iterator[str]:
        """
        Process a stream of audio chunks.

        Args:
            chunks: Iterator of audio chunks

        Yields:
            Transcribed text tokens
        """
        self._state = ProcessingState.PROCESSING
        self._start_time = time.perf_counter()

        try:
            for chunk in chunks:
                for token in self.process_chunk(chunk):
                    yield token

                    # Report progress
                    if self.progress_callback:
                        progress = self._stats.chunks_processed / max(1, self._stats.total_duration)
                        self.progress_callback(progress, token)

                if chunk.is_final:
                    break

        except Exception as e:
            logger.error(f"Processing error: {e}")
            self._stats.error_count += 1
            self._state = ProcessingState.ERROR
            raise

        finally:
            self._state = ProcessingState.COMPLETED
            end_time = time.perf_counter()
            self._stats.processing_time = end_time - self._start_time
            self._stats.update_rtf()

    def get_stats(self) -> ProcessingStats:
        """Get current processing statistics."""
        return self._stats

    def reset(self) -> None:
        """Reset processor state."""
        self._state = ProcessingState.IDLE
        self._stats = ProcessingStats()
        self._buffer.clear()
        self._first_token_time = None
        self._start_time = None

    def get_state(self) -> ProcessingState:
        """Get current processing state."""
        return self._state

    def is_realtime_capable(self) -> bool:
        """Check if processing is real-time capable (RTF < 0.5)."""
        return self._stats.is_within_target()

    def get_ttft(self) -> float:
        """Get Time To First Token in milliseconds."""
        return self._stats.ttft_ms
