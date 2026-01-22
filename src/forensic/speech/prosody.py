"""
Prosodic Feature Extraction Module

Uses Parselmouth to extract prosodic features from speech.
Provides F0, Jitter, Shimmer, HNR analysis for forensic applications.

REQ-T-003: Prosody analysis using Parselmouth.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from forensic.models.speech import ProsodyFeatures

logger = logging.getLogger(__name__)


class ProsodyConfig:
    """Configuration for prosodic feature extraction."""

    # Praat/Parselmouth settings
    TIME_STEP = 0.01  # Time step for analysis (seconds)
    PITCH_FLOOR = 75.0  # Hz
    PITCH_CEILING = 500.0  # Hz
    FORMANT_WINDOW_SIZE = 0.025  # seconds
    FORMANT_NUMBER = 5

    # Jitter/Shimmer settings
    JITTER_LOCAL = True
    JITTER_LOCAL_ABS = True
    JITTER_RAP = True
    JITTER_PPQ5 = True
    JITTER_DDP = True

    SHIMMER_LOCAL = True
    SHIMMER_LOCAL_DB = True
    SHIMMER_APQ3 = True
    SHIMMER_APQ5 = True
    SHIMMER_APQ11 = True
    SHIMMER_DDA = True

    # HNR settings
    HNR_FLOOR = 75.0
    HNR_CEILING = 500.0


class ProsodyExtractor:
    """
    Prosodic feature extractor using Parselmouth.

    Extracts F0, jitter, shimmer, and HNR features for forensic analysis.
    """

    def __init__(self) -> None:
        """Initialize the prosody extractor."""
        self._sound_class = None

    def _get_sound_class(self):
        """Get Parselmouth Sound class lazily."""
        if self._sound_class is None:
            try:
                import parselmouth

                self._sound_class = parselmouth.Sound
            except ImportError as e:
                raise ImportError(
                    "parselmouth is required. Install with: pip install parselmouth"
                ) from e
        return self._sound_class

    def load_audio(self, audio_path: str | Path):
        """
        Load audio file as Parselmouth Sound.

        Args:
            audio_path: Path to audio file

        Returns:
            Parselmouth Sound object
        """
        Sound = self._get_sound_class()

        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"Loading audio for prosody analysis: {audio_path}")
        return Sound(str(audio_path))

    def extract_f0(self, sound, time_step: float = ProsodyConfig.TIME_STEP) -> np.ndarray:
        """
        Extract fundamental frequency (F0) contour.

        Args:
            sound: Parselmouth Sound object
            time_step: Time step for analysis (seconds)

        Returns:
            F0 values as numpy array
        """
        pitch = sound.to_pitch_ac(
            time_step=time_step,
            pitch_floor=ProsodyConfig.PITCH_FLOOR,
            pitch_ceiling=ProsodyConfig.PITCH_CEILING,
        )

        f0_values = pitch.selected_array["frequency"]
        # Replace unvoiced (0) with NaN
        f0_values[f0_values == 0] = np.nan

        return f0_values

    def extract_f0_stats(
        self, sound, time_step: float = ProsodyConfig.TIME_STEP
    ) -> dict[str, float]:
        """
        Extract F0 statistics.

        Args:
            sound: Parselmouth Sound object
            time_step: Time step for analysis (seconds)

        Returns:
            Dictionary with F0 statistics
        """
        f0_values = self.extract_f0(sound, time_step)
        voiced_f0 = f0_values[~np.isnan(f0_values)]

        if len(voiced_f0) == 0:
            return {
                "f0_mean": 0.0,
                "f0_std": 0.0,
                "f0_min": 0.0,
                "f0_max": 0.0,
                "f0_range": 0.0,
                "voicing_rate": 0.0,
            }

        return {
            "f0_mean": float(np.mean(voiced_f0)),
            "f0_std": float(np.std(voiced_f0)),
            "f0_min": float(np.min(voiced_f0)),
            "f0_max": float(np.max(voiced_f0)),
            "f0_range": float(np.max(voiced_f0) - np.min(voiced_f0)),
            "voicing_rate": float(len(voiced_f0) / len(f0_values)),
        }

    def extract_jitter(self, sound) -> dict[str, float]:
        """
        Extract jitter (frequency perturbation) measures.

        Args:
            sound: Parselmouth Sound object

        Returns:
            Dictionary with jitter measures
        """
        point_process = sound.to_pitch().to_point_process()

        try:
            local_jitter = call(point_process, "Get jitter (local)", 0.0, 0.0, 0.0001, 0.02, 1.3)
        except Exception:
            local_jitter = 0.0

        try:
            local_abs_jitter = call(
                point_process, "Get jitter (local, absolute)", 0.0, 0.0, 0.0001, 0.02, 1.3
            )
        except Exception:
            local_abs_jitter = 0.0

        try:
            rap_jitter = call(point_process, "Get jitter (rap)", 0.0, 0.0, 0.0001, 0.02, 1.3)
        except Exception:
            rap_jitter = 0.0

        try:
            ppq5_jitter = call(point_process, "Get jitter (ppq5)", 0.0, 0.0, 0.0001, 0.02, 1.3)
        except Exception:
            ppq5_jitter = 0.0

        try:
            ddp_jitter = call(point_process, "Get jitter (ddp)", 0.0, 0.0, 0.0001, 0.02, 1.3)
        except Exception:
            ddp_jitter = 0.0

        return {
            "jitter_local": local_jitter * 100,  # Convert to percentage
            "jitter_local_abs": local_abs_jitter * 1000000,  # Convert to microseconds
            "jitter_rap": rap_jitter * 100,
            "jitter_ppq5": ppq5_jitter * 100,
            "jitter_ddp": ddp_jitter * 100,
        }

    def extract_shimmer(self, sound) -> dict[str, float]:
        """
        Extract shimmer (amplitude perturbation) measures.

        Args:
            sound: Parselmouth Sound object

        Returns:
            Dictionary with shimmer measures
        """
        point_process = sound.to_pitch().to_point_process()

        try:
            local_shimmer = call(
                [sound, point_process],
                "Get shimmer (local)",
                0.0,
                0.0,
                0.0001,
                0.02,
                1.3,
                1.6,
            )
        except Exception:
            local_shimmer = 0.0

        try:
            local_db_shimmer = call(
                [sound, point_process],
                "Get shimmer (local_dB)",
                0.0,
                0.0,
                0.0001,
                0.02,
                1.3,
                1.6,
            )
        except Exception:
            local_db_shimmer = 0.0

        try:
            apq3_shimmer = call(
                [sound, point_process],
                "Get shimmer (apq3)",
                0.0,
                0.0,
                0.0001,
                0.02,
                1.3,
                1.6,
            )
        except Exception:
            apq3_shimmer = 0.0

        try:
            apq5_shimmer = call(
                [sound, point_process],
                "Get shimmer (apq5)",
                0.0,
                0.0,
                0.0001,
                0.02,
                1.3,
                1.6,
            )
        except Exception:
            apq5_shimmer = 0.0

        try:
            apq11_shimmer = call(
                [sound, point_process],
                "Get shimmer (apq11)",
                0.0,
                0.0,
                0.0001,
                0.02,
                1.3,
                1.6,
            )
        except Exception:
            apq11_shimmer = 0.0

        try:
            dda_shimmer = call(
                [sound, point_process],
                "Get shimmer (dda)",
                0.0,
                0.0,
                0.0001,
                0.02,
                1.3,
                1.6,
            )
        except Exception:
            dda_shimmer = 0.0

        return {
            "shimmer_local": local_shimmer * 100,
            "shimmer_local_db": local_db_shimmer,
            "shimmer_apq3": apq3_shimmer * 100,
            "shimmer_apq5": apq5_shimmer * 100,
            "shimmer_apq11": apq11_shimmer * 100,
            "shimmer_dda": dda_shimmer * 100,
        }

    def extract_hnr(self, sound) -> dict[str, float]:
        """
        Extract harmonics-to-noise ratio (HNR).

        Args:
            sound: Parselmouth Sound object

        Returns:
            Dictionary with HNR measures
        """
        try:
            harmonicness = call(
                sound,
                "To Harmonicity (cc)",
                ProsodyConfig.HNR_FLOOR,
                ProsodyConfig.HNR_CEILING,
                0.01,
                0.5,
                1.0,
            )

            mean_hnr = call(harmonicness, "Get mean", 0.0, 0.0)
            std_hnr = call(harmonicness, "Get standard deviation", 0.0, 0.0)
        except Exception:
            mean_hnr = 0.0
            std_hnr = 0.0

        return {
            "hnr_mean": float(mean_hnr),
            "hnr_std": float(std_hnr),
        }

    def extract_from_segment(
        self,
        audio_path: str | Path,
        start_time: float,
        end_time: float,
        segment_id: str,
    ) -> ProsodyFeatures:
        """
        Extract prosodic features from a time segment.

        Args:
            audio_path: Path to audio file
            start_time: Start time in seconds
            end_time: End time in seconds
            segment_id: Segment identifier

        Returns:
            ProsodyFeatures object with extracted features
        """
        sound = self.load_audio(audio_path)

        # Extract segment
        start_sample = int(start_time * sound.sampling_frequency)
        end_sample = int(end_time * sound.sampling_frequency)
        segment = sound.extract_part(start_sample, end_sample)

        # Extract features
        f0_stats = self.extract_f0_stats(segment)
        jitter_stats = self.extract_jitter(segment)
        shimmer_stats = self.extract_shimmer(segment)
        hnr_stats = self.extract_hnr(segment)

        return ProsodyFeatures(
            segment_id=segment_id,
            f0_mean=f0_stats["f0_mean"],
            f0_std=f0_stats["f0_std"],
            f0_min=f0_stats["f0_min"],
            f0_max=f0_stats["f0_max"],
            f0_range=f0_stats["f0_range"],
            jitter=jitter_stats.get("jitter_local", 0.0),
            shimmer=shimmer_stats.get("shimmer_local", 0.0),
            hnr=hnr_stats.get("hnr_mean", 0.0),
        )

    def extract_from_audio(self, audio_path: str | Path, segments: list) -> list[ProsodyFeatures]:
        """
        Extract prosodic features for all segments.

        Args:
            audio_path: Path to audio file
            segments: List of segments with start_time, end_time, id

        Returns:
            List of ProsodyFeatures for each segment
        """
        results: list[ProsodyFeatures] = []

        for seg in segments:
            try:
                features = self.extract_from_segment(
                    audio_path,
                    seg.start_time,
                    seg.end_time,
                    seg.id,
                )
                results.append(features)
            except Exception as e:
                logger.warning(f"Failed to extract prosody for {seg.id}: {e}")
                # Create empty features
                results.append(
                    ProsodyFeatures(
                        segment_id=seg.id,
                        f0_mean=0.0,
                        f0_std=0.0,
                        f0_min=0.0,
                        f0_max=0.0,
                        f0_range=0.0,
                        jitter=0.0,
                        shimmer=0.0,
                        hnr=0.0,
                    )
                )

        return results


def call(*args):
    """
    Helper function to call Praat commands from Parselmouth.

    This is a simplified version - in production, use proper Parselmouth API.
    """
    try:
        import parselmouth

        return parselmouth.praat.call(*args)
    except Exception:
        return 0.0
