"""
Unit tests for E2E streaming speech processing modules.

Tests for streaming processor, lightweight decoder, and codec wrapper.
All tests use mocking to avoid requiring actual model loading.
"""

from unittest.mock import Mock

import numpy as np
import pytest

from forensic.speech.e2e import (
    CodecConfig,
    CodecState,
    CodecType,
    CodecWrapper,
    DecodedChunk,
    DecoderConfig,
    DecoderState,
    DecodingResult,
    EncodedChunk,
    LightweightDecoder,
    ProcessingState,
    ProcessingStats,
    StreamChunk,
    StreamingProcessor,
    StreamingProcessorConfig,
    TokenSchedule,
)


class TestStreamingProcessorConfig:
    """Tests for StreamingProcessorConfig."""

    def test_config_attributes(self):
        """Test config has expected attributes."""
        config = StreamingProcessorConfig()

        assert config.SAMPLE_RATE == 24000
        assert config.CHUNK_DURATION_SEC == 5.0
        assert config.TEXT_TOKENS_PER_STEP == 1
        assert config.AUDIO_TOKENS_PER_STEP == 2
        assert config.TARGET_TTFT_MS == 150.0
        assert config.TARGET_RTF == 0.5

    def test_config_custom(self):
        """Test custom configuration."""
        config = StreamingProcessorConfig(
            SAMPLE_RATE=16000,
            CHUNK_DURATION_SEC=10.0,
        )

        assert config.SAMPLE_RATE == 16000
        assert config.CHUNK_DURATION_SEC == 10.0


class TestStreamChunk:
    """Tests for StreamChunk dataclass."""

    def test_create_chunk(self):
        """Test creating a stream chunk."""
        audio = np.random.randn(48000).astype(np.float32)
        chunk = StreamChunk(
            audio=audio,
            sample_rate=24000,
            duration=2.0,
            chunk_id="test_chunk",
        )

        assert chunk.chunk_id == "test_chunk"
        assert chunk.sample_rate == 24000
        assert chunk.duration == 2.0
        assert chunk.is_final is False

    def test_frame_count(self):
        """Test frame count property."""
        audio = np.random.randn(48000).astype(np.float32)
        chunk = StreamChunk(
            audio=audio,
            sample_rate=24000,
            duration=2.0,
            chunk_id="test",
        )

        assert chunk.frame_count == 48000

    def test_token_estimate(self):
        """Test token estimate calculation."""
        # 320 samples per token estimate
        audio = np.random.randn(3200).astype(np.float32)
        chunk = StreamChunk(
            audio=audio,
            sample_rate=24000,
            duration=0.133,
            chunk_id="test",
        )

        assert chunk.token_estimate == 10


class TestProcessingStats:
    """Tests for ProcessingStats dataclass."""

    def test_default_stats(self):
        """Test default statistics."""
        stats = ProcessingStats()

        assert stats.chunks_processed == 0
        assert stats.total_duration == 0.0
        assert stats.processing_time == 0.0
        assert stats.ttft_ms == 0.0
        assert stats.rtf == 0.0

    def test_update_rtf(self):
        """Test RTF update."""
        stats = ProcessingStats(
            total_duration=10.0,
            processing_time=4.0,
        )

        stats.update_rtf()

        assert stats.rtf == 0.4

    def test_is_within_target(self):
        """Test RTF target check."""
        stats = ProcessingStats(rtf=0.3)
        assert stats.is_within_target() is True

        stats.rtf = 0.6
        assert stats.is_within_target() is False


class TestStreamingProcessor:
    """Tests for StreamingProcessor class."""

    def test_init_default(self):
        """Test default initialization."""
        processor = StreamingProcessor()

        assert processor.config.SAMPLE_RATE == 24000
        assert processor.get_state() == ProcessingState.IDLE

    def test_init_with_config(self):
        """Test initialization with custom config."""
        config = StreamingProcessorConfig(CHUNK_DURATION_SEC=10.0)
        processor = StreamingProcessor(config=config)

        assert processor.config.CHUNK_DURATION_SEC == 10.0

    def test_init_with_callback(self):
        """Test initialization with progress callback."""
        callback = Mock()
        processor = StreamingProcessor(progress_callback=callback)

        assert processor.progress_callback is callback

    def test_create_chunk(self):
        """Test creating a stream chunk."""
        processor = StreamingProcessor()
        audio = np.random.randn(48000).astype(np.float32)

        chunk = processor.create_chunk(audio, 24000, "test_001")

        assert chunk.chunk_id == "test_001"
        assert chunk.sample_rate == 24000
        assert chunk.frame_count == 48000
        assert chunk.is_final is False

    def test_create_chunk_final(self):
        """Test creating a final chunk."""
        processor = StreamingProcessor()
        audio = np.random.randn(48000).astype(np.float32)

        chunk = processor.create_chunk(audio, 24000, "final_001", is_final=True)

        assert chunk.is_final is True

    def test_validate_chunk_valid(self):
        """Test validation of valid chunk."""
        processor = StreamingProcessor()
        audio = np.random.randn(48000).astype(np.float32)
        chunk = processor.create_chunk(audio, 24000, "test")

        assert processor.validate_chunk(chunk) is True

    def test_validate_chunk_empty(self):
        """Test validation rejects empty chunk."""
        processor = StreamingProcessor()
        chunk = StreamChunk(
            audio=np.array([]),
            sample_rate=24000,
            duration=0.0,
            chunk_id="empty",
        )

        assert processor.validate_chunk(chunk) is False

    def test_validate_chunk_wrong_sample_rate(self):
        """Test validation rejects wrong sample rate."""
        processor = StreamingProcessor()
        audio = np.random.randn(16000).astype(np.float32)
        chunk = StreamChunk(
            audio=audio,
            sample_rate=16000,
            duration=1.0,
            chunk_id="wrong_sr",
        )

        assert processor.validate_chunk(chunk) is False

    def test_process_chunk_yields_tokens(self):
        """Test processing chunk yields tokens."""
        processor = StreamingProcessor()
        audio = np.random.randn(120000).astype(np.float32)  # 5 seconds at 24kHz
        chunk = processor.create_chunk(audio, 24000, "test")

        tokens = list(processor.process_chunk(chunk))

        assert len(tokens) > 0
        assert all(isinstance(t, str) for t in tokens)

    def test_process_chunk_updates_stats(self):
        """Test processing updates statistics."""
        processor = StreamingProcessor()
        audio = np.random.randn(120000).astype(np.float32)
        chunk = processor.create_chunk(audio, 24000, "test")

        list(processor.process_chunk(chunk))
        stats = processor.get_stats()

        assert stats.chunks_processed == 1
        assert stats.total_duration == 5.0

    def test_process_stream_with_chunks(self):
        """Test processing stream of chunks."""
        processor = StreamingProcessor()

        chunks = [
            processor.create_chunk(np.random.randn(120000).astype(np.float32), 24000, f"chunk_{i}")
            for i in range(3)
        ]
        chunks[-1].is_final = True

        tokens = list(processor.process_stream(iter(chunks)))

        assert len(tokens) > 0
        assert processor.get_state() == ProcessingState.COMPLETED

    def test_get_ttft(self):
        """Test getting TTFT."""
        processor = StreamingProcessor()
        audio = np.random.randn(120000).astype(np.float32)
        chunk = processor.create_chunk(audio, 24000, "test")

        list(processor.process_chunk(chunk))
        ttft = processor.get_ttft()

        assert ttft >= 0

    def test_reset(self):
        """Test resetting processor."""
        processor = StreamingProcessor()
        audio = np.random.randn(120000).astype(np.float32)
        chunk = processor.create_chunk(audio, 24000, "test")

        list(processor.process_chunk(chunk))
        processor.reset()

        assert processor.get_state() == ProcessingState.IDLE
        assert processor.get_stats().chunks_processed == 0


class TestDecoderConfig:
    """Tests for DecoderConfig."""

    def test_config_attributes(self):
        """Test config has expected attributes."""
        config = DecoderConfig()

        assert config.NUM_PARAMS == 100_000_000
        assert config.NUM_LAYERS == 6
        assert config.HIDDEN_SIZE == 512
        assert config.NUM_CODEBOOKS == 8

    def test_model_size_mb(self):
        """Test model size calculation."""
        config = DecoderConfig()

        # 100M params * 2 bytes (fp16) / 1024 / 1024
        expected_size = (100_000_000 * 2) / (1024 * 1024)
        assert abs(config.model_size_mb - expected_size) < 0.1


class TestTokenSchedule:
    """Tests for TokenSchedule dataclass."""

    def test_create_schedule(self):
        """Test creating a token schedule."""
        schedule = TokenSchedule(
            text_token="<T0>",
            audio_tokens=[0, 1],
            step_index=0,
            total_steps=10,
        )

        assert schedule.text_token == "<T0>"
        assert schedule.audio_tokens == [0, 1]
        assert schedule.step_index == 0

    def test_is_first_step(self):
        """Test first step detection."""
        schedule = TokenSchedule(
            text_token="<T0>",
            audio_tokens=[0, 1],
            step_index=0,
            total_steps=10,
        )

        assert schedule.is_first_step is True

        schedule.step_index = 1
        assert schedule.is_first_step is False

    def test_is_last_step(self):
        """Test last step detection."""
        schedule = TokenSchedule(
            text_token="<T0>",
            audio_tokens=[0, 1],
            step_index=9,
            total_steps=10,
        )

        assert schedule.is_last_step is True

        schedule.step_index = 8
        assert schedule.is_last_step is False

    def test_progress(self):
        """Test progress calculation."""
        schedule = TokenSchedule(
            text_token="<T0>",
            audio_tokens=[0, 1],
            step_index=5,
            total_steps=10,
        )

        assert schedule.progress == 0.5


class TestDecodingResult:
    """Tests for DecodingResult dataclass."""

    def test_create_result(self):
        """Test creating a decoding result."""
        result = DecodingResult(
            text="Hello",
            audio_tokens=[0, 1],
            confidence=0.95,
            step_index=0,
        )

        assert result.text == "Hello"
        assert result.audio_tokens == [0, 1]
        assert result.confidence == 0.95
        assert result.is_final is False

    def test_iterable(self):
        """Test result is iterable."""
        result = DecodingResult(
            text="Hello",
            audio_tokens=[0, 1],
            confidence=0.95,
            step_index=0,
        )

        text, tokens = result
        assert text == "Hello"
        assert tokens == [0, 1]


class TestLightweightDecoder:
    """Tests for LightweightDecoder class."""

    def test_init_default(self):
        """Test default initialization."""
        decoder = LightweightDecoder()

        assert decoder.config.NUM_PARAMS == 100_000_000
        assert decoder.get_state() == DecoderState.IDLE

    def test_init_with_config(self):
        """Test initialization with custom config."""
        config = DecoderConfig(NUM_LAYERS=12)
        decoder = LightweightDecoder(config=config)

        assert decoder.config.NUM_LAYERS == 12

    def test_load_model(self):
        """Test model loading."""
        decoder = LightweightDecoder()
        decoder.load_model()

        assert decoder.is_ready() is True
        assert decoder.get_state() == DecoderState.READY

    def test_decode_step_requires_model(self):
        """Test decode step requires loaded model."""
        decoder = LightweightDecoder()

        with pytest.raises(RuntimeError, match="Model not loaded"):
            decoder._decode_step("<T0>", [0, 1])

    def test_decode_step_after_load(self):
        """Test decode step after loading model."""
        decoder = LightweightDecoder()
        decoder.load_model()

        result = decoder._decode_step("<T0>", [0, 1])

        assert isinstance(result, DecodingResult)
        assert result.step_index == 0

    def test_decode_schedule(self):
        """Test decoding token schedule."""
        decoder = LightweightDecoder()
        decoder.load_model()

        schedules = [
            TokenSchedule("<T0>", [0, 1], 0, 3),
            TokenSchedule("<T1>", [2, 3], 1, 3),
            TokenSchedule("<T2>", [4, 5], 2, 3),
        ]

        results = list(decoder.decode_schedule(iter(schedules)))

        assert len(results) == 3
        assert results[0].step_index == 0
        assert results[2].is_final is True

    def test_reset(self):
        """Test resetting decoder."""
        decoder = LightweightDecoder()
        decoder.load_model()
        decoder._decode_step("<T0>", [0, 1])

        decoder.reset()

        assert decoder._current_step == 0

    def test_parameter_count(self):
        """Test parameter count property."""
        decoder = LightweightDecoder()

        assert decoder.parameter_count == 100_000_000


class TestCodecConfig:
    """Tests for CodecConfig."""

    def test_config_attributes(self):
        """Test config has expected attributes."""
        config = CodecConfig()

        assert config.CODEC_TYPE == CodecType.MIMI
        assert config.SAMPLE_RATE == 24000
        assert config.NUM_CODEBOOKS == 8
        assert config.BANDWIDTH == 6.0

    def test_frame_size_samples(self):
        """Test frame size calculation."""
        config = CodecConfig()

        expected = 24000 // 75  # 320
        assert config.frame_size_samples == expected

    def test_frame_duration_ms(self):
        """Test frame duration calculation."""
        config = CodecConfig()

        expected = 1000.0 / 75  # ~13.33ms
        assert abs(config.frame_duration_ms - expected) < 0.1


class TestEncodedChunk:
    """Tests for EncodedChunk dataclass."""

    def test_create_encoded(self):
        """Test creating encoded chunk."""
        tokens = [[i * 10 + j for j in range(10)] for i in range(8)]
        chunk = EncodedChunk(
            tokens=tokens,
            num_frames=10,
            duration=1.0,
            chunk_id="encoded_001",
        )

        assert chunk.num_codebooks == 8
        assert chunk.num_frames == 10

    def test_total_tokens(self):
        """Test total tokens calculation."""
        tokens = [[i * 10 + j for j in range(10)] for i in range(8)]
        chunk = EncodedChunk(
            tokens=tokens,
            num_frames=10,
            duration=1.0,
            chunk_id="test",
        )

        assert chunk.total_tokens == 80  # 8 codebooks * 10 frames


class TestDecodedChunk:
    """Tests for DecodedChunk dataclass."""

    def test_create_decoded(self):
        """Test creating decoded chunk."""
        audio = np.random.randn(48000).astype(np.float32)
        chunk = DecodedChunk(
            audio=audio,
            sample_rate=24000,
            duration=2.0,
            chunk_id="decoded_001",
        )

        assert chunk.chunk_id == "decoded_001"
        assert chunk.frame_count == 48000


class TestCodecWrapper:
    """Tests for CodecWrapper class."""

    def test_init_default(self):
        """Test default initialization."""
        codec = CodecWrapper()

        assert codec.config.CODEC_TYPE == CodecType.MIMI
        assert codec.get_state() == CodecState.IDLE

    def test_init_with_config(self):
        """Test initialization with custom config."""
        config = CodecConfig(NUM_CODEBOOKS=4)
        codec = CodecWrapper(config=config)

        assert codec.config.NUM_CODEBOOKS == 4

    def test_load_model(self):
        """Test model loading."""
        codec = CodecWrapper()
        codec.load_model()

        assert codec.is_ready() is True
        assert codec.get_state() == CodecState.READY

    def test_encode_requires_model(self):
        """Test encode requires loaded model."""
        codec = CodecWrapper()
        audio = np.random.randn(48000).astype(np.float32)

        # Should auto-load
        result = codec.encode(audio, "test")

        assert result.num_frames > 0

    def test_encode_stereo_to_mono(self):
        """Test encoding converts stereo to mono."""
        codec = CodecWrapper()
        codec.load_model()

        # Create stereo audio
        audio = np.random.randn(48000, 2).astype(np.float32)
        result = codec.encode(audio, "test")

        # Should succeed without error
        assert result.num_frames > 0

    def test_decode(self):
        """Test decoding."""
        codec = CodecWrapper()
        codec.load_model()

        encoded = EncodedChunk(
            tokens=[[i for i in range(10)] for _ in range(8)],
            num_frames=10,
            duration=0.133,
            chunk_id="test",
        )

        decoded = codec.decode(encoded)

        assert decoded.chunk_id == "test"
        assert decoded.sample_rate == 24000

    def test_bandwidth_property(self):
        """Test bandwidth property."""
        codec = CodecConfig()
        assert codec.TOTAL_BANDWIDTH == 48.0
