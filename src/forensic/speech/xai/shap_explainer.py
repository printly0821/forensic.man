"""
SHAP-based Feature Importance for Speech Analysis

SHAP (SHapley Additive exPlanations) for interpreting speech analysis
models. Provides feature-level attribution for model decisions.

REQ-T-008: XAI explainability using SHAP.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class FeatureType(str, Enum):
    """Types of audio features for SHAP analysis."""

    MFCC = "mfcc"
    LFCC = "lfcc"
    SPECTRAL_CENTROID = "spectral_centroid"
    SPECTRAL_ROLLOFF = "spectral_rolloff"
    ZCR = "zero_crossing_rate"
    ENERGY = "energy"
    PITCH = "pitch"


@dataclass
class SHAPConfig:
    """Configuration for SHAP computation."""

    # SHAP settings
    BACKGROUND_SAMPLES = 100
    NSAMPLES = "auto"  # Number of samples for SHAP values

    # Visualization settings
    MAX_FEATURES_DISPLAY = 20
    PLOT_TYPE = "bar"

    # Computation settings
    BATCH_SIZE = 32
    USE_APPROXIMATE = True


@dataclass
class FeatureImportance:
    """Importance score for a single feature."""

    feature_name: str
    feature_type: FeatureType
    importance: float
    shap_value: float
    direction: str  # positive, negative


class SpeechSHAPExplainer:
    """
    SHAP explainer for speech analysis models.

    Provides feature-level attribution for model predictions.
    """

    def __init__(self, model=None, masker=None) -> None:
        """
        Initialize SHAP explainer.

        Args:
            model: Model to explain
            masker: SHAP masker for background data
        """
        self.model = model
        self.masker = masker
        self.explainer = None
        self.shap_values = None

    def _create_masker(self, background_data: np.ndarray):
        """Create SHAP masker from background data."""
        try:
            import shap

            return shap.maskers.Independent(data=background_data)
        except ImportError as e:
            raise ImportError("shap is required for SHAP explanations") from e

    def _create_explainer(
        self,
        background_data: np.ndarray,
    ):
        """
        Create SHAP explainer.

        Args:
            background_data: Background data for explainer
        """
        try:
            import shap
        except ImportError as e:
            raise ImportError("shap is required") from e

        if self.masker is None:
            self.masker = self._create_masker(background_data)

        # Create explainer based on model type
        if self.model is not None:
            # Try to determine appropriate explainer
            try:
                self.explainer = shap.Explainer(
                    self.model,
                    self.masker,
                    algorithm="auto" if SHAPConfig.USE_APPROXIMATE else "exact",
                )
            except Exception:
                # Fallback to KernelExplainer
                self.explainer = shap.KernelExplainer(
                    self.model.predict if hasattr(self.model, "predict") else self.model,
                    background_data,
                )
        else:
            raise ValueError("Model must be provided for SHAP explanation")

    def compute_shap_values(
        self,
        features: np.ndarray,
        background_data: np.ndarray | None = None,
    ) -> np.ndarray:
        """
        Compute SHAP values for features.

        Args:
            features: Feature array to explain
            background_data: Background data for explainer

        Returns:
            SHAP values array
        """
        if background_data is None:
            # Use subset of features as background
            n_background = min(SHAPConfig.BACKGROUND_SAMPLES, len(features))
            background_data = features[:n_background]

        if self.explainer is None:
            self._create_explainer(background_data)

        # Compute SHAP values
        self.shap_values = self.explainer.shap_values(
            features,
            nsamples=SHAPConfig.NSAMPLES,
        )

        return self.shap_values

    def get_feature_importance(
        self,
        shap_values: np.ndarray,
        feature_names: list[str] | None = None,
    ) -> list[FeatureImportance]:
        """
        Get feature importance from SHAP values.

        Args:
            shap_values: Computed SHAP values
            feature_names: Names of features

        Returns:
            List of feature importance scores
        """
        if feature_names is None:
            feature_names = [f"feature_{i}" for i in range(shap_values.shape[1])]

        # Calculate mean absolute SHAP values
        mean_shap = np.mean(np.abs(shap_values), axis=0)

        importances: list[FeatureImportance] = []

        for i, (name, value) in enumerate(zip(feature_names, mean_shap, strict=True)):
            # Determine feature type from name
            feature_type = self._infer_feature_type(name)

            # Calculate direction (positive/negative impact)
            mean_value = np.mean(shap_values[:, i])
            direction = "positive" if mean_value > 0 else "negative"

            importances.append(
                FeatureImportance(
                    feature_name=name,
                    feature_type=feature_type,
                    importance=float(value),
                    shap_value=float(mean_value),
                    direction=direction,
                )
            )

        # Sort by importance
        importances.sort(key=lambda x: x.importance, reverse=True)

        return importances

    def _infer_feature_type(self, feature_name: str) -> FeatureType:
        """Infer feature type from feature name."""
        name_lower = feature_name.lower()

        if "mfcc" in name_lower:
            return FeatureType.MFCC
        elif "lfcc" in name_lower:
            return FeatureType.LFCC
        elif "centroid" in name_lower:
            return FeatureType.SPECTRAL_CENTROID
        elif "rolloff" in name_lower:
            return FeatureType.SPECTRAL_ROLLOFF
        elif "zcr" in name_lower or "zero" in name_lower:
            return FeatureType.ZCR
        elif "energy" in name_lower:
            return FeatureType.ENERGY
        elif "pitch" in name_lower or "f0" in name_lower:
            return FeatureType.PITCH
        else:
            return FeatureType.MFCC  # Default

    def explain_audio_features(
        self,
        audio_path: str | Path,
        feature_extractor=None,
    ) -> dict:
        """
        Explain audio features using SHAP.

        Args:
            audio_path: Path to audio file
            feature_extractor: Feature extractor function/class

        Returns:
            Dictionary with SHAP explanation
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Extract features
        if feature_extractor is None:
            try:
                from forensic.speech.features import AudioFeatureExtractor

                extractor = AudioFeatureExtractor()
                features_dict = extractor.extract_all_features(audio_path)
            except ImportError as e:
                raise ImportError("Audio feature extractor required") from e
        else:
            features_dict = feature_extractor(audio_path)

        # Combine features into single array
        feature_arrays = []
        feature_names = []

        for name, values in features_dict.items():
            if isinstance(values, np.ndarray) and values.ndim == 2:
                # Use mean of time dimension
                mean_features = np.mean(values, axis=1)
                feature_arrays.append(mean_features)
                for i in range(len(mean_features)):
                    feature_names.append(f"{name}_{i}")
            elif isinstance(values, np.ndarray):
                feature_arrays.append(values)
                feature_names.append(name)

        if not feature_arrays:
            return {
                "error": "No features extracted",
                "feature_importance": [],
            }

        features = np.concatenate(feature_arrays).reshape(1, -1)

        # Create dummy background data (in real use, would use actual background)
        background_data = np.random.randn(
            min(50, 100),
            features.shape[1],
        )

        # Compute SHAP values
        shap_values = self.compute_shap_values(features, background_data)

        # Get feature importance
        importance = self.get_feature_importance(shap_values, feature_names)

        return {
            "audio_file": str(audio_path),
            "feature_importance": importance,
            "shap_values": shap_values.tolist(),
            "feature_names": feature_names,
        }

    def visualize_importance(
        self,
        importance: list[FeatureImportance],
        save_path: str | Path | None = None,
        max_features: int = SHAPConfig.MAX_FEATURES_DISPLAY,
    ) -> str:
        """
        Create feature importance visualization.

        Args:
            importance: List of feature importance scores
            save_path: Path to save visualization
            max_features: Maximum features to display

        Returns:
            Base64 encoded image or file path
        """
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError as e:
            raise ImportError("matplotlib is required for visualization") from e

        # Get top features
        top_features = importance[:max_features]

        fig, ax = plt.subplots(figsize=(10, 6))

        # Plot
        y_pos = np.arange(len(top_features))
        values = [
            f.importance if f.direction == "positive" else -f.importance for f in top_features
        ]
        colors = ["green" if v > 0 else "red" for v in values]

        ax.barh(y_pos, values, color=colors, alpha=0.7)
        ax.set_yticks(y_pos)
        ax.set_yticklabels([f.feature_name for f in top_features])
        ax.set_xlabel("SHAP Value (Impact on Prediction)")
        ax.set_title("Feature Importance (SHAP)")
        ax.axvline(x=0, color="black", linestyle="-", linewidth=0.5)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            plt.close()
            return str(save_path)
        else:
            # Return as base64
            import base64
            import io

            buf = io.BytesIO()
            plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
            plt.close()
            buf.seek(0)
            return base64.b64encode(buf.read()).decode("utf-8")


class FeatureImportanceAnalyzer:
    """
    High-level analyzer for feature importance in speech forensic analysis.

    Provides easy-to-use interface for SHAP-based explanations.
    """

    def __init__(self) -> None:
        """Initialize the analyzer."""
        self.shap_explainer = SpeechSHAPExplainer()

    def analyze_audio(
        self,
        audio_path: str | Path,
        save_visualization: bool = False,
        output_dir: str | Path | None = None,
    ) -> dict:
        """
        Analyze audio feature importance.

        Args:
            audio_path: Path to audio file
            save_visualization: Whether to save visualization
            output_dir: Directory to save outputs

        Returns:
            Dictionary with analysis results
        """
        explanation = self.shap_explainer.explain_audio_features(audio_path)

        if "error" in explanation:
            return explanation

        # Generate visualization if requested
        visualization = None
        if save_visualization and output_dir and explanation["feature_importance"]:
            output_path = Path(output_dir) / f"{Path(audio_path).stem}_shap.png"
            visualization = self.shap_explainer.visualize_importance(
                explanation["feature_importance"],
                output_path,
            )

        explanation["visualization"] = visualization

        return explanation

    def get_top_features(
        self,
        explanation: dict,
        top_k: int = 10,
    ) -> list[FeatureImportance]:
        """
        Get top-k most important features.

        Args:
            explanation: SHAP explanation result
            top_k: Number of top features

        Returns:
            List of top-k features
        """
        return explanation.get("feature_importance", [])[:top_k]

    def generate_report(
        self,
        explanation: dict,
    ) -> str:
        """
        Generate human-readable report.

        Args:
            explanation: SHAP explanation result

        Returns:
            Formatted report string
        """
        lines = [
            "=" * 60,
            "특징 중요도 분석 보고서 (Feature Importance Report)",
            "=" * 60,
            "",
            f"파일: {explanation.get('audio_file', 'Unknown')}",
            "",
        ]

        importance_list = explanation.get("feature_importance", [])

        if not importance_list:
            lines.append("분석 결과가 없습니다.")
            lines.append("=" * 60)
            return "\n".join(lines)

        # Group by feature type
        by_type: dict[str, list[FeatureImportance]] = {}
        for imp in importance_list:
            ftype = imp.feature_type.value
            if ftype not in by_type:
                by_type[ftype] = []
            by_type[ftype].append(imp)

        # Summary by type
        lines.append("## 특징 유형별 요약 (By Feature Type)")
        for ftype, imps in sorted(by_type.items()):
            total_imp = sum(i.importance for i in imps)
            lines.append(f"  - {ftype.upper()}: {total_imp:.4f}")
        lines.append("")

        # Top features
        lines.append("## 주요 특징 (Top Features)")
        for i, imp in enumerate(importance_list[:15], 1):
            direction_symbol = "+" if imp.direction == "positive" else "-"
            lines.append(
                f"  {i}. {imp.feature_name}: "
                f"{direction_symbol}{imp.shap_value:.4f} "
                f"(중요도: {imp.importance:.4f})"
            )
        lines.append("")

        # Positive/negative split
        positive = [i for i in importance_list if i.direction == "positive"]
        negative = [i for i in importance_list if i.direction == "negative"]

        if positive:
            lines.append("## 긍정적 영향 (Positive Impact)")
            for imp in positive[:5]:
                lines.append(f"  - {imp.feature_name}: +{imp.shap_value:.4f}")
            lines.append("")

        if negative:
            lines.append("## 부정적 영향 (Negative Impact)")
            for imp in negative[:5]:
                lines.append(f"  - {imp.feature_name}: {imp.shap_value:.4f}")
            lines.append("")

        lines.append("=" * 60)

        return "\n".join(lines)

    def compare_features(
        self,
        explanations: list[dict],
    ) -> dict:
        """
        Compare feature importance across multiple audio files.

        Args:
            explanations: List of SHAP explanations

        Returns:
            Comparison dictionary
        """
        comparison: dict[str, list[float]] = {}

        for exp in explanations:
            for imp in exp.get("feature_importance", []):
                if imp.feature_name not in comparison:
                    comparison[imp.feature_name] = []
                comparison[imp.feature_name].append(imp.importance)

        # Calculate statistics
        stats: dict[str, dict] = {}
        for feature, values in comparison.items():
            stats[feature] = {
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
                "min": float(np.min(values)),
                "max": float(np.max(values)),
                "count": len(values),
            }

        return stats
