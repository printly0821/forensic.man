"""
End-to-End Speech Processing Module.

Chroma-style streaming architecture for speech transcription.
Implements 1:2 interleaved token processing for real-time transcription.

Components:
- StreamingProcessor: 1:2 interleaved token streaming
- LightweightDecoder: 100M params decoder architecture
- CodecWrapper: Audio codec interface wrapper
"""

from forensic.speech.e2e.codec_wrapper import (
    CodecConfig,
    CodecState,
    CodecType,
    CodecWrapper,
    DecodedChunk,
    EncodedChunk,
)
from forensic.speech.e2e.lightweight_decoder import (
    DecoderConfig,
    DecoderState,
    DecodingResult,
    LightweightDecoder,
    TokenSchedule,
)
from forensic.speech.e2e.streaming_processor import (
    ProcessingState,
    ProcessingStats,
    StreamChunk,
    StreamingProcessor,
    StreamingProcessorConfig,
)

__all__ = [
    # Streaming processor
    "StreamingProcessor",
    "StreamingProcessorConfig",
    "StreamChunk",
    "ProcessingStats",
    "ProcessingState",
    # Lightweight decoder
    "LightweightDecoder",
    "DecoderConfig",
    "DecoderState",
    "TokenSchedule",
    "DecodingResult",
    # Codec wrapper
    "CodecWrapper",
    "CodecConfig",
    "CodecState",
    "CodecType",
    "DecodedChunk",
    "EncodedChunk",
]

__version__ = "0.1.0"
