"""
Unit tests for unified transcriber factory module.

Tests for TranscriberFactory and related types.
All tests use mocking to avoid requiring actual model loading.
"""

from unittest.mock import Mock, patch

import pytest

from forensic.speech.unified import (
    TranscriberFactory,
    TranscriberType,
)


class TestTranscriberType:
    """Tests for TranscriberType enum."""

    def test_all_types(self):
        """Test all transcriber types exist."""
        assert TranscriberType.AUTO.value == "auto"
        assert TranscriberType.WHISPER.value == "whisper"
        assert TranscriberType.STREAMING.value == "streaming"
        assert TranscriberType.E2E.value == "e2e"

    def test_from_string(self):
        """Test creating from string."""
        assert TranscriberType("auto") == TranscriberType.AUTO
        assert TranscriberType("whisper") == TranscriberType.WHISPER


class TestTranscriberFactory:
    """Tests for TranscriberFactory class."""

    def test_init_default(self):
        """Test default initialization."""
        factory = TranscriberFactory()

        assert factory.default_type == TranscriberType.AUTO
        assert factory.device == "cuda"
        assert factory.model_size == "large-v3"

    def test_init_custom(self):
        """Test initialization with custom parameters."""
        factory = TranscriberFactory(
            default_type=TranscriberType.WHISPER,
            device="cpu",
            model_size="base",
        )

        assert factory.default_type == TranscriberType.WHISPER
        assert factory.device == "cpu"
        assert factory.model_size == "base"

    def test_is_whisper_available_true(self):
        """Test Whisper availability check returns True."""
        with patch("builtins.__import__", return_value=Mock()):
            factory = TranscriberFactory()
            factory._is_whisper_available = Mock(return_value=True)

            assert factory._is_whisper_available() is True

    def test_is_whisper_available_false(self):
        """Test Whisper availability check returns False."""
        factory = TranscriberFactory()
        factory._is_whisper_available = Mock(return_value=False)

        assert factory._is_whisper_available() is False

    def test_is_gpu_available_no_torch(self):
        """Test GPU availability check returns False without torch."""
        factory = TranscriberFactory()

        with patch("builtins.__import__", side_effect=ImportError):
            result = factory._is_gpu_available()
            assert result is False

    def test_create_e2e_transcriber(self):
        """Test creating E2E transcriber."""
        factory = TranscriberFactory()

        processor = factory._create_e2e_transcriber()

        assert processor is not None

    def test_select_auto_backend_no_backend(self):
        """Test auto selection with no backend available."""
        factory = TranscriberFactory()
        factory._is_whisper_available = Mock(return_value=False)

        with pytest.raises(RuntimeError, match="No transcriber backend available"):
            factory._select_auto_backend()

    def test_create_invalid_backend(self):
        """Test creating with invalid backend type."""
        factory = TranscriberFactory()

        with pytest.raises(ValueError, match="Invalid backend"):
            factory.create("invalid")

    def test_create_e2e_backend(self):
        """Test creating E2E backend."""
        factory = TranscriberFactory()

        transcriber = factory.create("e2e")

        assert transcriber is not None

    def test_get_available_backends_none(self):
        """Test getting available backends when none available."""
        factory = TranscriberFactory()
        factory._is_whisper_available = Mock(return_value=False)

        available = factory.get_available_backends()

        assert len(available) == 0

    def test_get_info(self):
        """Test getting factory information."""
        factory = TranscriberFactory(
            default_type=TranscriberType.WHISPER,
            device="cpu",
            model_size="base",
        )
        factory._is_whisper_available = Mock(return_value=False)
        factory._is_gpu_available = Mock(return_value=False)

        info = factory.get_info()

        assert info["default_type"] == "whisper"
        assert info["device"] == "cpu"
        assert info["model_size"] == "base"
        assert info["gpu_available"] is False
        assert info["whisper_available"] is False


class TestTranscriberFactoryIntegration:
    """Integration tests for TranscriberFactory."""

    def test_factory_creates_e2e_backend(self):
        """Test factory can create E2E backend."""
        factory = TranscriberFactory()

        e2e = factory.create("e2e")

        assert e2e is not None
