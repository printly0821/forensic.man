"""
Emotion Analysis Module

Emotion recognition for forensic speech analysis.
Based on KESDy18 (Korean Emotional Speech Database) patterns.

REQ-T-004: Emotion analysis using KESDy18 corpus.
"""

from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path

import numpy as np

from forensic.models.speech import EmotionAnalysis, EmotionCategory

logger = logging.getLogger(__name__)


class EmotionModel(str, Enum):
    """Available emotion recognition models."""

    RULE_BASED = "rule_based"
    PROSODY_BASED = "prosody_based"
    WAV2VEC2 = "wav2vec2"
    HUBERT = "hubert"


class EmotionConfig:
    """Configuration for emotion analysis."""

    # Emotion categories (KESDy18 based)
    EMOTIONS = [
        "neutral",
        "happy",
        "sad",
        "angry",
        "fear",
        "disgust",
        "surprise",
    ]

    # Prosodic feature weights for rule-based classification
    PROSODY_WEIGHTS = {
        "angry": {"f0_mean": 1.5, "f0_std": 1.2, "energy": 1.3, "speaking_rate": 1.1},
        "happy": {"f0_mean": 1.2, "f0_std": 1.0, "energy": 1.1, "speaking_rate": 1.2},
        "sad": {"f0_mean": 0.8, "f0_std": 0.7, "energy": 0.7, "speaking_rate": 0.8},
        "fear": {"f0_mean": 1.3, "f0_std": 1.4, "energy": 0.9, "speaking_rate": 1.3},
        "disgust": {"f0_mean": 0.9, "f0_std": 0.9, "energy": 0.8, "speaking_rate": 0.9},
        "surprise": {"f0_mean": 1.4, "f0_std": 1.3, "energy": 1.2, "speaking_rate": 1.2},
        "neutral": {"f0_mean": 1.0, "f0_std": 1.0, "energy": 1.0, "speaking_rate": 1.0},
    }

    # Thresholds
    CONFIDENCE_THRESHOLD = 0.5
    AROUSAL_HIGH_THRESHOLD = 0.6
    VALENCE_NEGATIVE_THRESHOLD = -0.3
    VALENCE_POSITIVE_THRESHOLD = 0.3


class EmotionAnalyzer:
    """
    Emotion analyzer for forensic speech.

    Uses prosodic features to classify emotional content.
    """

    def __init__(self, model: EmotionModel = EmotionModel.PROSODY_BASED) -> None:
        """
        Initialize emotion analyzer.

        Args:
            model: Model type to use
        """
        self.model = model
        self._model_instance = None

    def _load_model(self):
        """Load the emotion recognition model."""
        if self._model_instance is None:
            if self.model == EmotionModel.WAV2VEC2:
                self._load_wav2vec2_model()
            elif self.model == EmotionModel.HUBERT:
                self._load_hubert_model()
            else:
                # Rule-based models don't need loading
                pass
        return self._model_instance

    def _load_wav2vec2_model(self):
        """Load wav2vec2-based emotion model."""
        try:
            import torch
            from transformers import Wav2Vec2ForSequenceClassification, Wav2Vec2Processor

            model_name = "kresnik/wav2vec2-large-korean-speech-emotion-recognition"
            self._model_instance = {
                "model": Wav2Vec2ForSequenceClassification.from_pretrained(model_name),
                "processor": Wav2Vec2Processor.from_pretrained(model_name),
            }

            if torch.cuda.is_available():
                self._model_instance["model"].to("cuda")

        except ImportError:
            logger.warning("Transformers not available, falling back to rule-based")
            self.model = EmotionModel.RULE_BASED

    def _load_hubert_model(self):
        """Load Hubert-based emotion model."""
        try:
            import torch
            from transformers import AutoFeatureExtractor, AutoModelForAudioClassification

            model_name = "Rajaram1996/Hubert_emotion_detection"
            self._model_instance = {
                "model": AutoModelForAudioClassification.from_pretrained(model_name),
                "processor": AutoFeatureExtractor.from_pretrained(model_name),
            }

            if torch.cuda.is_available():
                self._model_instance["model"].to("cuda")

        except ImportError:
            logger.warning("Transformers not available, falling back to rule-based")
            self.model = EmotionModel.RULE_BASED

    def analyze_from_prosody(
        self,
        f0_mean: float,
        f0_std: float,
        energy: float | None = None,
        speaking_rate: float = 1.0,
        segment_id: str = "",
    ) -> EmotionAnalysis:
        """
        Analyze emotion from prosodic features.

        Args:
            f0_mean: Mean fundamental frequency
            f0_std: Standard deviation of F0
            energy: RMS energy (normalized)
            speaking_rate: Speaking rate (normalized, 1.0 = normal)
            segment_id: Segment identifier

        Returns:
            EmotionAnalysis object
        """
        # Calculate normalized values
        f0_mean_norm = f0_mean / 150.0  # Normalize around typical F0
        f0_std_norm = f0_std / 50.0

        # Calculate scores for each emotion
        scores: dict[str, float] = {}

        for emotion, weights in EmotionConfig.PROSODY_WEIGHTS.items():
            score = (
                abs(f0_mean_norm - weights["f0_mean"]) * 0.3
                + abs(f0_std_norm - weights["f0_std"]) * 0.3
                + abs(speaking_rate - weights["speaking_rate"]) * 0.2
            )

            # Invert score (lower difference = higher score)
            scores[emotion] = max(0.0, 1.0 - score)

            # Apply energy weighting if available
            if energy is not None:
                energy_diff = abs(energy - weights["energy"])
                scores[emotion] = scores[emotion] * 0.7 + max(0.0, 1.0 - energy_diff) * 0.3

        # Normalize scores
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}

        # Get primary emotion
        primary_emotion_str = max(scores, key=scores.get)
        primary_emotion = EmotionCategory(primary_emotion_str)

        # Calculate arousal and valence
        arousal = self._calculate_arousal(f0_mean_norm, f0_std_norm, speaking_rate)
        valence = self._calculate_valence(scores)

        confidence = scores[primary_emotion_str]

        return EmotionAnalysis(
            segment_id=segment_id,
            primary_emotion=primary_emotion,
            emotion_scores=scores,
            confidence=confidence,
            arousal=arousal,
            valence=valence,
        )

    def analyze_from_audio(
        self,
        audio_path: str | Path,
        segment_id: str = "",
    ) -> EmotionAnalysis:
        """
        Analyze emotion from audio file.

        Args:
            audio_path: Path to audio file
            segment_id: Segment identifier

        Returns:
            EmotionAnalysis object
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        if self.model in [EmotionModel.WAV2VEC2, EmotionModel.HUBERT]:
            return self._analyze_with_transformers(audio_path, segment_id)
        else:
            # Extract prosody and analyze
            return self._analyze_with_prosody_extraction(audio_path, segment_id)

    def _analyze_with_prosody_extraction(
        self,
        audio_path: Path,
        segment_id: str,
    ) -> EmotionAnalysis:
        """Analyze emotion using prosody extraction."""
        try:
            from forensic.speech.prosody import ProsodyExtractor
        except ImportError as e:
            raise ImportError("Prosody module required for rule-based emotion analysis") from e

        extractor = ProsodyExtractor()
        sound = extractor.load_audio(audio_path)

        f0_stats = extractor.extract_f0_stats(sound)

        # Estimate energy and speaking rate
        try:
            audio, _ = extractor._get_sound_class()(str(audio_path))
            energy = float(np.mean(audio.values**2))
        except Exception:
            energy = None

        return self.analyze_from_prosody(
            f0_mean=f0_stats["f0_mean"],
            f0_std=f0_stats["f0_std"],
            energy=energy,
            segment_id=segment_id,
        )

    def _analyze_with_transformers(
        self,
        audio_path: Path,
        segment_id: str,
    ) -> EmotionAnalysis:
        """Analyze emotion using transformer models."""
        model_dict = self._load_model()
        if model_dict is None:
            return self._analyze_with_prosody_extraction(audio_path, segment_id)

        try:
            import torch
        except ImportError as e:
            raise ImportError("PyTorch is required for transformer models") from e

        try:
            import soundfile as sf
        except ImportError as e:
            raise ImportError("soundfile is required") from e

        # Load audio
        audio, sr = sf.read(str(audio_path))

        # Ensure mono
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)

        # Resample if needed
        if sr != 16000:
            try:
                import librosa

                audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
                sr = 16000
            except ImportError:
                pass

        # Process
        inputs = model_dict["processor"](
            audio,
            sampling_rate=16000,
            return_tensors="pt",
            padding=True,
        )

        if torch.cuda.is_available():
            inputs = {k: v.to("cuda") for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model_dict["model"](**inputs)
            logits = outputs.logits[0]

        # Get probabilities
        probs = torch.softmax(logits, dim=-1).cpu().numpy()

        # Map to emotions
        emotion_labels = EmotionConfig.EMOTIONS
        scores = {label: float(probs[i]) for i, label in enumerate(emotion_labels)}

        primary_emotion = EmotionCategory(max(scores, key=scores.get))
        confidence = scores[primary_emotion.value]

        # Calculate arousal and valence from emotion
        arousal = self._emotion_to_arousal(primary_emotion)
        valence = self._emotion_to_valence(primary_emotion)

        return EmotionAnalysis(
            segment_id=segment_id,
            primary_emotion=primary_emotion,
            emotion_scores=scores,
            confidence=confidence,
            arousal=arousal,
            valence=valence,
        )

    def _calculate_arousal(
        self,
        f0_mean: float,
        f0_std: float,
        speaking_rate: float,
    ) -> float:
        """Calculate arousal from prosodic features."""
        # Higher F0, higher variability, faster rate = higher arousal
        arousal = (f0_mean - 1.0) * 0.3 + (f0_std - 1.0) * 0.4 + (speaking_rate - 1.0) * 0.3
        return float(np.clip(0.5 + arousal, 0.0, 1.0))

    def _calculate_valence(self, scores: dict[str, float]) -> float:
        """Calculate valence from emotion scores."""
        # Positive emotions: happy, surprise
        positive = scores.get("happy", 0) + scores.get("surprise", 0) * 0.5

        # Negative emotions: angry, sad, fear, disgust
        negative = (
            scores.get("angry", 0) * 0.5
            + scores.get("sad", 0)
            + scores.get("fear", 0) * 0.7
            + scores.get("disgust", 0) * 0.8
        )

        valence = positive - negative
        return float(np.clip(valence, -1.0, 1.0))

    def _emotion_to_arousal(self, emotion: EmotionCategory) -> float:
        """Map emotion to arousal level."""
        arousal_map = {
            EmotionCategory.ANGRY: 0.85,
            EmotionCategory.FEAR: 0.80,
            EmotionCategory.HAPPY: 0.75,
            EmotionCategory.SURPRISE: 0.70,
            EmotionCategory.DISGUST: 0.50,
            EmotionCategory.SAD: 0.30,
            EmotionCategory.NEUTRAL: 0.40,
        }
        return arousal_map.get(emotion, 0.5)

    def _emotion_to_valence(self, emotion: EmotionCategory) -> float:
        """Map emotion to valence level."""
        valence_map = {
            EmotionCategory.HAPPY: 0.8,
            EmotionCategory.SURPRISE: 0.4,
            EmotionCategory.NEUTRAL: 0.0,
            EmotionCategory.FEAR: -0.4,
            EmotionCategory.ANGRY: -0.5,
            EmotionCategory.DISGUST: -0.6,
            EmotionCategory.SAD: -0.7,
        }
        return valence_map.get(emotion, 0.0)

    def batch_analyze(
        self,
        segments: list[tuple[str, Path]],  # List of (segment_id, audio_path)
    ) -> list[EmotionAnalysis]:
        """
        Analyze emotions for multiple segments.

        Args:
            segments: List of (segment_id, audio_path) tuples

        Returns:
            List of EmotionAnalysis objects
        """
        results: list[EmotionAnalysis] = []

        for segment_id, audio_path in segments:
            try:
                analysis = self.analyze_from_audio(audio_path, segment_id)
                results.append(analysis)
            except Exception as e:
                logger.warning(f"Failed to analyze {segment_id}: {e}")
                # Create neutral analysis
                results.append(
                    EmotionAnalysis(
                        segment_id=segment_id,
                        primary_emotion=EmotionCategory.NEUTRAL,
                        emotion_scores={"neutral": 1.0},
                        confidence=0.0,
                    )
                )

        return results
