"""
Audio Feature Extraction Module

Extracts spectral features including MFCC and LFCC for forensic analysis.
These features are used for deepfake detection and speaker verification.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class FeatureConfig:
    """Configuration for audio feature extraction."""

    # Sample rate
    SAMPLE_RATE = 16000

    # STFT settings
    N_FFT = 2048
    HOP_LENGTH = 512
    WIN_LENGTH = 2048

    # MFCC settings
    N_MFCC = 20
    N_MELS = 40
    FMIN = 20  # Hz
    FMAX = 8000  # Hz

    # LFCC settings
    N_LFCC = 20
    N_LFILT = 40

    # Delta settings
    DELTA_WIDTH = 9
    DELTA_ORDER = 2

    # Statistics
    INCLUDE_DELTA = True
    INCLUDE_DELTA_DELTA = True


class AudioFeatureExtractor:
    """
    Audio feature extractor for forensic analysis.

    Extracts MFCC, LFCC, and other spectral features.
    """

    def __init__(self, sample_rate: int = FeatureConfig.SAMPLE_RATE) -> None:
        """
        Initialize feature extractor.

        Args:
            sample_rate: Target sample rate for audio
        """
        self.sample_rate = sample_rate

    def load_audio(
        self, audio_path: str | Path, offset: float = 0.0, duration: float | None = None
    ) -> tuple[np.ndarray, int]:
        """
        Load audio file.

        Args:
            audio_path: Path to audio file
            offset: Start offset in seconds
            duration: Duration to load in seconds

        Returns:
            Tuple of (audio_data, sample_rate)
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        try:
            import librosa
        except ImportError as e:
            raise ImportError("librosa is required. Install with: pip install librosa") from e

        audio, sr = librosa.load(
            str(audio_path),
            sr=self.sample_rate,
            offset=offset,
            duration=duration,
            mono=True,
        )

        return audio, sr

    def extract_mfcc(
        self,
        audio: np.ndarray,
        n_mfcc: int = FeatureConfig.N_MFCC,
        n_mels: int = FeatureConfig.N_MELS,
        n_fft: int = FeatureConfig.N_FFT,
        hop_length: int = FeatureConfig.HOP_LENGTH,
        win_length: int = FeatureConfig.WIN_LENGTH,
    ) -> np.ndarray:
        """
        Extract Mel-Frequency Cepstral Coefficients (MFCC).

        MFCCs are widely used in speech recognition and speaker identification.

        Args:
            audio: Audio signal
            n_mfcc: Number of MFCC coefficients
            n_mels: Number of mel bands
            n_fft: FFT size
            hop_length: Hop length for STFT
            win_length: Window length for STFT

        Returns:
            MFCC features with shape (n_mfcc, n_frames)
        """
        try:
            import librosa
        except ImportError as e:
            raise ImportError("librosa is required") from e

        mfcc = librosa.feature.mfcc(
            y=audio,
            sr=self.sample_rate,
            n_mfcc=n_mfcc,
            n_mels=n_mels,
            n_fft=n_fft,
            hop_length=hop_length,
            win_length=win_length,
            fmin=FeatureConfig.FMIN,
            fmax=FeatureConfig.FMAX,
        )

        return mfcc

    def extract_lfcc(
        self,
        audio: np.ndarray,
        n_lfcc: int = FeatureConfig.N_LFCC,
        n_lfilt: int = FeatureConfig.N_LFILT,
        n_fft: int = FeatureConfig.N_FFT,
        hop_length: int = FeatureConfig.HOP_LENGTH,
        win_length: int = FeatureConfig.WIN_LENGTH,
    ) -> np.ndarray:
        """
        Extract Linear-Frequency Cepstral Coefficients (LFCC).

        LFCCs are useful for detecting synthetic speech and deepfakes.

        Args:
            audio: Audio signal
            n_lfcc: Number of LFCC coefficients
            n_lfilt: Number of linear filters
            n_fft: FFT size
            hop_length: Hop length for STFT
            win_length: Window length for STFT

        Returns:
            LFCC features with shape (n_lfcc, n_frames)
        """
        # Compute STFT
        try:
            import librosa
        except ImportError as e:
            raise ImportError("librosa is required") from e

        stft = librosa.stft(
            y=audio,
            n_fft=n_fft,
            hop_length=hop_length,
            win_length=win_length,
            window="hamming",
        )

        # Power spectrum
        power = np.abs(stft) ** 2

        # Create linear filterbank
        linear_filters = self._create_linear_filterbank(
            n_lfilt,
            n_fft // 2 + 1,
            FeatureConfig.FMIN,
            min(self.sample_rate // 2, FeatureConfig.FMAX),
        )

        # Apply filters
        linear_energy = np.dot(linear_filters, power)

        # Log compression
        linear_log = np.log(linear_energy + 1e-10)

        # DCT to get cepstral coefficients
        lfcc = self._dct(linear_log, type=2, axis=0, norm="ortho")[:n_lfcc]

        return lfcc

    def extract_spectral_centroid(
        self,
        audio: np.ndarray,
        n_fft: int = FeatureConfig.N_FFT,
        hop_length: int = FeatureConfig.HOP_LENGTH,
    ) -> np.ndarray:
        """
        Extract spectral centroid.

        Measures the "center of mass" of the spectrum.

        Args:
            audio: Audio signal
            n_fft: FFT size
            hop_length: Hop length

        Returns:
            Spectral centroid over time
        """
        try:
            import librosa
        except ImportError as e:
            raise ImportError("librosa is required") from e

        return librosa.feature.spectral_centroid(
            y=audio,
            sr=self.sample_rate,
            n_fft=n_fft,
            hop_length=hop_length,
        )[0]

    def extract_spectral_rolloff(
        self,
        audio: np.ndarray,
        n_fft: int = FeatureConfig.N_FFT,
        hop_length: int = FeatureConfig.HOP_LENGTH,
        roll_percent: float = 0.85,
    ) -> np.ndarray:
        """
        Extract spectral rolloff point.

        Frequency below which roll_percent of energy is contained.

        Args:
            audio: Audio signal
            n_fft: FFT size
            hop_length: Hop length
            roll_percent: Rolloff percentage

        Returns:
            Spectral rolloff over time
        """
        try:
            import librosa
        except ImportError as e:
            raise ImportError("librosa is required") from e

        return librosa.feature.spectral_rolloff(
            y=audio,
            sr=self.sample_rate,
            n_fft=n_fft,
            hop_length=hop_length,
            roll_percent=roll_percent,
        )[0]

    def extract_zero_crossing_rate(
        self,
        audio: np.ndarray,
        frame_length: int = 2048,
        hop_length: int = FeatureConfig.HOP_LENGTH,
    ) -> np.ndarray:
        """
        Extract zero crossing rate.

        Measures rate at which signal changes sign.

        Args:
            audio: Audio signal
            frame_length: Frame length
            hop_length: Hop length

        Returns:
            Zero crossing rate over time
        """
        try:
            import librosa
        except ImportError as e:
            raise ImportError("librosa is required") from e

        return librosa.feature.zero_crossing_rate(
            y=audio,
            frame_length=frame_length,
            hop_length=hop_length,
        )[0]

    def extract_delta(
        self,
        features: np.ndarray,
        width: int = FeatureConfig.DELTA_WIDTH,
        order: int = 1,
    ) -> np.ndarray:
        """
        Compute delta (derivative) features.

        Args:
            features: Feature matrix (n_features, n_frames)
            width: Width for delta computation
            order: Order of delta (1 = delta, 2 = delta-delta)

        Returns:
            Delta features
        """
        try:
            import librosa
        except ImportError as e:
            raise ImportError("librosa is required") from e

        if order == 1:
            return librosa.feature.delta(features, order=1, width=width)
        elif order == 2:
            return librosa.feature.delta(features, order=2, width=width)
        else:
            raise ValueError(f"Unsupported delta order: {order}")

    def extract_all_features(
        self,
        audio_path: str | Path,
        include_delta: bool = FeatureConfig.INCLUDE_DELTA,
        include_delta_delta: bool = FeatureConfig.INCLUDE_DELTA_DELTA,
    ) -> dict[str, np.ndarray]:
        """
        Extract all available features.

        Args:
            audio_path: Path to audio file
            include_delta: Include delta features
            include_delta_delta: Include delta-delta features

        Returns:
            Dictionary with all extracted features
        """
        audio, _ = self.load_audio(audio_path)

        features: dict[str, np.ndarray] = {}

        # Static features
        features["mfcc"] = self.extract_mfcc(audio)
        features["lfcc"] = self.extract_lfcc(audio)
        features["spectral_centroid"] = self.extract_spectral_centroid(audio)
        features["spectral_rolloff"] = self.extract_spectral_rolloff(audio)
        features["zcr"] = self.extract_zero_crossing_rate(audio)

        # Delta features
        if include_delta:
            features["mfcc_delta"] = self.extract_delta(features["mfcc"], order=1)
            features["lfcc_delta"] = self.extract_delta(features["lfcc"], order=1)

        # Delta-delta features
        if include_delta_delta:
            features["mfcc_delta_delta"] = self.extract_delta(features["mfcc"], order=2)
            features["lfcc_delta_delta"] = self.extract_delta(features["lfcc"], order=2)

        return features

    def compute_feature_statistics(
        self,
        features: np.ndarray,
    ) -> dict[str, float]:
        """
        Compute statistics for feature matrix.

        Args:
            features: Feature matrix (n_features, n_frames)

        Returns:
            Dictionary with feature statistics
        """
        return {
            "mean": float(np.mean(features)),
            "std": float(np.std(features)),
            "min": float(np.min(features)),
            "max": float(np.max(features)),
            "median": float(np.median(features)),
            "q25": float(np.percentile(features, 25)),
            "q75": float(np.percentile(features, 75)),
        }

    def _create_linear_filterbank(
        self,
        n_filters: int,
        n_fft_bins: int,
        fmin: float,
        fmax: float,
    ) -> np.ndarray:
        """
        Create linear filterbank for LFCC.

        Args:
            n_filters: Number of filters
            n_fft_bins: Number of FFT bins
            fmin: Minimum frequency
            fmax: Maximum frequency

        Returns:
            Filterbank matrix
        """
        # Linear spacing between fmin and fmax
        freq_points = np.linspace(fmin, fmax, n_filters + 2)

        # Convert to bin indices
        bin_points = np.floor((n_fft_bins - 1) * freq_points / (self.sample_rate / 2)).astype(int)

        # Create filters
        filters = np.zeros((n_filters, n_fft_bins))

        for i in range(n_filters):
            # Rising edge
            left = bin_points[i]
            center = bin_points[i + 1]
            right = bin_points[i + 2]

            for j in range(left, center):
                filters[i, j] = (j - left) / (center - left)

            for j in range(center, right):
                filters[i, j] = (right - j) / (right - center)

        return filters

    @staticmethod
    def _dct(x: np.ndarray, type: int = 2, axis: int = -1, norm: str | None = None) -> np.ndarray:
        """
        Compute Discrete Cosine Transform.

        Args:
            x: Input array
            type: DCT type (1-4)
            axis: Axis along which to compute DCT
            norm: Normalization mode

        Returns:
            DCT of input
        """
        try:
            from scipy.fftpack import dct
        except ImportError as e:
            raise ImportError("scipy is required for DCT computation") from e

        return dct(x, type=type, axis=axis, norm=norm)
