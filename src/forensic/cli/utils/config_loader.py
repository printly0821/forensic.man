"""CLI configuration loader"""
import json
from pathlib import Path
from typing import Any

import yaml

from forensic.cli.models.config import ForensicCLIConfig


class CLIConfigLoader:
    DEFAULT_CONFIG_PATHS = [
        Path.home() / ".forensic" / "config.yaml",
        Path.home() / ".forensicrc.yaml",
        Path("forensic.yaml"),
    ]

    DEFAULT_CONFIG: dict[str, Any] = {
        "analysis": {"chunk_size_mb": 1, "parallel_workers": 4, "enable_gpu": False, "timeout_per_file": 300},
        "search": {"max_results": 1000, "timeout_seconds": 30, "default_page_size": 20, "enable_morpheme": True},
        "report": {"default_format": "markdown", "include_statistics": True, "include_timeline": True},
        "timeline": {"default_resolution": "day", "show_patterns": True, "highlight_important": True},
        "output": {"color": "auto", "unicode": True, "quiet": False, "verbose": False},
        "cache": {"enabled": True, "directory": ".forensic/cache", "max_size_mb": 500, "ttl_days": 7},
        "system": {"memory_limit_gb": 2, "temp_directory": "/tmp/forensic", "log_level": "INFO"},
    }

    def __init__(self, config_path: Path | str | None = None) -> None:
        if isinstance(config_path, str):
            config_path = Path(config_path)
        self.config_path = config_path
        self._config: ForensicCLIConfig | None = None

    def find_config_path(self) -> Path | None:
        if self.config_path:
            return self.config_path if self.config_path.exists() else None
        for path in self.DEFAULT_CONFIG_PATHS:
            if path.exists():
                return path
        return None

    def load(self, path: Path | str | None = None) -> ForensicCLIConfig:
        load_path = self._resolve_path(path)
        if load_path is None or not load_path.exists():
            self._config = ForensicCLIConfig(**self.DEFAULT_CONFIG)
            return self._config
        try:
            data = self._load_yaml(load_path)
            merged = self._merge_with_defaults(data)
            self._config = ForensicCLIConfig(**merged)
            return self._config
        except Exception:
            self._config = ForensicCLIConfig(**self.DEFAULT_CONFIG)
            return self._config

    def _resolve_path(self, path: Path | str | None) -> Path | None:
        if path is not None:
            return Path(path) if isinstance(path, str) else path
        if self.config_path is not None:
            return self.config_path
        return self.find_config_path()

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        try:
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError:
            try:
                with open(path, encoding="utf-8") as f:
                    return json.load(f) or {}
            except json.JSONDecodeError:
                return {}

    def _merge_with_defaults(self, data: dict[str, Any]) -> dict[str, Any]:
        result = self.DEFAULT_CONFIG.copy()
        for key, value in data.items():
            if key in result and isinstance(value, dict):
                result[key] = {**result[key], **value}
            else:
                result[key] = value
        return result

    def save(self, config: ForensicCLIConfig, path: Path | str | None = None) -> None:
        save_path = path or self.config_path or self.find_config_path()
        if save_path is None:
            save_path = Path.home() / ".forensic" / "config.yaml"
        if isinstance(save_path, str):
            save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        data = config.model_dump()
        with open(save_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    def reload(self) -> ForensicCLIConfig:
        self._config = None
        return self.load()

    @property
    def config(self) -> ForensicCLIConfig:
        if self._config is None:
            self._config = self.load()
        return self._config
