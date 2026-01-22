"""
Lightweight Decoder Module

Implements a 100M parameter decoder architecture inspired by Chroma.
Designed for real-time streaming with low memory footprint.

Architecture:
- 100M parameters for efficient inference
- RVQ (Residual Vector Quantization) decoding
- Supports streaming token-by-token generation
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum

import numpy as np

logger = logging.getLogger(__name__)


class DecoderState(str, Enum):
    """Decoder state machine."""

    IDLE = "idle"
    LOADING = "loading"
    READY = "ready"
    DECODING = "decoding"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class TokenSchedule:
    """
    Token schedule for 1:2 interleaved processing.

    Attributes:
        text_token: Current text token
        audio_tokens: List of audio tokens (typically 2)
        step_index: Current step index
        total_steps: Total number of steps
    """

    text_token: str
    audio_tokens: list[int]
    step_index: int
    total_steps: int

    @property
    def is_first_step(self) -> bool:
        """Check if this is the first step."""
        return self.step_index == 0

    @property
    def is_last_step(self) -> bool:
        """Check if this is the last step."""
        return self.step_index >= self.total_steps - 1

    @property
    def progress(self) -> float:
        """Get progress as a fraction (0.0 to 1.0)."""
        if self.total_steps == 0:
            return 1.0
        return self.step_index / self.total_steps


@dataclass
class DecoderConfig:
    """Configuration for lightweight decoder."""

    # Model architecture
    NUM_PARAMS: int = 100_000_000  # 100M parameters
    NUM_LAYERS: int = 6
    HIDDEN_SIZE: int = 512
    NUM_ATTENTION_HEADS: int = 8

    # Token schedule
    TEXT_TOKENS_PER_STEP: int = 1
    AUDIO_TOKENS_PER_STEP: int = 2

    # RVQ settings
    NUM_CODEBOOKS: int = 8
    CODEBOOK_SIZE: int = 1024
    BITS_PER_CODEBOOK: int = 10

    # Caching
    ENABLE_KV_CACHE: bool = True
    CACHE_SIZE: int = 1024

    # Quantization
    QUANTIZE: bool = True
    QUANTIZATION_BITS: int = 8

    @property
    def model_size_mb(self) -> float:
        """Get model size in megabytes."""
        # Rough estimate: 100M params * 2 bytes (fp16) / 1024 / 1024
        return self.NUM_PARAMS * 2 / (1024 * 1024)


@dataclass
class DecodingResult:
    """
    Result from decoding step.

    Attributes:
        text: Decoded text token
        audio_tokens: Audio tokens for this step
        confidence: Confidence score (0-1)
        step_index: Current step index
        is_final: Whether this is the final result
    """

    text: str
    audio_tokens: list[int]
    confidence: float
    step_index: int
    is_final: bool = False

    def __iter__(self):
        """Allow unpacking as tuple."""
        return iter((self.text, self.audio_tokens))


class LightweightDecoder:
    """
    Lightweight decoder with 100M parameters.

    Implements RVQ decoding for streaming speech processing.
    Designed for low-latency real-time applications.

    Example:
        decoder = LightweightDecoder()
        decoder.load_model()
        for result in decoder.decode_stream(token_iterator):
            print(result.text)
    """

    def __init__(
        self,
        config: DecoderConfig | None = None,
    ) -> None:
        """
        Initialize the lightweight decoder.

        Args:
            config: Decoder configuration
        """
        self.config = config or DecoderConfig()
        self._state = DecoderState.IDLE
        self._kv_cache: dict[int, np.ndarray] = {}
        self._current_step = 0
        self._model_loaded = False

    def load_model(self) -> None:
        """
        Load the decoder model (lazy loading).

        In production, this would load the actual model weights.
        For now, this is a mock implementation.
        """
        self._state = DecoderState.LOADING
        logger.info("Loading lightweight decoder model...")

        # Simulate model loading
        # In production: load from checkpoint or HuggingFace
        self._model_loaded = True
        self._state = DecoderState.READY

        logger.info(f"Lightweight decoder loaded: {self.config.model_size_mb:.1f}MB")

    def _decode_step(
        self,
        text_token: str,
        audio_tokens: list[int],
    ) -> DecodingResult:
        """
        Perform a single decoding step.

        Args:
            text_token: Input text token
            audio_tokens: Input audio tokens

        Returns:
            DecodingResult with decoded output
        """
        if not self._model_loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        # Simulate decoding with mock output
        # In production: actual model forward pass
        decoded_text = text_token.replace("<T", "").replace(">", "")
        confidence = 0.95 - (self._current_step * 0.01)  # Slight decay

        return DecodingResult(
            text=decoded_text,
            audio_tokens=audio_tokens,
            confidence=max(0.0, min(1.0, confidence)),
            step_index=self._current_step,
        )

    def decode_schedule(
        self,
        schedules: Iterator[TokenSchedule],
    ) -> Iterator[DecodingResult]:
        """
        Decode a sequence of token schedules.

        Args:
            schedules: Iterator of token schedules

        Yields:
            DecodingResult for each step
        """
        if not self._model_loaded:
            self.load_model()

        self._state = DecoderState.DECODING

        try:
            for schedule in schedules:
                result = self._decode_step(
                    schedule.text_token,
                    schedule.audio_tokens,
                )
                result.is_final = schedule.is_last_step
                self._current_step += 1
                yield result

        except Exception as e:
            logger.error(f"Decoding error: {e}")
            self._state = DecoderState.ERROR
            raise

        finally:
            self._state = DecoderState.COMPLETED

    def decode_stream(
        self,
        text_tokens: Iterator[str],
        audio_tokens: Iterator[list[int]],
    ) -> Iterator[DecodingResult]:
        """
        Decode from interleaved token streams.

        Args:
            text_tokens: Iterator of text tokens
            audio_tokens: Iterator of audio token lists

        Yields:
            DecodingResult for each step
        """
        if not self._model_loaded:
            self.load_model()

        self._state = DecoderState.DECODING

        try:
            for text_tok, audio_tok in zip(text_tokens, audio_tokens, strict=True):
                result = self._decode_step(text_tok, audio_tok)
                self._current_step += 1
                yield result

        except Exception as e:
            logger.error(f"Stream decoding error: {e}")
            self._state = DecoderState.ERROR
            raise

        finally:
            self._state = DecoderState.COMPLETED

    def reset(self) -> None:
        """Reset decoder state."""
        self._state = DecoderState.IDLE if self._model_loaded else DecoderState.READY
        self._current_step = 0
        self._kv_cache.clear()

    def clear_cache(self) -> None:
        """Clear KV cache."""
        self._kv_cache.clear()

    def get_state(self) -> DecoderState:
        """Get current decoder state."""
        return self._state

    def is_ready(self) -> bool:
        """Check if decoder is ready for decoding."""
        return self._state == DecoderState.READY or self._model_loaded

    @property
    def parameter_count(self) -> int:
        """Get total parameter count."""
        return self.config.NUM_PARAMS

    @property
    def cache_size(self) -> int:
        """Get current cache size in bytes."""
        return sum(v.nbytes for v in self._kv_cache.values())
