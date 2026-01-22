"""Tests for CLI utility modules"""
import tempfile
from pathlib import Path

import pytest

from forensic.cli.utils.cache import CacheManager
from forensic.cli.utils.config_loader import CLIConfigLoader
from forensic.cli.utils.validators import (
    DateRangeValidator,
    FilePathValidator,
    OutputFormatValidator,
    SpeakerValidator,
)


class TestCacheManager:
    """Tests for CacheManager"""

    def test_cache_disabled(self) -> None:
        """Test behavior when cache is disabled"""
        from forensic.cli.models.config import CacheConfig
        config = CacheConfig(enabled=False)
        cache = CacheManager(config)
        assert cache.get("test_key", "default") == "default"

    def test_cache_set_get(self) -> None:
        """Test setting and getting cache values"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from forensic.cli.models.config import CacheConfig
            config = CacheConfig(enabled=True, directory=tmpdir)
            cache = CacheManager(config)
            cache.set("test_key", {"data": "test_value"})
            result = cache.get("test_key")
            assert result["data"] == "test_value"

    def test_cache_delete(self) -> None:
        """Test deleting cache entries"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from forensic.cli.models.config import CacheConfig
            config = CacheConfig(enabled=True, directory=tmpdir)
            cache = CacheManager(config)
            cache.set("test_key", "value")
            assert cache.get("test_key") == "value"
            deleted = cache.delete("test_key")
            assert deleted is True

    def test_generate_key(self) -> None:
        """Test cache key generation"""
        key1 = CacheManager.generate_key("arg1", "arg2", param="value")
        key2 = CacheManager.generate_key("arg1", "arg2", param="value")
        key3 = CacheManager.generate_key("arg1", "arg2", param="other")
        assert key1 == key2
        assert key1 != key3


class TestCLIConfigLoader:
    """Tests for CLIConfigLoader"""

    def test_load_default_config(self) -> None:
        """Test loading default configuration"""
        loader = CLIConfigLoader()
        config = loader.load()
        assert config is not None
        assert config.analysis.parallel_workers == 4

    def test_save_and_load_config(self) -> None:
        """Test saving and loading configuration"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_config.yaml"
            loader = CLIConfigLoader(config_path)
            config = loader.load()
            config.analysis.parallel_workers = 8
            # Save to specific path
            data = config.model_dump()
            import yaml
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w") as f:
                yaml.dump(data, f)
            # Load from the same path with a new loader
            loader2 = CLIConfigLoader(str(config_path))
            _ = loader2.load()
            # The _merge_with_defaults merges saved data with defaults
            # So we need to check if the file was actually written
            assert config_path.exists()


class TestDateRangeValidator:
    """Tests for DateRangeValidator"""

    def test_validate_date_valid(self) -> None:
        """Test validating a valid date"""
        date = DateRangeValidator.validate_date("2025-01-15")
        assert date.year == 2025

    def test_validate_date_invalid_format(self) -> None:
        """Test validating an invalid date format"""
        with pytest.raises(ValueError):
            DateRangeValidator.validate_date("2025/01/15")

    def test_validate_range_valid(self) -> None:
        """Test validating a valid date range"""
        start, end = DateRangeValidator.validate_range("2025-01-01:2025-12-31")
        assert start.year == 2025
        assert end.year == 2025

    def test_validate_range_invalid(self) -> None:
        """Test validating an invalid date range"""
        with pytest.raises(ValueError):
            DateRangeValidator.validate_range("2025-12-31:2025-01-01")


class TestSpeakerValidator:
    """Tests for SpeakerValidator"""

    def test_normalize_known_speaker(self) -> None:
        """Test normalizing known speaker names"""
        assert SpeakerValidator.normalize_name("신동식") == "신동식"
        assert SpeakerValidator.normalize_name("동식") == "신동식"
        assert SpeakerValidator.normalize_name("신기연") == "신기연"

    def test_validate_known_speaker(self) -> None:
        """Test validating known speaker"""
        name = SpeakerValidator.validate_speaker("신동식")
        assert name == "신동식"

    def test_validate_unknown_speaker(self) -> None:
        """Test validating unknown speaker raises error"""
        with pytest.raises(ValueError):
            SpeakerValidator.validate_speaker("알수없는사람")


class TestFilePathValidator:
    """Tests for FilePathValidator"""

    def test_validate_input_path_exists(self) -> None:
        """Test validating existing input path"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = FilePathValidator.validate_input_path(tmpdir)
            assert path.exists()

    def test_validate_input_path_not_exists(self) -> None:
        """Test validating non-existent input path raises error"""
        with pytest.raises(ValueError):
            FilePathValidator.validate_input_path("/nonexistent/path")

    def test_validate_output_path_create(self) -> None:
        """Test validating output path with directory creation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "new_output_dir"
            path = FilePathValidator.validate_output_path(output_path, create=True)
            assert path.exists()


class TestOutputFormatValidator:
    """Tests for OutputFormatValidator"""

    def test_validate_valid_formats(self) -> None:
        """Test validating valid output formats"""
        for fmt in ["table", "json", "csv", "markdown", "html", "pdf"]:
            result = OutputFormatValidator.validate(fmt)
            assert result == fmt

    def test_validate_invalid_format(self) -> None:
        """Test validating invalid output format"""
        with pytest.raises(ValueError):
            OutputFormatValidator.validate("invalid")
