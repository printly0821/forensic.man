"""
I/O module for forensic.man.

Provides streaming file reading, chunk processing, and memory
monitoring optimized for DGX Spark environments.

Modules:
    memory: Memory monitoring with threshold-based adjustments.
    reader: Streaming file reader with encoding detection.
    chunk: Chunk processor for parsing text segments.
    buffer: Buffer manager for chunk boundary handling.
    merger: Segment merger for split segment handling.
    discovery: File discovery with glob patterns and filtering.
    progress: Progress tracking for batch processing.
    batch: Batch processor for multiple transcript files.
"""

# Phase 3: Batch processing modules
from forensic.io.batch import (
    BatchConfig,
    BatchProcessingError,
    BatchProcessorProtocol,
    BatchResult,
    FileProcessingError,
    TranscriptBatchProcessor,
    process_directory,
    process_files,
)
from forensic.io.buffer import (
    DEFAULT_BUFFER_SIZE_LIMIT,
    BufferManager,
    BufferManagerProtocol,
    BufferOverflowError,
    BufferState,
    InvalidUTF8Error,
    find_last_complete_char,
    get_utf8_char_length,
    is_valid_utf8_sequence,
)
from forensic.io.chunk import (
    ChunkProcessor,
    ChunkProcessorProtocol,
    DecodingError,
    TimestampedChunkProcessor,
)
from forensic.io.discovery import (
    DirectoryNotFoundError,
    FileDiscovery,
    FileDiscoveryProtocol,
    FileFilter,
    FileInfo,
    InvalidFilterError,
    SortOrder,
    discover_files,
)
from forensic.io.memory import (
    CRITICAL_BATCH_SIZE,
    CRITICAL_CHUNK_SIZE,
    DEFAULT_BATCH_SIZE,
    DEFAULT_CHUNK_SIZE,
    DGX_SPARK_BATCH_SIZE,
    DGX_SPARK_CHUNK_SIZE,
    DGX_SPARK_MEMORY_THRESHOLD_GB,
    MEMORY_CRITICAL_THRESHOLD_GB,
    MEMORY_WARNING_THRESHOLD_GB,
    WARNING_BATCH_SIZE,
    WARNING_CHUNK_SIZE,
    MemoryMonitor,
    MemoryMonitorProtocol,
    MemoryState,
    clear_memory_monitor,
    get_memory_monitor,
)
from forensic.io.merger import (
    DEFAULT_MIN_GAP,
    DEFAULT_TIME_TOLERANCE,
    MergeError,
    MergeStats,
    SegmentMerger,
    SegmentMergerProtocol,
    detect_split_segments,
    merge_all_continuous,
    validate_segment_continuity,
)
from forensic.io.progress import (
    BatchProgress,
    FileProgress,
    NoActiveFileError,
    ProgressCallback,
    ProgressCallbackError,
    ProgressTracker,
    ProgressTrackerProtocol,
    SimpleProgressCallback,
    create_progress_tracker,
)
from forensic.io.reader import (
    EncodingDetectionError,
    FileNotOpenError,
    StreamReader,
    StreamReaderProtocol,
    read_file_streaming,
)

__all__ = [
    # Buffer module
    "BufferManager",
    "BufferManagerProtocol",
    "BufferState",
    "BufferOverflowError",
    "InvalidUTF8Error",
    "DEFAULT_BUFFER_SIZE_LIMIT",
    "is_valid_utf8_sequence",
    "get_utf8_char_length",
    "find_last_complete_char",
    # Chunk module
    "ChunkProcessor",
    "ChunkProcessorProtocol",
    "TimestampedChunkProcessor",
    "DecodingError",
    # Memory module
    "MemoryMonitor",
    "MemoryMonitorProtocol",
    "MemoryState",
    "get_memory_monitor",
    "clear_memory_monitor",
    "MEMORY_WARNING_THRESHOLD_GB",
    "MEMORY_CRITICAL_THRESHOLD_GB",
    "DEFAULT_CHUNK_SIZE",
    "DGX_SPARK_CHUNK_SIZE",
    "WARNING_CHUNK_SIZE",
    "CRITICAL_CHUNK_SIZE",
    "DEFAULT_BATCH_SIZE",
    "DGX_SPARK_BATCH_SIZE",
    "WARNING_BATCH_SIZE",
    "CRITICAL_BATCH_SIZE",
    "DGX_SPARK_MEMORY_THRESHOLD_GB",
    # Merger module
    "SegmentMerger",
    "SegmentMergerProtocol",
    "MergeStats",
    "MergeError",
    "DEFAULT_TIME_TOLERANCE",
    "DEFAULT_MIN_GAP",
    "detect_split_segments",
    "merge_all_continuous",
    "validate_segment_continuity",
    # Reader module
    "StreamReader",
    "StreamReaderProtocol",
    "FileNotOpenError",
    "EncodingDetectionError",
    "read_file_streaming",
    # Discovery module (Phase 3)
    "FileDiscovery",
    "FileDiscoveryProtocol",
    "FileFilter",
    "FileInfo",
    "SortOrder",
    "DirectoryNotFoundError",
    "InvalidFilterError",
    "discover_files",
    # Progress module (Phase 3)
    "ProgressTracker",
    "ProgressTrackerProtocol",
    "FileProgress",
    "BatchProgress",
    "ProgressCallback",
    "SimpleProgressCallback",
    "NoActiveFileError",
    "ProgressCallbackError",
    "create_progress_tracker",
    # Batch module (Phase 3)
    "TranscriptBatchProcessor",
    "BatchProcessorProtocol",
    "BatchConfig",
    "BatchResult",
    "BatchProcessingError",
    "FileProcessingError",
    "process_directory",
    "process_files",
]
