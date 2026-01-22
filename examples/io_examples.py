"""
IO Module Usage Examples

IO 모듈의 사용 예제를 제공합니다.
DGX Spark 환경 최적화를 포함한 대용량 파일 처리를 보여줍니다.

실행 방법:
    python -m examples.io_examples
"""

from pathlib import Path
from typing import Any

# IO 모듈 임포트
from forensic.io.batch import (
    BatchConfig,
    TranscriptBatchProcessor,
    process_directory,
)
from forensic.io.buffer import (
    BufferManager,
    find_last_complete_char,
    get_utf8_char_length,
    is_valid_utf8_sequence,
)
from forensic.io.chunk import ChunkProcessor, TimestampedChunkProcessor
from forensic.io.discovery import (
    FileDiscovery,
    FileFilter,
    SortOrder,
)
from forensic.io.memory import (
    CRITICAL_BATCH_SIZE,
    CRITICAL_CHUNK_SIZE,
    DEFAULT_BATCH_SIZE,
    DEFAULT_CHUNK_SIZE,
    DGX_SPARK_BATCH_SIZE,
    DGX_SPARK_CHUNK_SIZE,
    MEMORY_CRITICAL_THRESHOLD_GB,
    MEMORY_WARNING_THRESHOLD_GB,
    MemoryMonitor,
    MemoryState,
    get_memory_monitor,
)
from forensic.io.merger import (
    MergeStats,
    SegmentMerger,
    detect_split_segments,
    merge_all_continuous,
)
from forensic.io.progress import (
    FileProgress,
    ProgressTracker,
    create_progress_tracker,
)
from forensic.io.reader import StreamReader, read_file_streaming
from forensic.models.transcript import Segment, Transcript

# =============================================================================
# Memory Monitor Examples
# =============================================================================


def example_memory_monitor_basic() -> dict[str, Any]:
    """
    MemoryMonitor 기본 사용 예제입니다.
    """
    print("\n=== Memory Monitor Basic Usage ===")

    monitor = MemoryMonitor()

    # 메모리 상태 확인
    state: MemoryState = monitor.get_memory_state()
    print(f"Memory Usage: {state.usage_gb:.2f} GB / {state.total_gb:.2f} GB")
    print(f"Memory Available: {state.available_gb:.2f} GB")
    print(f"Memory Level: {state.level}")

    # 청크 크기 추천
    chunk_size = monitor.get_recommended_chunk_size()
    batch_size = monitor.get_recommended_batch_size()
    print(f"Recommended Chunk Size: {chunk_size / 1024 / 1024:.2f} MB")
    print(f"Recommended Batch Size: {batch_size}")

    # DGX Spark 정보
    print(f"DGX Spark Optimized: {monitor.dgx_info.is_optimized}")
    if monitor.dgx_info.is_optimized:
        print(f"System: {monitor.dgx_info.system_info}")

    return {
        "memory_usage_gb": state.usage_gb,
        "memory_level": state.level,
        "chunk_size": chunk_size,
        "batch_size": batch_size,
    }


def example_memory_monitor_adaptive() -> None:
    """
    적응형 메모리 관리 예제입니다.
    """
    print("\n=== Adaptive Memory Management ===")

    monitor = get_memory_monitor()

    # 메모리 상태에 따른 동적 처리
    state = monitor.get_memory_state()

    match state.level:
        case "critical":
            chunk_size = CRITICAL_CHUNK_SIZE
            batch_size = CRITICAL_BATCH_SIZE
            # 강제 GC 실행
            freed = monitor.force_gc()
            print(f"Critical level - Freed {freed / 1024 / 1024:.2f} MB")
        case "warning":
            chunk_size = 512 * 1024  # 512KB
            batch_size = 5
            print("Warning level - Reduced chunk size")
        case "normal":
            if monitor.dgx_info.is_optimized:
                chunk_size = DGX_SPARK_CHUNK_SIZE
                batch_size = DGX_SPARK_BATCH_SIZE
                print("Normal level + DGX Spark - Optimized chunk size")
            else:
                chunk_size = DEFAULT_CHUNK_SIZE
                batch_size = DEFAULT_BATCH_SIZE
                print("Normal level - Default chunk size")

    print(f"Adaptive Chunk Size: {chunk_size / 1024 / 1024:.2f} MB")
    print(f"Adaptive Batch Size: {batch_size}")


def example_memory_monitor_thresholds() -> dict[str, float]:
    """
    메모리 임계값 확인 예제입니다.
    """
    print("\n=== Memory Thresholds ===")

    monitor = MemoryMonitor()

    print(f"Warning Threshold: {MEMORY_WARNING_THRESHOLD_GB} GB")
    print(f"Critical Threshold: {MEMORY_CRITICAL_THRESHOLD_GB} GB")

    should_reduce = monitor.should_reduce_chunk_size()
    should_gc = monitor.should_force_gc()

    print(f"Should Reduce Chunk Size: {should_reduce}")
    print(f"Should Force GC: {should_gc}")

    return {
        "warning_threshold": MEMORY_WARNING_THRESHOLD_GB,
        "critical_threshold": MEMORY_CRITICAL_THRESHOLD_GB,
        "current_usage": monitor.get_usage_gb(),
        "should_reduce": should_reduce,
        "should_gc": should_gc,
    }


# =============================================================================
# Stream Reader Examples
# =============================================================================


def example_stream_reader_context_manager() -> list[Segment]:
    """
    StreamReader 컨텍스트 매니저 사용 예제입니다.
    """
    print("\n=== Stream Reader with Context Manager ===")

    # 테스트용 샘플 데이터 생성
    sample_path = Path("/tmp/sample_transcript.txt")
    sample_path.write_text(
        "Speaker A: Hello, this is a test transcript.\n"
        "Speaker B: Hi there! How are you today?\n"
        "Speaker A: I'm doing well, thank you for asking.\n",
        encoding="utf-8",
    )

    segments: list[Segment] = []

    with StreamReader() as reader:
        reader.open(sample_path)

        print(f"File: {reader.path}")
        print(f"Encoding: {reader.encoding}")
        print(f"File Size: {reader.file_size} bytes")

        for chunk in reader.read_chunks():
            text = chunk.decode(reader.encoding)
            print(f"Progress: {reader.get_progress_percent():.1f}%")
            # 간단한 파싱
            if "Speaker" in text:
                segments.append(
                    Segment(
                        id=f"seg_{len(segments)}",
                        speaker="A" if "Speaker A" in text else "B",
                        start_time=len(segments) * 2.0,
                        end_time=(len(segments) + 1) * 2.0,
                        content=text.strip(),
                        confidence=1.0,
                    )
                )

    # 정리
    sample_path.unlink(missing_ok=True)

    print(f"Processed {len(segments)} segments")
    return segments


def example_stream_reader_progress() -> None:
    """
    진행률 추적 예제입니다.
    """
    print("\n=== Stream Reader Progress Tracking ===")

    # 테스트용 대용량 파일 생성
    sample_path = Path("/tmp/large_sample.txt")
    with open(sample_path, "w") as f:
        for i in range(1000):
            f.write(f"Line {i}: Sample content for testing streaming.\n")

    with StreamReader() as reader:
        reader.open(sample_path)

        chunk_count = 0
        for chunk in reader.read_chunks(chunk_size=4096):
            chunk_count += 1
            if chunk_count % 100 == 0:
                print(f"Chunk {chunk_count}: {reader.get_progress_percent():.1f}% complete")

    print(f"Total chunks: {chunk_count}")

    # 정리
    sample_path.unlink(missing_ok=True)


def example_read_file_streaming() -> None:
    """
    편의 함수 `read_file_streaming` 사용 예제입니다.
    """
    print("\n=== Read File Streaming Convenience Function ===")

    sample_path = Path("/tmp/streaming_test.txt")
    sample_path.write_text("Streaming content test\n" * 100, encoding="utf-8")

    total_bytes = 0
    for chunk in read_file_streaming(sample_path, chunk_size=1024):
        total_bytes += len(chunk)

    print(f"Total bytes read: {total_bytes}")

    # 정리
    sample_path.unlink(missing_ok=True)


# =============================================================================
# Chunk Processor Examples
# =============================================================================


def example_chunk_processor_basic() -> list[Segment]:
    """
    ChunkProcessor 기본 사용 예제입니다.
    """
    print("\n=== Chunk Processor Basic Usage ===")

    processor = ChunkProcessor(
        encoding="utf-8",
        default_speaker="unknown",
        default_confidence=1.0,
    )

    # 샘플 청크 데이터
    chunk1 = b"Speaker A: This is the first segment.\n"
    chunk2 = b"Speaker B: This is the second segment.\n"
    chunk3 = b"Speaker A: This is the third segment.\n"

    all_segments: list[Segment] = []

    # 청크 처리
    segments = processor.process(chunk1)
    all_segments.extend(segments)
    print(f"Chunk 1: {len(segments)} segments")

    segments = processor.process(chunk2)
    all_segments.extend(segments)
    print(f"Chunk 2: {len(segments)} segments")

    # 마지막 청크
    segments = processor.process(chunk3, is_last=True)
    all_segments.extend(segments)
    print(f"Chunk 3: {len(segments)} segments")

    # 플러시 (남은 데이터 처리)
    remaining = processor.flush()
    all_segments.extend(remaining)

    for seg in all_segments:
        print(f"  [{seg.speaker}] {seg.content}")

    return all_segments


def example_timestamped_processor() -> list[Segment]:
    """
    TimestampedChunkProcessor 사용 예제입니다.
    """
    print("\n=== Timestamped Chunk Processor ===")

    processor = TimestampedChunkProcessor(encoding="utf-8")

    # 타임스탬프 형식 데이터
    chunk = b"[00:00:00] Speaker A: First message.\n[00:01:30] Speaker B: Second message.\n"

    segments = processor.process(chunk, is_last=True)

    for seg in segments:
        print(f"  [{seg.start_time:.0f}s - {seg.end_time:.0f}s] {seg.speaker}: {seg.content}")

    return segments


def example_chunk_processor_flush() -> None:
    """
    청크 프로세서 플러시 예제입니다.
    """
    print("\n=== Chunk Processor Flush ===")

    processor = ChunkProcessor(encoding="utf-8")

    # 불완전한 세그먼트가 있는 청크
    chunk1 = b"Speaker A: This is a message that spa"
    chunk2 = b"nks across chunk boundaries."

    segments = processor.process(chunk1)
    print(f"After chunk 1: {len(segments)} segments, pending: {processor.get_pending()}")

    segments = processor.process(chunk2, is_last=True)
    print(f"After chunk 2: {len(segments)} segments")

    remaining = processor.flush()
    print(f"After flush: {len(remaining)} segments")


# =============================================================================
# Buffer Manager Examples
# =============================================================================


def example_buffer_manager_basic() -> None:
    """
    BufferManager 기본 사용 예제입니다.
    """
    print("\n=== Buffer Manager Basic Usage ===")

    buffer = BufferManager(size_limit=64 * 1024)  # 64KB

    # 데이터 추가
    chunk1 = b"Hello, World! "
    complete1 = buffer.append(chunk1)
    print(f"Complete: {complete1}")
    print(f"Buffer state: {buffer.get_state()}")

    chunk2 = b"This is more data. "
    complete2 = buffer.append(chunk2)
    print(f"Complete: {complete2}")

    # 플러시
    remaining_bytes, remaining_line = buffer.flush()
    print(f"Remaining bytes: {remaining_bytes}")
    print(f"Remaining line: {remaining_line}")


def example_buffer_manager_utf8() -> None:
    """
    UTF-8 멀티바이트 문자 처리 예제입니다.
    """
    print("\n=== Buffer Manager UTF-8 Handling ===")

    buffer = BufferManager(size_limit=1024)

    # 한글과 emoji 포함 데이터
    korean_text = "안녕하세요 세계!"  # 각 문자 3바이트
    emoji_text = "Hello 😀 World!"  # emoji는 4바이트

    data = (korean_text + emoji_text).encode("utf-8")

    # 중간에서 분리 시도
    mid_point = len(data) // 2
    chunk1 = data[:mid_point]
    chunk2 = data[mid_point:]

    complete1 = buffer.append(chunk1)
    print(f"Chunk 1 complete: {complete1}")
    print(f"Buffer has pending: {buffer.has_pending_data()}")

    complete2 = buffer.append(chunk2)
    print(f"Chunk 2 complete: {complete2}")

    # 전체 텍스트 확인
    full_text = (complete1 + complete2).decode("utf-8")
    print(f"Full text: {full_text}")


def example_buffer_decode_safe() -> None:
    """
    안전한 디코딩 예제입니다.
    """
    print("\n=== Buffer Safe Decoding ===")

    buffer = BufferManager()

    # 불완전한 UTF-8 시퀀스
    text = "Hello" + "안녕" + "하세요"
    data = text.encode("utf-8")

    # 중간에서 자르기 (한글 문자 중간)
    split_at = 7  # "Hello안"의 바이트 중간
    chunk1 = data[:split_at]
    chunk2 = data[split_at:]

    decoded, incomplete = buffer.decode_safe(chunk1)
    print(f"Decoded: {decoded}")
    print(f"Incomplete bytes: {incomplete.hex()}")

    decoded2, incomplete2 = buffer.decode_safe(chunk2)
    print(f"Decoded 2: {decoded2}")
    print(f"Incomplete bytes 2: {incomplete2.hex()}")

    print(f"Full text: {decoded + decoded2}")


def example_utf8_utilities() -> None:
    """
    UTF-8 유틸리티 함수 예제입니다.
    """
    print("\n=== UTF-8 Utility Functions ===")

    # UTF-8 문자 길이 확인
    test_chars = ["A", "\n", "안", "😀"]
    for char in test_chars:
        leading_byte = ord(char.encode("utf-8")[0])
        length = get_utf8_char_length(leading_byte)
        print(f"'{char}': {length} bytes")

    # 마지막 완전한 문자 찾기
    data = "Hello😀World".encode()
    idx = find_last_complete_char(data)
    print(f"Last complete char index: {idx}")
    print(f"Complete part: {data[:idx].decode('utf-8')}")

    # UTF-8 시퀀스 유효성 확인
    valid = is_valid_utf8_sequence(data)
    print(f"Is valid UTF-8: {valid}")


# =============================================================================
# Segment Merger Examples
# =============================================================================


def example_segment_merger_basic() -> list[Segment]:
    """
    SegmentMerger 기본 사용 예제입니다.
    """
    print("\n=== Segment Merger Basic Usage ===")

    merger = SegmentMerger(time_tolerance=0.5)

    # 연속된 세그먼트
    seg1 = Segment(
        id="1", speaker="A", start_time=0.0, end_time=2.0, content="First part", confidence=1.0
    )
    seg2 = Segment(
        id="2", speaker="A", start_time=2.1, end_time=4.0, content="second part", confidence=1.0
    )
    seg3 = Segment(
        id="3",
        speaker="B",
        start_time=4.5,
        end_time=6.0,
        content="Different speaker",
        confidence=1.0,
    )

    # 세그먼트 추가
    completed = merger.add_segment(seg1)
    print(f"After seg1: {len(completed)} completed")

    completed = merger.add_segment(seg2)
    print(f"After seg2: {len(completed)} completed (merged with seg1)")

    completed = merger.add_segment(seg3)
    print(f"After seg3: {len(completed)} completed (seg1+seg2 output)")

    # 플러시
    final = merger.flush()
    all_completed = final
    for seg in all_completed:
        print(f"  [{seg.speaker}] {seg.content} ({seg.start_time}s - {seg.end_time}s)")

    return all_completed


def example_segment_merger_stats() -> MergeStats:
    """
    병합 통계 확인 예제입니다.
    """
    print("\n=== Segment Merger Statistics ===")

    merger = SegmentMerger()

    segments = [
        Segment(
            id=str(i),
            speaker="A",
            start_time=i * 2.0,
            end_time=i * 2.0 + 2.0,
            content=f"Segment {i}",
            confidence=1.0,
        )
        for i in range(10)
    ]

    for seg in segments:
        merger.add_segment(seg)

    merger.flush()

    stats: MergeStats = merger.stats
    print(f"Segments received: {stats.segments_received}")
    print(f"Segments merged: {stats.segments_merged}")
    print(f"Segments output: {stats.segments_output}")
    print(f"Merge ratio: {stats.merge_ratio:.2%}")

    return stats


def example_segment_merger_detection() -> None:
    """
    분할된 세그먼트 감지 예제입니다.
    """
    print("\n=== Split Segment Detection ===")

    segments = [
        Segment(id="1", speaker="A", start_time=0.0, end_time=1.0, content="hel", confidence=1.0),
        Segment(id="2", speaker="A", start_time=1.0, end_time=2.0, content="lo", confidence=1.0),
        Segment(id="3", speaker="B", start_time=2.0, end_time=3.0, content="world", confidence=1.0),
    ]

    # 분할 감지
    splits = detect_split_segments(segments)
    print(f"Detected {len(splits)} split pairs:")
    for i, j in splits:
        print(f"  Segments {i} and {j} may be split")

    # 전체 병합
    merged = merge_all_continuous(segments)
    print(f"Merged to {len(merged)} segments")
    for seg in merged:
        print(f"  [{seg.speaker}] {seg.content}")


# =============================================================================
# File Discovery Examples
# =============================================================================


def example_file_discovery_pattern() -> list[Path]:
    """
    패턴 기반 파일 검색 예제입니다.
    """
    print("\n=== File Discovery by Pattern ===")

    discovery = FileDiscovery()

    # 테스트용 파일 생성
    test_dir = Path("/tmp/test_discovery")
    test_dir.mkdir(exist_ok=True)

    (test_dir / "file1.txt").write_text("content1")
    (test_dir / "file2.txt").write_text("content2")
    (test_dir / "file3.json").write_text("{}")
    (test_dir / "README.md").write_text("# readme")

    # 패턴 검색
    txt_files = discovery.find_by_pattern(test_dir, "*.txt", recursive=False)
    print(f"TXT files: {[f.name for f in txt_files]}")

    all_files = discovery.find_by_pattern(test_dir, "*", recursive=False)
    print(f"All files: {[f.name for f in all_files]}")

    # 정리
    for f in test_dir.glob("*"):
        f.unlink(missing_ok=True)
    test_dir.rmdir()

    return txt_files


def example_file_discovery_filter() -> list[Path]:
    """
    필터 기반 파일 검색 예제입니다.
    """
    print("\n=== File Discovery with Filter ===")

    discovery = FileDiscovery()
    test_dir = Path("/tmp/test_filter")
    test_dir.mkdir(exist_ok=True)

    # 테스트 파일 생성
    (test_dir / "small.txt").write_text("small")
    (test_dir / "large.txt").write_text("x" * 2000)
    (test_dir / "medium.json").write_text("{}", encoding="utf-8")

    # 크기 필터
    size_filter = FileFilter(
        pattern="*.txt",
        min_size=100,  # 100 bytes 이상
        recursive=False,
    )
    filtered = discovery.find(test_dir, size_filter)
    print(f"Files > 100 bytes: {[f.name for f in filtered]}")

    # 확장자 필터
    ext_filter = FileFilter(
        pattern="*",
        recursive=False,
        extensions=[".txt", ".json"],
    )
    filtered = discovery.find(test_dir, ext_filter)
    print(f"TXT and JSON files: {[f.name for f in filtered]}")

    # 정리
    for f in test_dir.glob("*"):
        f.unlink(missing_ok=True)
    test_dir.rmdir()

    return filtered


def example_file_discovery_sorting() -> None:
    """
    정렬 옵션 예제입니다.
    """
    print("\n=== File Discovery Sorting ===")

    discovery = FileDiscovery()
    test_dir = Path("/tmp/test_sort")
    test_dir.mkdir(exist_ok=True)

    # 테스트 파일 생성
    files = [
        ("zebra.txt", 100),
        ("alpha.txt", 300),
        ("beta.txt", 200),
    ]
    for name, size in files:
        (test_dir / name).write_text("x" * size)

    # 이름 오름차순
    by_name = discovery.find_by_pattern(test_dir, "*.txt", sort_order=SortOrder.NAME)
    print(f"By name: {[f.name for f in by_name]}")

    # 크기 오름차순
    by_size = discovery.find_by_pattern(test_dir, "*.txt", sort_order=SortOrder.SIZE)
    print(f"By size: {[f.name for f in by_size]}")

    # 정리
    for f in test_dir.glob("*"):
        f.unlink(missing_ok=True)
    test_dir.rmdir()


def example_file_discovery_stats() -> dict[str, Any]:
    """
    파일 검색 통계 예제입니다.
    """
    print("\n=== File Discovery Statistics ===")

    discovery = FileDiscovery()
    test_dir = Path("/tmp/test_stats")
    test_dir.mkdir(exist_ok=True)

    # 테스트 파일 생성
    (test_dir / "a.txt").write_text("x" * 100)
    (test_dir / "b.txt").write_text("x" * 200)
    (test_dir / "c.json").write_text("{}")
    (test_dir / "d.md").write_text("# doc")

    files = list(test_dir.glob("*"))

    # 총 크기
    total = discovery.get_total_size(files)
    print(f"Total size: {total} bytes")

    # 확장자별 개수
    counts = discovery.count_by_extension(files)
    print(f"By extension: {counts}")

    # 정리
    for f in test_dir.glob("*"):
        f.unlink(missing_ok=True)
    test_dir.rmdir()

    return {"total_size": total, "extension_counts": counts}


# =============================================================================
# Progress Tracker Examples
# =============================================================================


def example_progress_tracker_basic() -> None:
    """
    ProgressTracker 기본 사용 예제입니다.
    """
    print("\n=== Progress Tracker Basic Usage ===")

    tracker = ProgressTracker(total_files=3)

    # 콜백 설정
    def print_progress(path: Path, file_prog: float, overall_prog: float) -> None:
        print(f"  {path.name}: {file_prog:.1%} | Overall: {overall_prog:.1%}")

    tracker.set_callback(print_progress)

    # 파일 처리 시뮬레이션
    for i in range(3):
        file_path = Path(f"file{i}.txt")
        file_size = 1000

        tracker.start_file(file_path, file_size)

        # 청크 처리 시뮬레이션
        for _ in range(5):
            tracker.update_bytes(200)

        tracker.finish_file()

    print(f"Files completed: {tracker.files_completed}")
    print(f"Summary: {tracker.get_summary()}")


def example_progress_tracker_history() -> list[FileProgress]:
    """
    파일 진행 기록 예제입니다.
    """
    print("\n=== Progress Tracker History ===")

    tracker = ProgressTracker(total_files=2)

    # 파일 처리
    tracker.start_file(Path("file1.txt"), 1000)
    tracker.update_bytes(1000)
    tracker.finish_file()

    tracker.start_file(Path("file2.txt"), 2000)
    tracker.update_bytes(1000)
    tracker.update_bytes(1000)
    tracker.finish_file()

    # 기록 확인
    history = tracker.get_file_history()
    print(f"File history: {len(history)} files")
    for fp in history:
        print(f"  {fp.path.name}: {fp.progress:.1%} complete")

    return history


def example_create_progress_tracker() -> None:
    """
    편의 함수 `create_progress_tracker` 사용 예제입니다.
    """
    print("\n=== Create Progress Tracker Convenience Function ===")

    files = [Path("a.txt"), Path("b.txt"), Path("c.txt")]

    tracker = create_progress_tracker(
        files,
        callback=lambda p, fp, op: print(f"{p.name}: {fp:.1%}"),
    )

    print(f"Total files to track: {tracker.total_files}")
    print(f"Files remaining: {tracker.files_remaining}")


# =============================================================================
# Batch Processor Examples
# =============================================================================


def example_batch_processor_config() -> None:
    """
    BatchConfig 설정 예제입니다.
    """
    print("\n=== Batch Processor Configuration ===")

    config = BatchConfig(
        default_chunk_size=4 * 1024 * 1024,  # 4MB
        skip_on_error=True,
        merge_segments=True,
        encoding="utf-8",
        default_speaker="unknown",
    )

    print(f"Default chunk size: {config.default_chunk_size / 1024 / 1024} MB")
    print(f"Skip on error: {config.skip_on_error}")
    print(f"Merge segments: {config.merge_segments}")


def example_batch_processor_basic() -> list[Transcript]:
    """
    TranscriptBatchProcessor 기본 사용 예제입니다.
    """
    print("\n=== Batch Processor Basic Usage ===")

    # 테스트용 파일 생성
    test_dir = Path("/tmp/test_batch")
    test_dir.mkdir(exist_ok=True)

    test_content = """Speaker A: This is a test transcript.
Speaker B: Hello from the other side.
Speaker A: How are you doing today?
Speaker B: I'm doing great, thanks!
"""

    for i in range(3):
        (test_dir / f"transcript_{i}.txt").write_text(test_content)

    # 프로세서 생성
    processor = TranscriptBatchProcessor()

    # 파일 검색
    files = processor.discover_files(test_dir, "*.txt", recursive=False)
    print(f"Found {len(files)} files")

    # 배치 처리
    transcripts: list[Transcript] = []
    for transcript in processor.process_all(
        files,
        on_progress=lambda p, prog: None,  # 진행률 콜백
    ):
        transcripts.append(transcript)
        print(f"  Processed: {transcript.file_path.name}")
        print(f"    Speakers: {', '.join(transcript.speakers)}")
        print(f"    Segments: {transcript.segment_count}")

    # 결과 요약
    summary = processor.get_batch_summary()
    print("\nSummary:")
    print(f"  Successful: {summary['successful_files']}")
    print(f"  Total segments: {summary['total_segments']}")
    print(f"  Total duration: {summary['total_duration_seconds']:.1f}s")

    # 정리
    for f in test_dir.glob("*"):
        f.unlink(missing_ok=True)
    test_dir.rmdir()

    return transcripts


def example_process_directory_convenience() -> None:
    """
    편의 함수 `process_directory` 사용 예제입니다.
    """
    print("\n=== Process Directory Convenience Function ===")

    # 테스트용 파일 생성
    test_dir = Path("/tmp/test_convenience")
    test_dir.mkdir(exist_ok=True)

    (test_dir / "test1.txt").write_text("Speaker A: Test content one.\n")
    (test_dir / "test2.txt").write_text("Speaker B: Test content two.\n")

    # 디렉토리 처리
    count = 0
    for transcript in process_directory(test_dir, "*.txt", recursive=False):
        count += 1
        print(f"  {transcript.file_path.name}: {len(transcript.segments)} segments")

    print(f"Processed {count} files")

    # 정리
    for f in test_dir.glob("*"):
        f.unlink(missing_ok=True)
    test_dir.rmdir()


# =============================================================================
# Integration Examples
# =============================================================================


def example_complete_pipeline() -> dict[str, Any]:
    """
    전체 처리 파이프라인 통합 예제입니다.
    """
    print("\n=== Complete Processing Pipeline ===")

    # 1. 메모리 모니터 확인
    monitor = get_memory_monitor()
    memory_state = monitor.get_memory_state()
    print(f"Memory: {memory_state.usage_gb:.1f}GB ({memory_state.level})")

    # 2. 파일 검색
    discovery = FileDiscovery()
    test_dir = Path("/tmp/test_pipeline")
    test_dir.mkdir(exist_ok=True)

    # 테스트 파일 생성
    for i in range(2):
        content = f"""[00:0{i}:00] Speaker A: Message {i} from speaker A.
[00:0{i}:15] Speaker B: Response {i} from speaker B.
[00:0{i}:30] Speaker A: Reply {i} to speaker B.
"""
        (test_dir / f"transcript_{i}.txt").write_text(content)

    files = discovery.find_by_pattern(test_dir, "*.txt", recursive=False)
    print(f"Found {len(files)} files to process")

    # 3. 배치 처리 설정
    config = BatchConfig(
        default_chunk_size=monitor.get_recommended_chunk_size(),
        merge_segments=True,
        encoding="utf-8",
    )

    # 4. 진행률 추적기 생성
    tracker = ProgressTracker(total_files=len(files))

    def on_progress(path: Path, progress: float) -> None:
        if tracker.files_completed % 1 == 0:  # 매 파일마다 출력
            print(f"  {path.name}: {progress:.1%}")

    # 5. 배치 처리
    processor = TranscriptBatchProcessor(config=config)
    results: list[dict[str, Any]] = []

    for transcript in processor.process_all(files, on_progress=on_progress):
        result = {
            "file": transcript.file_path.name,
            "speakers": transcript.speakers,
            "segment_count": transcript.segment_count,
            "duration": transcript.duration_seconds,
        }
        results.append(result)
        print(f"    -> {result['segment_count']} segments, {len(result['speakers'])} speakers")

    # 6. 결과 요약
    total_segments = sum(r["segment_count"] for r in results)
    total_duration = sum(r["duration"] for r in results)

    summary = {
        "files_processed": len(results),
        "total_segments": total_segments,
        "total_duration": total_duration,
        "memory_level": memory_state.level,
    }

    print("\nPipeline Summary:")
    print(f"  Files: {summary['files_processed']}")
    print(f"  Total segments: {summary['total_segments']}")
    print(f"  Total duration: {summary['total_duration']:.1f}s")

    # 정리
    for f in test_dir.glob("*"):
        f.unlink(missing_ok=True)
    test_dir.rmdir()

    return summary


def example_dgx_spark_optimization() -> dict[str, Any]:
    """
    DGX Spark 최적화 활용 예제입니다.
    """
    print("\n=== DGX Spark Optimization ===")

    monitor = get_memory_monitor()

    print(f"DGX Spark Detected: {monitor.dgx_info.is_optimized}")
    print(f"System Info: {monitor.dgx_info.system_info}")

    # 최적화된 설정
    state = monitor.get_memory_state()
    chunk_size = monitor.get_recommended_chunk_size()
    batch_size = monitor.get_recommended_batch_size()

    config = BatchConfig(
        default_chunk_size=chunk_size,
        merge_segments=True,
    )

    print("\nOptimized Configuration:")
    print(f"  Memory Level: {state.level}")
    print(f"  Chunk Size: {chunk_size / 1024 / 1024:.2f} MB")
    print(f"  Batch Size: {batch_size}")

    # DGX Spark 최적화 확인
    is_optimized = (
        monitor.dgx_info.is_optimized
        and state.level == "normal"
        and chunk_size >= DGX_SPARK_CHUNK_SIZE
    )

    print(f"\nDGX Spark Optimization Active: {is_optimized}")

    return {
        "dgx_detected": monitor.dgx_info.is_optimized,
        "memory_level": state.level,
        "chunk_size_mb": chunk_size / 1024 / 1024,
        "batch_size": batch_size,
        "is_optimized": is_optimized,
    }


# =============================================================================
# Main Entry Point
# =============================================================================


def main() -> None:
    """
    모든 예제를 실행하는 메인 함수입니다.
    """
    print("=" * 60)
    print("IO Module Usage Examples")
    print("=" * 60)

    examples = [
        (
            "Memory Monitor",
            [
                example_memory_monitor_basic,
                example_memory_monitor_adaptive,
                example_memory_monitor_thresholds,
            ],
        ),
        (
            "Stream Reader",
            [
                example_stream_reader_context_manager,
                example_stream_reader_progress,
                example_read_file_streaming,
            ],
        ),
        (
            "Chunk Processor",
            [
                example_chunk_processor_basic,
                example_timestamped_processor,
                example_chunk_processor_flush,
            ],
        ),
        (
            "Buffer Manager",
            [
                example_buffer_manager_basic,
                example_buffer_manager_utf8,
                example_buffer_decode_safe,
                example_utf8_utilities,
            ],
        ),
        (
            "Segment Merger",
            [
                example_segment_merger_basic,
                example_segment_merger_stats,
                example_segment_merger_detection,
            ],
        ),
        (
            "File Discovery",
            [
                example_file_discovery_pattern,
                example_file_discovery_filter,
                example_file_discovery_sorting,
                example_file_discovery_stats,
            ],
        ),
        (
            "Progress Tracker",
            [
                example_progress_tracker_basic,
                example_progress_tracker_history,
                example_create_progress_tracker,
            ],
        ),
        (
            "Batch Processor",
            [
                example_batch_processor_config,
                example_batch_processor_basic,
                example_process_directory_convenience,
            ],
        ),
        (
            "Integration",
            [
                example_complete_pipeline,
                example_dgx_spark_optimization,
            ],
        ),
    ]

    for category, funcs in examples:
        print("\n" + "=" * 60)
        print(f"{category} Examples")
        print("=" * 60)

        for func in funcs:
            try:
                func()
            except Exception as e:
                print(f"\nError in {func.__name__}: {e}")

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
