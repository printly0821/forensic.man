"""
Codec Wrapper Module

Audio codec interface for Chroma-style streaming.
Supports Mimi codec (24kHz, 8 codebooks) for efficient audio encoding.

This module provides a wrapper interface for audio codecs used in
end-to-end speech processing.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class CodecType(str, Enum):
    """Supported codec types."""

    MIMI = "mimi"  # Mimi codec (24kHz, 8 codebooks)
    ENCODEC = "encodec"  # EnCodec codec
    CUSTOM = "custom"  # Custom codec


class CodecState(str, Enum):
    """Codec state machine."""

    IDLE = "idle"
    LOADING = "loading"
    READY = "ready"
    ENCODING = "encoding"
    DECODING = "decoding"
    ERROR = "error"


@dataclass
class CodecConfig:
    """Configuration for audio codec."""

    # Codec type
    CODEC_TYPE: CodecType = CodecType.MIMI

    # Audio settings
    SAMPLE_RATE: int = 24000  # 24kHz for Mimi
    CHANNELS: int = 1  # Mono
    BITS_PER_SAMPLE: int = 16

    # Mimi-specific settings
    NUM_CODEBOOKS: int = 8
    CODEBOOK_SIZE: int = 1024
    FRAME_RATE: int = 75  # Frames per second

    # Bandwidth
    BANDWIDTH: float = 6.0  # kbps per codebook
    TOTAL_BANDWIDTH: float = 48.0  # kbps (6 * 8)

    # Latency
    TARGET_LATENCY_MS: float = 50.0  # < 50ms encoding latency

    @property
    def frame_size_samples(self) -> int:
        """Get frame size in samples."""
        return self.SAMPLE_RATE // self.FRAME_RATE

    @property
    def frame_duration_ms(self) -> float:
        """Get frame duration in milliseconds."""
        return 1000.0 / self.FRAME_RATE


@dataclass
class EncodedChunk:
    """
    Encoded audio chunk.

    Attributes:
        tokens: Encoded tokens (one list per codebook)
        num_frames: Number of frames in chunk
        duration: Duration in seconds
        chunk_id: Unique identifier
    """

    tokens: list[list[int]]  # Shape: [num_codebooks, num_frames]
    num_frames: int
    duration: float
    chunk_id: str

    @property
    def num_codebooks(self) -> int:
        """Get number of codebooks."""
        return len(self.tokens)

    @property
    def total_tokens(self) -> int:
        """Get total number of tokens across all codebooks."""
        return sum(len(cb) for cb in self.tokens)

    @property
    def bandwidth_usage(self) -> float:
        """Get approximate bandwidth usage in kbps."""
        tokens_per_second = self.total_tokens / max(0.001, self.duration)
        return tokens_per_second * self.BITS_PER_SAMPLE / 1000


@dataclass
class DecodedChunk:
    """
    Decoded audio chunk.

    Attributes:
        audio: Decoded audio as numpy array
        sample_rate: Sample rate in Hz
        duration: Duration in seconds
        chunk_id: Unique identifier
    """

    audio: np.ndarray
    sample_rate: int
    duration: float
    chunk_id: str

    @property
    def frame_count(self) -> int:
        """Get number of audio frames."""
        return len(self.audio)


class CodecWrapper:
    """
    Audio codec wrapper for Chroma-style streaming.

    Supports encoding and decoding with Mimi codec.
    Designed for low-latency real-time applications.

    Example:
        codec = CodecWrapper()
        codec.load_model()
        encoded = codec.encode(audio_chunk)
        decoded = codec.decode(encoded)
    """

    def __init__(
        self,
        config: CodecConfig | None = None,
    ) -> None:
        """
        Initialize the codec wrapper.

        Args:
            config: Codec configuration
        """
        self.config = config or CodecConfig()
        self._state = CodecState.IDLE
        self._model_loaded = False

    def load_model(self) -> None:
        """
        Load the codec model (lazy loading).

        In production, this would load the actual codec model.
        For now, this is a mock implementation.
        """
        self._state = CodecState.LOADING
        logger.info(f"Loading {self.config.CODEC_TYPE} codec...")

        # Simulate model loading
        # In production: load from checkpoint or HuggingFace
        self._model_loaded = True
        self._state = CodecState.READY

        logger.info(
            f"{self.config.CODEC_TYPE} codec loaded: "
            f"{self.config.SAMPLE_RATE}Hz, {self.config.NUM_CODEBOOKS} codebooks"
        )

    def encode(
        self,
        audio: np.ndarray,
        chunk_id: str = "",
    ) -> EncodedChunk:
        """
        Encode audio to codec tokens.

        Args:
            audio: Audio data as numpy array (float32, mono)
            chunk_id: Unique chunk identifier

        Returns:
            EncodedChunk with codec tokens
        """
        if not self._model_loaded:
            self.load_model()

        self._state = CodecState.ENCODING

        try:
            # Validate input
            if len(audio.shape) > 1:
                audio = audio.mean(axis=1)  # Convert to mono

            duration = len(audio) / self.config.SAMPLE_RATE
            num_frames = int(duration * self.config.FRAME_RATE)

            # Simulate encoding with mock tokens
            # In production: actual codec encode
            tokens = [
                [i * num_frames + j for j in range(num_frames)]
                for i in range(self.config.NUM_CODEBOOKS)
            ]

            return EncodedChunk(
                tokens=tokens,
                num_frames=num_frames,
                duration=duration,
                chunk_id=chunk_id,
            )

        except Exception as e:
            logger.error(f"Encoding error: {e}")
            self._state = CodecState.ERROR
            raise

        finally:
            self._state = CodecState.READY

    def encode_stream(
        self,
        audio_chunks: Iterator[tuple[np.ndarray, str]],
    ) -> Iterator[EncodedChunk]:
        """
        Encode a stream of audio chunks.

        Args:
            audio_chunks: Iterator of (audio, chunk_id) tuples

        Yields:
            EncodedChunk for each input
        """
        if not self._model_loaded:
            self.load_model()

        for audio, chunk_id in audio_chunks:
            yield self.encode(audio, chunk_id)

    def decode(
        self,
        encoded: EncodedChunk,
    ) -> DecodedChunk:
        """
        Decode codec tokens to audio.

        Args:
            encoded: Encoded chunk

        Returns:
            DecodedChunk with audio data
        """
        if not self._model_loaded:
            self.load_model()

        self._state = CodecState.DECODING

        try:
            num_samples = int(encoded.duration * self.config.SAMPLE_RATE)

            # Simulate decoding with mock audio
            # In production: actual codec decode
            audio = np.random.randn(num_samples).astype(np.float32) * 0.1

            return DecodedChunk(
                audio=audio,
                sample_rate=self.config.SAMPLE_RATE,
                duration=encoded.duration,
                chunk_id=encoded.chunk_id,
            )

        except Exception as e:
            logger.error(f"Decoding error: {e}")
            self._state = CodecState.ERROR
            raise

        finally:
            self._state = CodecState.READY

    def decode_stream(
        self,
        encoded_chunks: Iterator[EncodedChunk],
    ) -> Iterator[DecodedChunk]:
        """
        Decode a stream of encoded chunks.

        Args:
            encoded_chunks: Iterator of EncodedChunk

        Yields:
            DecodedChunk for each input
        """
        if not self._model_loaded:
            self.load_model()

        for encoded in encoded_chunks:
            yield self.decode(encoded)

    def encode_file(
        self,
        audio_path: Path,
    ) -> Iterator[EncodedChunk]:
        """
        Encode an audio file in chunks.

        Args:
            audio_path: Path to audio file

        Yields:
            EncodedChunk for each chunk
        """
        try:
            import soundfile as sf
        except ImportError as e:
            raise ImportError("soundfile is required for file encoding") from e

        audio, sr = sf.read(str(audio_path))

        # Resample if needed
        if sr != self.config.SAMPLE_RATE:
            import librosa

            audio = librosa.resample(audio, orig_sr=sr, target_sr=self.config.SAMPLE_RATE)

        # Chunk and encode
        chunk_duration = 5.0  # 5 seconds per chunk
        samples_per_chunk = int(chunk_duration * self.config.SAMPLE_RATE)

        for i, start in enumerate(range(0, len(audio), samples_per_chunk)):
            chunk_audio = audio[start : start + samples_per_chunk]
            chunk_id = f"{audio_path.stem}_chunk_{i:04d}"
            yield self.encode(chunk_audio, chunk_id)

    def get_state(self) -> CodecState:
        """Get current codec state."""
        return self._state

    def is_ready(self) -> bool:
        """Check if codec is ready."""
        return self._state == CodecState.READY or self._model_loaded

    def reset(self) -> None:
        """Reset codec state."""
        self._state = CodecState.READY if self._model_loaded else CodecState.IDLE

    @property
    def bandwidth(self) -> float:
        """Get total bandwidth in kbps."""
        return self.config.TOTAL_BANDWIDTH
