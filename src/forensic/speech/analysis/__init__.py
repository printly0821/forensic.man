"""
Forensic Speech Analysis Subpackage

Analysis modules for emotion recognition, gaslighting detection,
and deepfake detection.
"""

from forensic.speech.analysis.deepfake import (
    CNNLSTMDeepfakeDetector,
    DeepfakeConfig,
    DeepfakeModel,
    EnsembleDeepfakeDetector,
)
from forensic.speech.analysis.emotion import (
    EmotionAnalyzer,
    EmotionConfig,
    EmotionModel,
)
from forensic.speech.analysis.gaslighting import (
    GaslightingDetector,
    GaslightingPatterns,
    GaslightingReportGenerator,
)

__all__ = [
    # Emotion
    "EmotionAnalyzer",
    "EmotionConfig",
    "EmotionModel",
    # Gaslighting
    "GaslightingDetector",
    "GaslightingPatterns",
    "GaslightingReportGenerator",
    # Deepfake
    "CNNLSTMDeepfakeDetector",
    "EnsembleDeepfakeDetector",
    "DeepfakeConfig",
    "DeepfakeModel",
]
