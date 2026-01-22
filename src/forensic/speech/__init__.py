"""
Forensic Speech Analysis Package

Comprehensive speech analysis for forensic applications including:
- Transcription with faster-whisper
- Speaker diarization with pyannote-audio
- Prosodic feature extraction with Parselmouth
- Emotion recognition (KESDy18 based)
- Gaslighting pattern detection
- Deepfake detection with CNN-LSTM
- XAI explanations with GradCAM and SHAP
- Legal report generation (Daubert standard)
"""

from forensic.speech.diarizer import DiarizationConfig, Diarizer
from forensic.speech.features import AudioFeatureExtractor, FeatureConfig
from forensic.speech.prosody import ProsodyConfig, ProsodyExtractor
from forensic.speech.transcriber import Transcriber, TranscriptionConfig
from forensic.speech.vad import ProbabilisticVAD, VadConfig, VoiceActivityDetector

__all__ = [
    # Core modules
    "Transcriber",
    "TranscriptionConfig",
    "Diarizer",
    "DiarizationConfig",
    "ProsodyExtractor",
    "ProsodyConfig",
    "VoiceActivityDetector",
    "ProbabilisticVAD",
    "VadConfig",
    "AudioFeatureExtractor",
    "FeatureConfig",
]

# Version info
__version__ = "0.1.0"
