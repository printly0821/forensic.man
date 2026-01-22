"""CLI configuration models"""
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class AnalysisConfig(BaseModel):
    chunk_size_mb: int = Field(ge=1, le=100, default=1)
    parallel_workers: int = Field(ge=1, le=16, default=4)
    enable_gpu: bool = False
    timeout_per_file: int = Field(ge=10, le=3600, default=300)


class SearchConfig(BaseModel):
    max_results: int = Field(ge=1, le=10000, default=1000)
    timeout_seconds: int = Field(ge=1, le=300, default=30)
    default_page_size: int = Field(ge=1, le=100, default=20)
    enable_morpheme: bool = True


class ReportConfig(BaseModel):
    default_format: str = "markdown"
    include_statistics: bool = True
    include_timeline: bool = True
    legal_template: str | None = None

    @field_validator("default_format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        valid = ["markdown", "html", "json", "pdf"]
        v_lower = v.lower()
        if v_lower not in valid:
            raise ValueError(f"Invalid format '{v}'")
        return v_lower


class TimelineConfig(BaseModel):
    default_resolution: str = "day"
    show_patterns: bool = True
    highlight_important: bool = True

    @field_validator("default_resolution")
    @classmethod
    def validate_resolution(cls, v: str) -> str:
        valid = ["day", "week", "month"]
        v_lower = v.lower()
        if v_lower not in valid:
            raise ValueError(f"Invalid resolution '{v}'")
        return v_lower


class OutputConfig(BaseModel):
    color: str = "auto"
    unicode: bool = True
    quiet: bool = False
    verbose: bool = False

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        valid = ["auto", "always", "never"]
        v_lower = v.lower()
        if v_lower not in valid:
            raise ValueError(f"Invalid color mode '{v}'")
        return v_lower


class CacheConfig(BaseModel):
    enabled: bool = True
    directory: Path = Field(default=Path(".forensic/cache"))
    max_size_mb: int = Field(ge=1, le=10000, default=500)
    ttl_days: int = Field(ge=1, le=365, default=7)


class SystemConfig(BaseModel):
    memory_limit_gb: int = Field(ge=1, le=128, default=2)
    temp_directory: str = "/tmp/forensic"
    log_level: str = "INFO"


class ForensicCLIConfig(BaseModel):
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)
    timeline: TimelineConfig = Field(default_factory=TimelineConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    system: SystemConfig = Field(default_factory=SystemConfig)

    def get(self, key: str, default=None):
        keys = key.split(".")
        value = self
        for k in keys:
            if hasattr(value, k):
                value = getattr(value, k)
            else:
                return default
        return value
