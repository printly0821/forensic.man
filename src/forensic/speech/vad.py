"""
Voice Activity Detection Module

Detects speech segments in audio using webrtcvad or pyannote.audio.
Identifies regions with speech vs silence/noise.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class VadConfig:
    """Configuration for Voice Activity Detection."""

    # Frame settings
    FRAME_DURATION_MS = 30  # Frame duration in milliseconds
    PAD_DURATION_MS = 300  # Padding duration in milliseconds

    # Detection settings
    AGGRESSIVENESS = 3  # 0-3, higher = more aggressive filtering

    # Threshold settings
    SPEECH_PROB_THRESHOLD = 0.5  # For probabilistic VAD
    MIN_SPEECH_DURATION_MS = 250  # Minimum speech segment duration
    MIN_SILENCE_DURATION_MS = 100  # Minimum silence duration


@dataclass
class SpeechFrame:
    """A single frame with VAD result."""

    start_time: float
    end_time: float
    is_speech: bool
    speech_probability: float = 1.0


class VoiceActivityDetector:
    """
    Voice Activity Detection using webrtcvad.

    Identifies speech and non-speech regions in audio.
    """

    def __init__(self, aggressiveness: int = VadConfig.AGGRESSIVENESS) -> None:
        """
        Initialize VAD.

        Args:
            aggressiveness: VAD aggressiveness (0-3)
        """
        self.aggressiveness = max(0, min(3, aggressiveness))
        self._vad = None

    def _get_vad(self):
        """Get webrtcvad.VAD instance."""
        if self._vad is None:
            try:
                import webrtcvad

                self._vad = webrtcvad.Vad(self.aggressiveness)
            except ImportError as e:
                raise ImportError(
                    "webrtcvad is required. Install with: pip install webrtcvad"
                ) from e
        return self._vad

    def detect_frames(
        self,
        audio_path: str | Path,
        frame_duration_ms: int = VadConfig.FRAME_DURATION_MS,
    ) -> list[SpeechFrame]:
        """
        Detect speech frames in audio.

        Args:
            audio_path: Path to audio file
            frame_duration_ms: Frame duration in ms (10, 20, or 30)

        Returns:
            List of speech frames
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Load audio
        try:
            import soundfile as sf
        except ImportError as e:
            raise ImportError("soundfile is required for audio loading") from e

        audio, sample_rate = sf.read(str(audio_path))

        # Convert to mono if needed
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)

        # Convert to 16-bit PCM
        audio_int16 = (audio * 32767).astype(np.int16)

        # Calculate frame size
        frame_size = int(sample_rate * frame_duration_ms / 1000)

        vad = self._get_vad()
        frames: list[SpeechFrame] = []

        for _i, start_sample in enumerate(range(0, len(audio_int16), frame_size)):
            end_sample = min(start_sample + frame_size, len(audio_int16))
            frame = audio_int16[start_sample:end_sample]

            if len(frame) < frame_size:
                # Pad last frame
                frame = np.pad(frame, (0, frame_size - len(frame)), constant_values=0)

            start_time = start_sample / sample_rate
            end_time = end_sample / sample_rate

            is_speech = bool(vad.is_speech(frame.tobytes(), sample_rate))

            frames.append(
                SpeechFrame(
                    start_time=start_time,
                    end_time=end_time,
                    is_speech=is_speech,
                )
            )

        return frames

    def merge_speech_segments(
        self,
        frames: list[SpeechFrame],
        min_duration_ms: int = VadConfig.MIN_SPEECH_DURATION_MS,
        pad_duration_ms: int = VadConfig.PAD_DURATION_MS,
    ) -> list[tuple[float, float]]:
        """
        Merge consecutive speech frames into segments.

        Args:
            frames: List of speech frames
            min_duration_ms: Minimum segment duration in ms
            pad_duration_ms: Padding duration in ms

        Returns:
            List of (start_time, end_time) tuples
        """
        segments: list[tuple[float, float]] = []
        current_start = None
        current_end = None

        for frame in frames:
            if frame.is_speech:
                if current_start is None:
                    current_start = frame.start_time
                    current_end = frame.end_time
                else:
                    # Check if gap is within padding threshold
                    if frame.start_time - current_end <= pad_duration_ms / 1000:
                        current_end = frame.end_time
                    else:
                        # Gap too large, end current segment
                        segments.append((current_start, current_end))
                        current_start = frame.start_time
                        current_end = frame.end_time
            else:
                if current_start is not None:
                    segments.append((current_start, current_end))
                    current_start = None
                    current_end = None

        # Add final segment if active
        if current_start is not None:
            segments.append((current_start, current_end))

        # Filter by minimum duration
        min_duration = min_duration_ms / 1000
        filtered = [(s, e) for s, e in segments if e - s >= min_duration]

        return filtered

    def detect(
        self,
        audio_path: str | Path,
        min_duration_ms: int = VadConfig.MIN_SPEECH_DURATION_MS,
        pad_duration_ms: int = VadConfig.PAD_DURATION_MS,
    ) -> list[tuple[float, float]]:
        """
        Detect speech segments in audio.

        Args:
            audio_path: Path to audio file
            min_duration_ms: Minimum segment duration in ms
            pad_duration_ms: Padding duration in ms

        Returns:
            List of (start_time, end_time) tuples for speech segments
        """
        frames = self.detect_frames(audio_path)
        return self.merge_speech_segments(frames, min_duration_ms, pad_duration_ms)

    def get_speech_ratio(
        self,
        audio_path: str | Path,
    ) -> float:
        """
        Calculate ratio of speech to total audio duration.

        Args:
            audio_path: Path to audio file

        Returns:
            Speech ratio (0.0 to 1.0)
        """
        frames = self.detect_frames(audio_path)

        speech_frames = [f for f in frames if f.is_speech]
        speech_duration = sum(f.end_time - f.start_time for f in speech_frames)

        total_duration = frames[-1].end_time if frames else 0.0

        if total_duration == 0:
            return 0.0

        return speech_duration / total_duration


class ProbabilisticVAD:
    """
    Probabilistic VAD using pyannote.audio.

    Provides soft decisions with confidence scores.
    """

    def __init__(self, device: str = "cuda") -> None:
        """
        Initialize probabilistic VAD.

        Args:
            device: Device to use (cuda or cpu)
        """
        self.device = device
        self._pipeline = None

    def _get_pipeline(self):
        """Get VAD pipeline."""
        if self._pipeline is None:
            try:
                from pyannote.audio import Pipeline
            except ImportError as e:
                raise ImportError(
                    "pyannote-audio is required. Install with: pip install pyannote-audio"
                ) from e

            # Use pre-trained VAD model
            self._pipeline = Pipeline.from_pretrained(
                "pyannote/voice-activity-detection",
            )

            if self.device == "cuda":
                try:
                    import torch

                    if torch.cuda.is_available():
                        self._pipeline.to(torch.device("cuda"))
                except ImportError:
                    pass

        return self._pipeline

    def detect(
        self,
        audio_path: str | Path,
        _threshold: float = VadConfig.SPEECH_PROB_THRESHOLD,
    ) -> list[tuple[float, float, float]]:
        """
        Detect speech segments with probability.

        Args:
            audio_path: Path to audio file
            threshold: Speech probability threshold

        Returns:
            List of (start_time, end_time, probability) tuples
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        pipeline = self._get_pipeline()

        # Load audio
        try:
            import torch
        except ImportError as e:
            raise ImportError("PyTorch is required for pyannote VAD") from e

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

        # Run VAD
        output = pipeline({"waveform": waveform, "sample_rate": sample_rate})

        # Process output
        segments: list[tuple[float, float, float]] = []

        for region in output.get_timeline().support():
            # Get speech probability for this region
            probability = 1.0  # pyannote VAD is binary, we can simulate probability
            segments.append((float(region.start), float(region.end), probability))

        return segments
