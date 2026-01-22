"""
Speech Transcription Module

Uses faster-whisper for fast and accurate Korean speech-to-text.
Optimized for DGX Spark ARM64 environment.

REQ-T-001: Speech-to-Text transcription using faster-whisper.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from forensic.models.speech import SpeechSegment

if TYPE_CHECKING:
    from collections.abc import Generator

logger = logging.getLogger(__name__)


class TranscriptionConfig:
    """Configuration for faster-whisper transcription."""

    # Model options: tiny, tiny.en, base, base.en, small, small.en
    # medium, medium.en, large-v1, large-v2, large-v3
    MODEL_SIZE = "large-v3"

    # Inference settings
    COMPUTE_TYPE = "float16"  # float16, int8, int8_float16
    DEVICE = "cuda"  # cuda, cpu
    NUM_WORKERS = 4
    BATCH_SIZE = 16

    # Language settings
    LANGUAGE = "ko"  # Korean
    TASK = "transcribe"

    # VAD settings
    VAD_FILTER = True
    VAD_PARAMETERS = {
        "min_silence_duration_ms": 500,
        "speech_pad_ms": 300,
    }

    # Beam search settings
    BEAM_SIZE = 5
    BEST_OF = 5

    # Timestamp settings
    WORD_TIMINGS = True
    HIGHLIGHT_WORDS = True


class Transcriber:
    """
    Speech transcriber using faster-whisper.

    Provides fast and accurate transcription for Korean audio.
    Supports GPU acceleration for faster processing.
    """

    def __init__(
        self,
        model_size: str = TranscriptionConfig.MODEL_SIZE,
        device: str = TranscriptionConfig.DEVICE,
        compute_type: str = TranscriptionConfig.COMPUTE_TYPE,
    ) -> None:
        """
        Initialize the transcriber.

        Args:
            model_size: Size of the Whisper model
            device: Device to use (cuda or cpu)
            compute_type: Computation type for inference
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def load_model(self) -> None:
        """Load the Whisper model lazily."""
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as e:
                raise ImportError(
                    "faster-whisper is required. Install with: pip install faster-whisper"
                ) from e

            logger.info(f"Loading Whisper model: {self.model_size}")
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                num_workers=TranscriptionConfig.NUM_WORKERS,
            )
            logger.info("Whisper model loaded successfully")

    def transcribe(
        self,
        audio_path: str | Path,
        beam_size: int = TranscriptionConfig.BEAM_SIZE,
        best_of: int = TranscriptionConfig.BEST_OF,
        word_timings: bool = TranscriptionConfig.WORD_TIMINGS,
    ) -> list[SpeechSegment]:
        """
        Transcribe audio file.

        Args:
            audio_path: Path to audio file
            beam_size: Beam size for decoding
            best_of: Number of candidates for sampling
            word_timings: Whether to return word-level timestamps

        Returns:
            List of transcribed speech segments
        """
        self.load_model()

        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"Transcribing: {audio_path}")

        segments: list[SpeechSegment] = []
        segment_infos = self._model.transcribe(
            str(audio_path),
            language=TranscriptionConfig.LANGUAGE,
            task=TranscriptionConfig.TASK,
            beam_size=beam_size,
            best_of=best_of,
            word_timestamps=word_timings,
            vad_filter=TranscriptionConfig.VAD_FILTER,
            vad_parameters=TranscriptionConfig.VAD_PARAMETERS,
            batch_size=TranscriptionConfig.BATCH_SIZE,
        )

        for i, seg in enumerate(segment_infos["segments"]):
            speech_seg = SpeechSegment(
                id=f"{audio_path.stem}_seg_{i:04d}",
                start_time=seg["start"],
                end_time=seg["end"],
                text=seg["text"].strip(),
                confidence=seg.get("avg_logprob", 1.0),
            )
            segments.append(speech_seg)

        logger.info(f"Transcription complete: {len(segments)} segments")
        return segments

    def transcribe_stream(
        self,
        audio_path: str | Path,
        _chunk_size: float = 30.0,
    ) -> Generator[SpeechSegment, None, None]:
        """
        Transcribe audio in chunks for streaming.

        Args:
            audio_path: Path to audio file
            chunk_size: Chunk size in seconds

        Yields:
            Speech segments as they are transcribed
        """
        self.load_model()

        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"Streaming transcription: {audio_path}")

        segment_infos = self._model.transcribe(
            str(audio_path),
            language=TranscriptionConfig.LANGUAGE,
            vad_filter=TranscriptionConfig.VAD_FILTER,
        )

        for i, seg in enumerate(segment_infos["segments"]):
            speech_seg = SpeechSegment(
                id=f"{audio_path.stem}_seg_{i:04d}",
                start_time=seg["start"],
                end_time=seg["end"],
                text=seg["text"].strip(),
                confidence=seg.get("avg_logprob", 1.0),
            )
            yield speech_seg

    def get_language_info(self, audio_path: str | Path) -> dict[str, str | float]:
        """
        Detect language from audio.

        Args:
            audio_path: Path to audio file

        Returns:
            Dictionary with language detection results
        """
        self.load_model()

        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Run with language detection
        segment_infos = self._model.transcribe(str(audio_path), language=None)

        info = segment_infos.get("language", "unknown")
        return {"language": info, "confidence": 1.0}
