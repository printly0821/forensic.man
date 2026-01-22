"""
Forensic Speech XAI Subpackage

Explainable AI modules for speech analysis including GradCAM
temporal attribution and SHAP feature importance.
"""

from forensic.speech.xai.gradcam import (
    GradCAMAnalyzer,
    GradCAMConfig,
    SpeechGradCAM,
    TemporalContribution,
)
from forensic.speech.xai.shap_explainer import (
    FeatureImportance,
    FeatureImportanceAnalyzer,
    FeatureType,
    SHAPConfig,
    SpeechSHAPExplainer,
)

__all__ = [
    # GradCAM
    "SpeechGradCAM",
    "GradCAMAnalyzer",
    "GradCAMConfig",
    "TemporalContribution",
    # SHAP
    "SpeechSHAPExplainer",
    "FeatureImportanceAnalyzer",
    "SHAPConfig",
    "FeatureImportance",
    "FeatureType",
]
