"""
Forensic Speech Analysis Data Models

Pydantic v2 based data models for forensic speech analysis system.
Supports DGX Spark environment (ARM64, 128GB unified memory).

These models cover:
- Speech segments and diarization
- Prosodic features (F0, Jitter, Shimmer, HNR)
- Emotion analysis (KESDy18 based)
- Gaslighting detection
- Authenticity scoring and deepfake detection
- Analysis results and XAI explanations
"""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator


class GaslightingType(str, Enum):
    """Gaslighting pattern types."""

    DENIAL = "denial"  # Denial of facts
    COUNTER_ATTACK = "counter_attack"  # Counter-attack
    TRIVIALIZING = "trivializing"  # Trivializing
    FORGETTING = "forgetting"  # Selective forgetting
    BLOCKING = "blocking"  # Topic blocking
    GASLIGHTING_BY_PROXY = "proxy"  # Proxy gaslighting


class EmotionCategory(str, Enum):
    """Emotion categories based on KESDy18 corpus."""

    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    FEAR = "fear"
    DISGUST = "disgust"
    SURPRISE = "surprise"


class SpeechSegment(BaseModel):
    """
    Speech segment model.

    Represents a single speech segment from transcription.
    Used for temporal analysis and speaker-based processing.

    Attributes:
        id: Unique segment identifier
        start_time: Segment start time in seconds (>= 0)
        end_time: Segment end time in seconds (> start_time)
        text: Transcribed text content
        confidence: Transcription confidence (0.0 ~ 1.0)
    """

    id: str
    start_time: Annotated[float, Field(ge=0, description="Start time in seconds")]
    end_time: Annotated[float, Field(gt=0, description="End time in seconds")]
    text: str
    confidence: Annotated[float, Field(ge=0, le=1, default=1.0)]

    @field_validator("end_time")
    @classmethod
    def validate_end_time(cls, v: float, info) -> float:
        """Validate end_time is greater than start_time."""
        if "start_time" in info.data and v <= info.data["start_time"]:
            raise ValueError("end_time must be greater than start_time")
        return v

    @property
    def duration(self) -> float:
        """Return segment duration in seconds."""
        return self.end_time - self.start_time


class DiarizationSegment(BaseModel):
    """
    Speaker diarization segment.

    Represents a segment with speaker identification.

    Attributes:
        id: Unique identifier
        start_time: Start time in seconds
        end_time: End time in seconds
        speaker_id: Speaker identifier
        confidence: Speaker identification confidence
    """

    id: str
    start_time: Annotated[float, Field(ge=0)]
    end_time: Annotated[float, Field(gt=0)]
    speaker_id: str
    confidence: Annotated[float, Field(ge=0, le=1, default=1.0)]

    @field_validator("end_time")
    @classmethod
    def validate_end_time(cls, v: float, info) -> float:
        """Validate end_time is greater than start_time."""
        if "start_time" in info.data and v <= info.data["start_time"]:
            raise ValueError("end_time must be greater than start_time")
        return v

    @property
    def duration(self) -> float:
        """Return segment duration in seconds."""
        return self.end_time - self.start_time

    def overlaps(self, other: "DiarizationSegment") -> bool:
        """Check if this segment overlaps with another."""
        return not (self.end_time <= other.start_time or self.start_time >= other.end_time)


class ProsodyFeatures(BaseModel):
    """
    Prosodic features extracted from speech.

    Contains acoustic features relevant for forensic analysis.

    Attributes:
        segment_id: Reference to speech segment
        f0_mean: Mean fundamental frequency (Hz)
        f0_std: Standard deviation of F0 (Hz)
        f0_min: Minimum F0 (Hz)
        f0_max: Maximum F0 (Hz)
        f0_range: Range of F0 (max - min, Hz)
        jitter: Frequency perturbation quotient (%)
        shimmer: Amplitude perturbation quotient (%)
        hnr: Harmonics-to-noise ratio (dB)
        energy: RMS energy (optional)
        zero_crossing_rate: Zero crossing rate (optional)
    """

    segment_id: str
    f0_mean: Annotated[float, Field(ge=0, description="Mean F0 in Hz")]
    f0_std: Annotated[float, Field(ge=0, description="F0 standard deviation in Hz")]
    f0_min: Annotated[float, Field(ge=0, description="Minimum F0 in Hz")]
    f0_max: Annotated[float, Field(ge=0, description="Maximum F0 in Hz")]
    f0_range: Annotated[float, Field(ge=0, description="F0 range in Hz")]
    jitter: Annotated[float, Field(ge=0, description="Jitter (%)")]
    shimmer: Annotated[float, Field(ge=0, description="Shimmer (%)")]
    hnr: Annotated[float, Field(description="Harmonics-to-noise ratio in dB")]
    energy: float | None = None
    zero_crossing_rate: float | None = None

    @property
    def f0_cv(self) -> float:
        """Coefficient of variation of F0."""
        if self.f0_mean == 0:
            return 0.0
        return (self.f0_std / self.f0_mean) * 100


class EmotionAnalysis(BaseModel):
    """
    Emotion analysis results based on KESDy18.

    Attributes:
        segment_id: Reference to speech segment
        primary_emotion: Primary emotion category
        emotion_scores: Dictionary of emotion probabilities (0-1)
        confidence: Overall analysis confidence (0-1)
        arousal: Arousal level (0-1)
        valence: Valence level (-1 to 1)
    """

    segment_id: str
    primary_emotion: EmotionCategory
    emotion_scores: dict[str, Annotated[float, Field(ge=0, le=1)]] = Field(
        default_factory=dict
    )
    confidence: Annotated[float, Field(ge=0, le=1)] = 1.0
    arousal: Annotated[float, Field(ge=0, le=1)] = 0.5
    valence: Annotated[float, Field(ge=-1, le=1)] = 0.0

    def get_emotion_score(self, emotion: EmotionCategory) -> float:
        """Get score for specific emotion."""
        return self.emotion_scores.get(emotion.value, 0.0)

    def is_high_arousal(self) -> bool:
        """Check if emotion is high arousal."""
        return self.arousal > 0.6

    def is_negative_valence(self) -> bool:
        """Check if emotion has negative valence."""
        return self.valence < -0.3


class GaslightingIndicator(BaseModel):
    """
    Gaslighting pattern detection result.

    Attributes:
        segment_id: Reference to speech segment
        type: Gaslighting type
        severity: Severity level (LOW, MEDIUM, HIGH)
        confidence: Detection confidence (0-1)
        evidence: Textual evidence
        context: Surrounding context
    """

    segment_id: str
    type: GaslightingType
    severity: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    confidence: Annotated[float, Field(ge=0, le=1)] = 1.0
    evidence: str = ""
    context: str = ""

    def is_high_severity(self) -> bool:
        """Check if high severity."""
        return self.severity == "HIGH"

    def is_confident(self) -> bool:
        """Check if high confidence."""
        return self.confidence > 0.7


class AuthenticityScore(BaseModel):
    """
    Speech authenticity assessment.

    Attributes:
        audio_id: Audio file identifier
        score: Authenticity score (0-100)
        explanation: Human-readable explanation
        deepfake_probability: Probability of deepfake (0-1)
        confidence: Overall confidence (0-1)
        indicators: List of indicators considered
    """

    audio_id: str
    score: Annotated[float, Field(ge=0, le=100)]
    explanation: str
    deepfake_probability: Annotated[float, Field(ge=0, le=1)]
    confidence: Annotated[float, Field(ge=0, le=1)] = 1.0
    indicators: list[str] = Field(default_factory=list)

    def is_likely_authentic(self) -> bool:
        """Check if likely authentic (score >= 70)."""
        return self.score >= 70

    def is_likely_deepfake(self) -> bool:
        """Check if likely deepfake (probability > 0.5)."""
        return self.deepfake_probability > 0.5


class AuthenticityExplanation(BaseModel):
    """
    Detailed explanation for authenticity assessment.

    Attributes:
        audio_id: Audio identifier
        prosodic_analysis: Prosodic feature analysis
        spectral_analysis: Spectral feature analysis
        temporal_inconsistencies: Temporal inconsistency indicators
        artifact_detection: Audio artifact findings
        conclusion: Final conclusion
    """

    audio_id: str
    prosodic_analysis: str
    spectral_analysis: str
    temporal_inconsistencies: str
    artifact_detection: str
    conclusion: str


class TemporalDegradationReport(BaseModel):
    """
    Report on temporal degradation in audio.

    Attributes:
        audio_id: Audio identifier
        degradation_detected: Whether degradation was detected
        degradation_type: Type of degradation
        affected_segments: List of affected segment IDs
        severity: Severity level
    """

    audio_id: str
    degradation_detected: bool
    degradation_type: str | None = None
    affected_segments: list[str] = Field(default_factory=list)
    severity: Literal["NONE", "LOW", "MEDIUM", "HIGH"] = "NONE"


class IntegrityChain(BaseModel):
    """
    Chain of custody for forensic audio.

    Attributes:
        audio_id: Audio identifier
        created_at: Creation timestamp
        modified_at: Last modification timestamp
        checksum: File checksum (SHA-256)
        handlers: List of handlers
        modifications: List of modifications
    """

    audio_id: str
    created_at: datetime
    modified_at: datetime
    checksum: str
    handlers: list[str] = Field(default_factory=list)
    modifications: list[str] = Field(default_factory=list)

    def verify_integrity(self, current_checksum: str) -> bool:
        """Verify integrity against stored checksum."""
        return self.checksum == current_checksum


class AnalysisResults(BaseModel):
    """
    Complete analysis results for an audio file.

    Aggregates all analysis results for comprehensive reporting.

    Attributes:
        audio_id: Audio file identifier
        segments: Speech segments
        diarization: Speaker diarization
        prosody: Prosodic features
        emotions: Emotion analysis
        gaslighting: Gaslighting indicators
        authenticity: Authenticity assessment
        timestamp: Analysis timestamp
        processing_time: Processing time in seconds
    """

    audio_id: str
    segments: list[SpeechSegment] = Field(default_factory=list)
    diarization: list[DiarizationSegment] = Field(default_factory=list)
    prosody: list[ProsodyFeatures] = Field(default_factory=list)
    emotions: list[EmotionAnalysis] = Field(default_factory=list)
    gaslighting: list[GaslightingIndicator] = Field(default_factory=list)
    authenticity: AuthenticityScore | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_time: Annotated[float, Field(ge=0)] = 0.0

    def get_segment_count(self) -> int:
        """Return number of speech segments."""
        return len(self.segments)

    def get_speaker_count(self) -> int:
        """Return number of unique speakers."""
        speakers = {seg.speaker_id for seg in self.diarization}
        return len(speakers)

    def get_gaslighting_count(self) -> int:
        """Return number of gaslighting indicators."""
        return len(self.gaslighting)

    def has_deepfake_risk(self) -> bool:
        """Check if deepfake risk detected."""
        return self.authenticity is not None and self.authenticity.is_likely_deepfake()


# Type aliases for convenience
SegmentId = str
SpeakerId = str
AudioId = str
