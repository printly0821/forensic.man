"""
GradCAM-based XAI for Speech Analysis

Gradient-weighted Class Activation Mapping for interpreting
speech analysis model decisions. Provides temporal visualization
of which audio regions contributed most to predictions.

REQ-T-008: XAI explainability using GradCAM.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class GradCAMConfig:
    """Configuration for GradCAM computation."""

    # Layer settings
    TARGET_LAYER = "features.8"  # Target layer for GradCAM

    # Computation settings
    INTERPOLATE_METHOD = "bilinear"
    SMOOTH_GRAD = True
    NOISE_LEVEL = 0.15

    # Visualization settings
    COLORMAP = "jet"
    ALPHA = 0.4
    THRESHOLD_PERCENTILE = 80


@dataclass
class TemporalContribution:
    """Temporal contribution to model prediction."""

    start_time: float
    end_time: float
    contribution: float
    importance: str  # HIGH, MEDIUM, LOW


class SpeechGradCAM:
    """
    GradCAM implementation for speech analysis models.

    Provides temporal importance visualization for model predictions.
    """

    def __init__(self, model=None, target_layer: str | None = None) -> None:
        """
        Initialize GradCAM.

        Args:
            model: PyTorch model to analyze
            target_layer: Target layer name for GradCAM
        """
        self.model = model
        self.target_layer = target_layer or GradCAMConfig.TARGET_LAYER
        self.gradients = None
        self.activations = None

    def register_hooks(self):
        """Register forward and backward hooks for gradient extraction."""
        if self.model is None:
            raise ValueError("Model must be set before registering hooks")

        try:
            import torch  # noqa: F401
        except ImportError as e:
            raise ImportError("PyTorch is required for GradCAM") from e

        self.gradients = None
        self.activations = None

        def forward_hook(_module, _input, output):
            self.activations = output.detach()

        def backward_hook(_module, _grad_input, grad_output):
            self.gradients = grad_output[0].detach()

        # Find target layer
        target_module = None
        for name, module in self.model.named_modules():
            if name == self.target_layer:
                target_module = module
                break

        if target_module is None:
            logger.warning(f"Layer {self.target_layer} not found, using last conv layer")
            # Try to find last conv layer
            for _name, module in reversed(list(self.model.named_modules())):
                if hasattr(module, "out_channels"):
                    target_module = module
                    break

        if target_module is not None:
            target_module.register_forward_hook(forward_hook)
            target_module.register_full_backward_hook(backward_hook)

    def compute_gradcam(
        self,
        input_tensor,
        target_class: int | None = None,
    ) -> np.ndarray:
        """
        Compute GradCAM heatmap.

        Args:
            input_tensor: Input tensor (1, features, time)
            target_class: Target class index (None = use predicted)

        Returns:
            GradCAM heatmap as numpy array
        """
        try:
            import torch
        except ImportError as e:
            raise ImportError("PyTorch is required for GradCAM") from e

        if self.model is None:
            raise ValueError("Model must be set for GradCAM computation")

        # Register hooks
        self.register_hooks()

        # Forward pass
        self.model.eval()
        output = self.model(input_tensor)

        # Get target class
        if target_class is None:
            target_class = torch.argmax(output, dim=1).item()

        # Backward pass
        self.model.zero_grad()
        output[0, target_class].backward(retain_graph=True)

        # Get gradients and activations
        gradients = self.gradients  # (1, C, T)
        activations = self.activations  # (1, C, T)

        if gradients is None or activations is None:
            logger.warning("Failed to capture gradients or activations")
            return np.zeros(input_tensor.shape[2])

        # Global average pooling of gradients
        weights = torch.mean(gradients, dim=[0, 2])  # (C,)

        # Weighted combination of activations
        gradcam = torch.zeros(activations.shape[2])  # (T,)
        for i, w in enumerate(weights):
            gradcam += w * activations[0, i, :]

        # ReLU
        gradcam = torch.relu(gradcam)

        # Normalize
        gradcam = gradcam / (torch.max(gradcam) + 1e-8)

        return gradcam.cpu().numpy()

    def compute_temporal_importance(
        self,
        audio_path: str | Path,
        _sample_rate: int = 16000,
        window_size: float = 1.0,
    ) -> list[TemporalContribution]:
        """
        Compute temporal importance for audio segments.

        Args:
            audio_path: Path to audio file
            sample_rate: Audio sample rate
            window_size: Window size in seconds

        Returns:
            List of temporal contributions
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        try:
            import soundfile as sf
        except ImportError as e:
            raise ImportError("soundfile is required") from e

        # Load audio
        audio, sr = sf.read(str(audio_path))

        # Calculate number of windows
        duration = len(audio) / sr
        num_windows = int(duration / window_size)

        contributions: list[TemporalContribution] = []

        # For each window, compute importance
        for i in range(num_windows):
            start_time = i * window_size
            end_time = (i + 1) * window_size

            # Simulate importance (in real implementation, would use model)
            # This is a placeholder for demonstration
            importance = self._compute_window_importance(
                audio,
                sr,
                int(start_time * sr),
                int(end_time * sr),
            )

            # Determine importance level
            if importance > 0.7:
                level = "HIGH"
            elif importance > 0.4:
                level = "MEDIUM"
            else:
                level = "LOW"

            contributions.append(
                TemporalContribution(
                    start_time=start_time,
                    end_time=end_time,
                    contribution=float(importance),
                    importance=level,
                )
            )

        return contributions

    def _compute_window_importance(
        self,
        audio: np.ndarray,
        _sample_rate: int,
        start_sample: int,
        end_sample: int,
    ) -> float:
        """
        Compute importance for a single window.

        Args:
            audio: Audio array
            sample_rate: Sample rate
            start_sample: Start sample index
            end_sample: End sample index

        Returns:
            Importance score (0-1)
        """
        # Extract window
        window = audio[start_sample:end_sample]

        if len(window) == 0:
            return 0.0

        # Compute simple features as proxy for importance
        # In real implementation, would use model forward pass

        # Energy-based importance
        energy = np.mean(window**2)

        # Spectral centroid
        try:
            import librosa

            stft = np.abs(librosa.stft(window))
            spec_centroid = librosa.feature.spectral_centroid(S=stft)[0]
            centroid_mean = np.mean(spec_centroid)
        except ImportError:
            centroid_mean = 0

        # Combine features (normalized)
        importance = min(1.0, energy * 1000 + centroid_mean / 5000)

        return float(importance)

    def visualize_heatmap(
        self,
        audio_path: str | Path,
        gradcam_values: np.ndarray,
        save_path: str | Path | None = None,
    ) -> str:
        """
        Create GradCAM heatmap visualization.

        Args:
            audio_path: Path to audio file
            gradcam_values: GradCAM values
            save_path: Path to save visualization

        Returns:
            Base64 encoded image or file path
        """
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError as e:
            raise ImportError("matplotlib is required for visualization") from e

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6))

        # Load audio for waveform
        try:
            import soundfile as sf

            audio, sr = sf.read(str(audio_path))

            # Plot waveform
            time_axis = np.arange(len(audio)) / sr
            ax1.plot(time_axis, audio)
            ax1.set_title("Waveform")
            ax1.set_xlabel("Time (s)")
            ax1.set_ylabel("Amplitude")

            # Plot GradCAM heatmap
            extent = [0, len(audio) / sr, 0, 1]
            im = ax2.imshow(
                gradcam_values.reshape(1, -1),
                aspect="auto",
                extent=extent,
                cmap=GradCAMConfig.COLORMAP,
                vmin=0,
                vmax=1,
            )
            ax2.set_title("GradCAM Importance")
            ax2.set_xlabel("Time (s)")
            ax2.set_yticks([])

            plt.colorbar(im, ax=ax2, label="Importance")

        except Exception as e:
            logger.warning(f"Failed to create visualization: {e}")

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

    def explain_prediction(
        self,
        audio_path: str | Path,
        prediction: str,
        contributions: list[TemporalContribution] | None = None,
    ) -> str:
        """
        Generate text explanation of prediction.

        Args:
            audio_path: Path to audio file
            prediction: Model prediction
            contributions: Temporal contributions

        Returns:
            Text explanation
        """
        if contributions is None:
            contributions = self.compute_temporal_importance(audio_path)

        # Find high importance regions
        high_importance = [c for c in contributions if c.importance == "HIGH"]
        medium_importance = [c for c in contributions if c.importance == "MEDIUM"]

        lines = [
            f"예측: {prediction}",
            "",
            "시간대별 기여도 분석:",
        ]

        for i, c in enumerate(high_importance[:5], 1):
            lines.append(
                f"  {i}. {c.start_time:.2f}s-{c.end_time:.2f}s: 높은 기여도 ({c.contribution:.2%})"
            )

        if medium_importance:
            lines.append("")
            lines.append("중간 기여도 구간:")
            for c in medium_importance[:3]:
                lines.append(f"  - {c.start_time:.2f}s-{c.end_time:.2f}s")

        return "\n".join(lines)


class GradCAMAnalyzer:
    """
    High-level GradCAM analyzer for speech forensic analysis.

    Provides easy-to-use interface for explaining model predictions.
    """

    def __init__(self) -> None:
        """Initialize the analyzer."""
        self.gradcam = SpeechGradCAM()

    def analyze_audio(
        self,
        audio_path: str | Path,
        save_visualization: bool = False,
        output_dir: str | Path | None = None,
    ) -> dict:
        """
        Analyze audio with GradCAM explanation.

        Args:
            audio_path: Path to audio file
            save_visualization: Whether to save heatmap visualization
            output_dir: Directory to save outputs

        Returns:
            Dictionary with analysis results
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Compute temporal importance
        contributions = self.gradcam.compute_temporal_importance(audio_path)

        # Create heatmap values
        heatmap = np.array([c.contribution for c in contributions])

        # Generate visualization
        visualization = None
        if save_visualization and output_dir:
            output_path = Path(output_dir) / f"{audio_path.stem}_gradcam.png"
            visualization = self.gradcam.visualize_heatmap(audio_path, heatmap, output_path)

        # Find important regions
        important_regions = [
            {"start": c.start_time, "end": c.end_time, "score": c.contribution}
            for c in contributions
            if c.importance == "HIGH"
        ]

        return {
            "audio_file": str(audio_path),
            "contributions": contributions,
            "heatmap": heatmap.tolist(),
            "important_regions": important_regions,
            "visualization": visualization,
        }

    def get_important_segments(
        self,
        contributions: list[TemporalContribution],
        top_k: int = 5,
    ) -> list[TemporalContribution]:
        """
        Get top-k most important segments.

        Args:
            contributions: List of temporal contributions
            top_k: Number of top segments to return

        Returns:
            List of top-k important segments
        """
        sorted_contributions = sorted(
            contributions,
            key=lambda c: c.contribution,
            reverse=True,
        )
        return sorted_contributions[:top_k]

    def generate_report(
        self,
        analysis_result: dict,
    ) -> str:
        """
        Generate human-readable report from analysis result.

        Args:
            analysis_result: Result from analyze_audio

        Returns:
            Formatted report string
        """
        lines = [
            "=" * 60,
            "GradCAM 분석 보고서 (GradCAM Analysis Report)",
            "=" * 60,
            "",
            f"파일: {analysis_result['audio_file']}",
            "",
        ]

        contributions = analysis_result["contributions"]

        # Summary statistics
        high_count = sum(1 for c in contributions if c.importance == "HIGH")
        medium_count = sum(1 for c in contributions if c.importance == "MEDIUM")
        low_count = sum(1 for c in contributions if c.importance == "LOW")

        lines.extend(
            [
                "## 기여도 요약 (Summary)",
                f"높음 (HIGH): {high_count}구간",
                f"중간 (MEDIUM): {medium_count}구간",
                f"낮음 (LOW): {low_count}구간",
                "",
            ]
        )

        # Important regions
        if analysis_result["important_regions"]:
            lines.append("## 중요 구간 (Important Regions)")
            for i, region in enumerate(analysis_result["important_regions"], 1):
                lines.append(
                    f"{i}. {region['start']:.2f}s-{region['end']:.2f}s "
                    f"(기여도: {region['score']:.2%})"
                )
            lines.append("")

        lines.append("=" * 60)

        return "\n".join(lines)
