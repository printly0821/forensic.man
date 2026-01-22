"""
Speaker Diarization Module

Uses pyannote-audio for speaker diarization.
Separates and identifies different speakers in audio.

REQ-T-002: Speaker diarization using pyannote-audio.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from forensic.models.speech import DiarizationSegment

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class DiarizationConfig:
    """Configuration for pyannote-audio diarization."""

    # Pipeline options
    PIPELINE = "pyannote/speaker-diarization-3.1"

    # Inference settings
    DEVICE = "cuda"  # cuda, cpu
    BATCH_SIZE = 32

    # Segmentation settings
    SEGMENTATION_MIN_DURATION = 0.0
    SEGMENTATION_MAX_DURATION = 30.0

    # Clustering settings
    CLUSTERING_THRESHOLD = 0.5
    MIN_SPEAKERS = 1
    MAX_SPEAKERS = 10


class Diarizer:
    """
    Speaker diarization using pyannote-audio.

    Identifies and separates different speakers in audio.
    """

    def __init__(
        self,
        pipeline: str = DiarizationConfig.PIPELINE,
        device: str = DiarizationConfig.DEVICE,
        use_auth_token: str | None = None,
    ) -> None:
        """
        Initialize the diarizer.

        Args:
            pipeline: HuggingFace pipeline identifier
            device: Device to use (cuda or cpu)
            use_auth_token: HuggingFace authentication token
        """
        self.pipeline_name = pipeline
        self.device = device
        self.use_auth_token = use_auth_token
        self._pipeline = None
        self._hf_token = use_auth_token

    def load_pipeline(self) -> None:
        """Load the diarization pipeline lazily."""
        if self._pipeline is None:
            try:
                from pyannote.audio import Pipeline
            except ImportError as e:
                raise ImportError(
                    "pyannote-audio is required. Install with: pip install pyannote-audio"
                ) from e

            logger.info(f"Loading diarization pipeline: {self.pipeline_name}")

            if self._hf_token:
                self._pipeline = Pipeline.from_pretrained(
                    self.pipeline_name,
                    use_auth_token=self._hf_token,
                )
            else:
                # Try to load from local cache or config
                try:
                    self._pipeline = Pipeline.from_pretrained(self.pipeline_name)
                except Exception as e:
                    raise RuntimeError(
                        f"Cannot load pipeline {self.pipeline_name}. "
                        "Please accept user conditions at "
                        f"https://huggingface.co/{self.pipeline_name} "
                        "and provide HF token."
                    ) from e

            # Move to device
            if self.device == "cuda":
                try:
                    import torch

                    if torch.cuda.is_available():
                        self._pipeline.to(torch.device("cuda"))
                        logger.info("Pipeline moved to CUDA")
                except ImportError:
                    logger.warning("PyTorch not available, using CPU")

            logger.info("Diarization pipeline loaded successfully")

    def diarize(
        self,
        audio_path: str | Path,
        min_speakers: int = DiarizationConfig.MIN_SPEAKERS,
        max_speakers: int = DiarizationConfig.MAX_SPEAKERS,
    ) -> list[DiarizationSegment]:
        """
        Perform speaker diarization on audio file.

        Args:
            audio_path: Path to audio file
            min_speakers: Minimum number of speakers
            max_speakers: Maximum number of speakers

        Returns:
            List of diarization segments
        """
        self.load_pipeline()

        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"Diarizing: {audio_path}")

        # Prepare waveform
        try:
            import torch
        except ImportError as e:
            raise ImportError("PyTorch is required for pyannote-audio") from e

        try:
            import soundfile as sf
        except ImportError as e:
            raise ImportError("soundfile is required for audio loading") from e

        waveform, sample_rate = sf.read(str(audio_path))

        # Ensure mono
        if len(waveform.shape) > 1:
            waveform = waveform.mean(axis=1)

        # Convert to torch tensor
        waveform = torch.from_numpy(waveform).float().unsqueeze(0)

        # Apply preprocessor
        from pyannote.audio.core.io import Audio

        audio = Audio(sample_rate=sample_rate, mono=True)
        waveform = audio({"waveform": waveform, "sample_rate": sample_rate})

        # Run diarization
        diarization = self._pipeline(
            waveform,
            num_speakers=(min_speakers, max_speakers),
        )

        # Convert to DiarizationSegment objects
        segments: list[DiarizationSegment] = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            seg = DiarizationSegment(
                id=f"{audio_path.stem}_{speaker}_{turn.start:.2f}",
                start_time=float(turn.start),
                end_time=float(turn.end),
                speaker_id=str(speaker),
                confidence=1.0,  # pyannote doesn't provide confidence
            )
            segments.append(seg)

        logger.info(f"Diarization complete: {len(segments)} segments")
        return segments

    def diarize_with_transcription(
        self,
        audio_path: str | Path,
        transcription_segments: list,
        min_speakers: int = DiarizationConfig.MIN_SPEAKERS,
        max_speakers: int = DiarizationConfig.MAX_SPEAKERS,
    ) -> list[DiarizationSegment]:
        """
        Perform diarization and align with transcription.

        Args:
            audio_path: Path to audio file
            transcription_segments: List of transcription segments
            min_speakers: Minimum number of speakers
            max_speakers: Maximum number of speakers

        Returns:
            List of diarization segments aligned with transcription
        """
        diarization_segments = self.diarize(
            audio_path, min_speakers=min_speakers, max_speakers=max_speakers
        )

        # Align diarization with transcription
        # Find best matching speaker for each transcription segment
        aligned: list[DiarizationSegment] = []

        for trans_seg in transcription_segments:
            trans_start = trans_seg.start_time
            trans_end = trans_seg.end_time

            # Find diarization segment with maximum overlap
            best_speaker = "UNKNOWN"
            max_overlap = 0.0

            for dia_seg in diarization_segments:
                overlap = min(trans_end, dia_seg.end_time) - max(trans_start, dia_seg.start_time)
                if overlap > max_overlap:
                    max_overlap = overlap
                    best_speaker = dia_seg.speaker_id

            aligned.append(
                DiarizationSegment(
                    id=trans_seg.id,
                    start_time=trans_start,
                    end_time=trans_end,
                    speaker_id=best_speaker,
                    confidence=1.0 if max_overlap > 0 else 0.0,
                )
            )

        return aligned

    def get_speaker_count(self, audio_path: str | Path) -> int:
        """
        Get number of unique speakers in audio.

        Args:
            audio_path: Path to audio file

        Returns:
            Number of unique speakers
        """
        segments = self.diarize(audio_path)
        speakers = {seg.speaker_id for seg in segments}
        return len(speakers)
