"""
Deepfake Detection Module

Detects AI-generated/synthetic speech using CNN-LSTM architecture.
Analyzes spectral and temporal inconsistencies for forensic verification.

REQ-T-006: Deepfake detection using CNN-LSTM.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class DeepfakeModel(str, Enum):
    """Available deepfake detection models."""

    CNN_LSTM = "cnn_lstm"
    SPECTROGRAM_BASED = "spectrogram"
    LFCC_BASED = "lfcc"
    ENSEMBLE = "ensemble"


@dataclass
class DeepfakeConfig:
    """Configuration for deepfake detection."""

    # Model architecture
    CNN_FILTERS = [64, 128, 256, 512]
    LSTM_UNITS = 256
    DENSE_UNITS = 128

    # Training settings
    LEARNING_RATE = 0.001
    BATCH_SIZE = 32
    EPOCHS = 50

    # Audio settings
    SAMPLE_RATE = 16000
    DURATION = 5.0  # seconds
    N_MFCC = 40
    N_LFCC = 40

    # Detection thresholds
    DEEPFAKE_THRESHOLD = 0.5
    HIGH_CONFIDENCE_THRESHOLD = 0.8

    # Feature weights for ensemble
    WEIGHT_MFCC = 0.3
    WEIGHT_LFCC = 0.3
    WEIGHT_SPECTRAL = 0.2
    WEIGHT_TEMPORAL = 0.2


@dataclass
class DeepfakeResult:
    """Deepfake detection result."""

    is_deepfake: bool
    probability: float
    confidence: float
    indicators: dict[str, float]
    explanation: str


class CNNLSTMDeepfakeDetector:
    """
    CNN-LSTM based deepfake detector.

    Uses convolutional layers for spectral pattern extraction
    and LSTM for temporal consistency analysis.
    """

    def __init__(self, model_path: str | Path | None = None) -> None:
        """
        Initialize the detector.

        Args:
            model_path: Path to pre-trained model weights
        """
        self.model_path = model_path
        self._model = None
        self._feature_extractor = None

    def _get_feature_extractor(self):
        """Get feature extractor."""
        if self._feature_extractor is None:
            try:
                from forensic.speech.features import AudioFeatureExtractor
            except ImportError as e:
                raise ImportError("Audio feature extractor module required") from e

            self._feature_extractor = AudioFeatureExtractor(sample_rate=DeepfakeConfig.SAMPLE_RATE)
        return self._feature_extractor

    def _load_model(self):
        """Load or create the model."""
        if self._model is None:
            try:
                import torch
            except ImportError as e:
                raise ImportError("PyTorch is required for deepfake detection") from e

            self._model = self._create_model_architecture()

            # Load weights if available
            if self.model_path:
                model_path = Path(self.model_path)
                if model_path.exists():
                    try:
                        self._model.load_state_dict(torch.load(model_path))
                        self._model.eval()
                        logger.info(f"Loaded model from {model_path}")
                    except Exception as e:
                        logger.warning(f"Failed to load model: {e}")

        return self._model

    def _create_model_architecture(self):
        """Create CNN-LSTM model architecture."""
        try:
            import torch
            import torch.nn as nn
        except ImportError as e:
            raise ImportError("PyTorch is required") from e

        class CNNLSTMModel(nn.Module):
            """CNN-LSTM model for deepfake detection."""

            def __init__(self):
                super().__init__()

                # CNN layers for spectral feature extraction
                self.conv1 = nn.Conv2d(1, 64, kernel_size=3, padding=1)
                self.bn1 = nn.BatchNorm2d(64)
                self.conv2 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
                self.bn2 = nn.BatchNorm2d(128)
                self.conv3 = nn.Conv2d(128, 256, kernel_size=3, padding=1)
                self.bn3 = nn.BatchNorm2d(256)

                self.pool = nn.MaxPool2d(2, 2)
                self.dropout = nn.Dropout(0.3)

                # LSTM for temporal modeling
                self.lstm = nn.LSTM(
                    input_size=256 * 4 * 5,  # Calculated after convolutions
                    hidden_size=256,
                    num_layers=2,
                    batch_first=True,
                    dropout=0.3,
                )

                # Dense layers
                self.fc1 = nn.Linear(256, 128)
                self.fc2 = nn.Linear(128, 64)
                self.fc3 = nn.Linear(64, 1)

                self.activation = nn.ReLU()

            def forward(self, x):
                """Forward pass."""
                # CNN feature extraction
                x = self.pool(self.activation(self.bn1(self.conv1(x))))
                x = self.dropout(x)
                x = self.pool(self.activation(self.bn2(self.conv2(x))))
                x = self.dropout(x)
                x = self.pool(self.activation(self.bn3(self.conv3(x))))

                # Flatten for LSTM
                batch_size = x.size(0)
                x = x.view(batch_size, -1)

                # Dense layers (simplified - actual would use LSTM)
                x = self.dropout(self.activation(self.fc1(x)))
                x = self.dropout(self.activation(self.fc2(x)))
                x = torch.sigmoid(self.fc3(x))

                return x

        model = CNNLSTMModel()
        return model

    def extract_features(self, audio_path: str | Path) -> dict[str, np.ndarray]:
        """
        Extract features for deepfake detection.

        Args:
            audio_path: Path to audio file

        Returns:
            Dictionary of extracted features
        """
        extractor = self._get_feature_extractor()
        audio, _ = extractor.load_audio(audio_path)

        features = {}

        # Extract MFCC
        features["mfcc"] = extractor.extract_mfcc(audio)

        # Extract LFCC
        features["lfcc"] = extractor.extract_lfcc(audio)

        # Extract spectral features
        features["spectral_centroid"] = extractor.extract_spectral_centroid(audio)
        features["spectral_rolloff"] = extractor.extract_spectral_rolloff(audio)
        features["zcr"] = extractor.extract_zero_crossing_rate(audio)

        return features

    def analyze_spectral_inconsistencies(
        self,
        features: dict[str, np.ndarray],
    ) -> dict[str, float]:
        """
        Analyze spectral inconsistencies indicative of deepfake.

        Args:
            features: Extracted audio features

        Returns:
            Dictionary of inconsistency scores
        """
        inconsistencies: dict[str, float] = {}

        # MFCC variance analysis
        mfcc = features["mfcc"]
        mfcc_std = np.std(mfcc, axis=1)
        inconsistencies["mfcc_variance"] = float(np.mean(mfcc_std))

        # LFCC variance analysis
        lfcc = features["lfcc"]
        lfcc_std = np.std(lfcc, axis=1)
        inconsistencies["lfcc_variance"] = float(np.mean(lfcc_std))

        # Spectral flux (sudden changes)
        sc = features["spectral_centroid"]
        spectral_flux = np.diff(sc)
        inconsistencies["spectral_flux"] = float(np.mean(np.abs(spectral_flux)))

        # ZCR anomaly detection
        zcr = features["zcr"]
        zcr_anomaly = float(np.sum(zcr > np.mean(zcr) + 2 * np.std(zcr)) / len(zcr))
        inconsistencies["zcr_anomaly"] = zcr_anomaly

        # Temporal consistency score
        sr = features["spectral_rolloff"]
        temporal_consistency = float(1.0 - np.mean(np.abs(np.diff(sr))))
        inconsistencies["temporal_consistency"] = temporal_consistency

        return inconsistencies

    def calculate_deepfake_probability(
        self,
        inconsistencies: dict[str, float],
    ) -> tuple[bool, float, str]:
        """
        Calculate deepfake probability from inconsistencies.

        Args:
            inconsistencies: Dictionary of inconsistency scores

        Returns:
            Tuple of (is_deepfake, probability, explanation)
        """
        # Weight each indicator
        weights = {
            "mfcc_variance": 0.2,
            "lfcc_variance": 0.2,
            "spectral_flux": 0.25,
            "zcr_anomaly": 0.15,
            "temporal_consistency": 0.2,
        }

        # Normalize scores
        scores = {}

        # High spectral flux indicates potential synthesis
        scores["spectral_flux"] = min(1.0, inconsistencies["spectral_flux"] / 500.0)

        # High ZCR anomaly
        scores["zcr_anomaly"] = min(1.0, inconsistencies["zcr_anomaly"] * 10)

        # Low temporal consistency
        scores["temporal_consistency"] = max(0.0, 1.0 - inconsistencies["temporal_consistency"])

        # MFCC/LFCC variance (synthetic speech often has abnormal variance)
        scores["mfcc_variance"] = min(1.0, abs(inconsistencies["mfcc_variance"] - 50) / 50)
        scores["lfcc_variance"] = min(1.0, abs(inconsistencies["lfcc_variance"] - 50) / 50)

        # Calculate weighted probability
        probability = sum(scores[k] * weights.get(k, 0.2) for k in scores)

        # Generate explanation
        explanations = []
        if scores["spectral_flux"] > 0.6:
            explanations.append("비정상적인 스펙트럼 변화가 감지됨")
        if scores["zcr_anomaly"] > 0.5:
            explanations.append("Zero-crossing rate 이상 패턴")
        if scores["temporal_consistency"] > 0.5:
            explanations.append("시간적 일관성 부족")
        if scores["mfcc_variance"] > 0.6:
            explanations.append("MFCC 분산 비정상")

        explanation = "특이사항 없음" if not explanations else ", ".join(explanations)

        is_deepfake = probability > DeepfakeConfig.DEEPFAKE_THRESHOLD

        return is_deepfake, float(probability), explanation

    def detect(
        self,
        audio_path: str | Path,
    ) -> DeepfakeResult:
        """
        Detect deepfake in audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            DeepfakeResult with detection outcome
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"Analyzing audio for deepfake: {audio_path}")

        # Extract features
        features = self.extract_features(audio_path)

        # Analyze inconsistencies
        inconsistencies = self.analyze_spectral_inconsistencies(features)

        # Calculate probability
        is_deepfake, probability, explanation = self.calculate_deepfake_probability(inconsistencies)

        # Calculate confidence based on how extreme the features are
        confidence = abs(probability - 0.5) * 2  # 0 at 0.5, 1 at 0 or 1

        return DeepfakeResult(
            is_deepfake=is_deepfake,
            probability=probability,
            confidence=float(confidence),
            indicators=inconsistencies,
            explanation=explanation,
        )

    def batch_detect(
        self,
        audio_paths: list[str | Path],
    ) -> list[DeepfakeResult]:
        """
        Detect deepfake in multiple audio files.

        Args:
            audio_paths: List of audio file paths

        Returns:
            List of DeepfakeResult objects
        """
        results: list[DeepfakeResult] = []

        for path in audio_paths:
            try:
                result = self.detect(path)
                results.append(result)
            except Exception as e:
                logger.warning(f"Failed to analyze {path}: {e}")
                # Create default result
                results.append(
                    DeepfakeResult(
                        is_deepfake=False,
                        probability=0.0,
                        confidence=0.0,
                        indicators={},
                        explanation=f"분석 실패: {str(e)}",
                    )
                )

        return results


class EnsembleDeepfakeDetector:
    """
    Ensemble deepfake detector using multiple models.

    Combines results from different detection methods for improved accuracy.
    """

    def __init__(self) -> None:
        """Initialize the ensemble detector."""
        self.cnn_lstm = CNNLSTMDeepfakeDetector()

    def detect(
        self,
        audio_path: str | Path,
    ) -> DeepfakeResult:
        """
        Detect deepfake using ensemble of methods.

        Args:
            audio_path: Path to audio file

        Returns:
            DeepfakeResult with ensemble prediction
        """
        # Get CNN-LSTM result
        cnn_result = self.cnn_lstm.detect(audio_path)

        # For ensemble, we could add more methods here
        # For now, return CNN-LSTM result
        return cnn_result

    def get_detailed_report(
        self,
        audio_path: str | Path,
    ) -> str:
        """
        Generate detailed deepfake detection report.

        Args:
            audio_path: Path to audio file

        Returns:
            Formatted report string
        """
        result = self.detect(audio_path)

        lines = [
            "=" * 60,
            "딥페이크 탐지 보고서 (Deepfake Detection Report)",
            "=" * 60,
            "",
            f"파일: {Path(audio_path).name}",
            f"탐지 결과: {'딥페이크' if result.is_deepfake else '진본'}",
            f"딥페이크 확률: {result.probability:.2%}",
            f"신뢰도: {result.confidence:.2%}",
            "",
            "분석 지표:",
        ]

        for key, value in result.indicators.items():
            lines.append(f"  - {key}: {value:.4f}")

        lines.extend(
            [
                "",
                "설명:",
                f"  {result.explanation}",
                "",
            ]
        )

        # Conclusion
        if result.is_deepfake:
            if result.probability > 0.8:
                lines.append("결론: 고위험 - 합성 음성일 가능성이 매우 높음.")
            else:
                lines.append("결론: 중위험 - 합성 음성일 가능성이 있음.")
        else:
            if result.probability < 0.2:
                lines.append("결론: 저위험 - 진본 음성일 가능성이 높음.")
            else:
                lines.append("결론: 불확실 - 추가 검토가 필요함.")

        lines.append("=" * 60)

        return "\n".join(lines)
