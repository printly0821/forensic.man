"""forensic analyze command"""

import json
import sys
import time
from contextlib import suppress
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console

from forensic.cli.models.config import ForensicCLIConfig
from forensic.cli.models.progress import ProgressState
from forensic.cli.models.result import AnalyzeResult, SpeakerStats
from forensic.cli.output.panel import PanelFormatter
from forensic.cli.utils.signal_handler import GracefulInterrupt
from forensic.cli.utils.validators import FilePathValidator


@click.command()
@click.option(
    "--input", "-i", required=True, type=click.Path(exists=True), help="입력 디렉토리 경로"
)
@click.option("--output", "-o", required=True, type=click.Path(), help="출력 디렉토리 경로")
@click.option("--force", "-f", is_flag=True, help="캐시 무시하고 강제 재분석")
@click.option("--parallel", "-p", is_flag=True, help="멀티코어 병렬 처리")
@click.option("--gpu", is_flag=True, help="GPU 가속 사용")
@click.option("--no-cache", is_flag=True, help="캐시 사용 안 함")
@click.pass_context
def analyze(
    ctx: click.Context,
    input: str,
    output: str,
    force: bool,
    parallel: bool,
    gpu: bool,
    no_cache: bool,
) -> None:
    """전체 분석 파이프라인 실행"""
    _ = force, parallel, gpu, no_cache  # Unused options reserved for future use

    console_manager = ctx.obj.get("console_manager")
    config: ForensicCLIConfig = ctx.obj.get("config", ForensicCLIConfig())
    console: Console = ctx.obj.get("console", Console())

    try:
        input_path = FilePathValidator.validate_input_path(input)
        output_path = FilePathValidator.validate_output_path(output, create=True)
    except ValueError as e:
        console_manager.error(f"경로 오류: {e}")
        sys.exit(1)

    result = AnalyzeResult(output_path=output_path)

    progress_state = ProgressState.create_new(
        job_id=f"analyze_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        total_files=len(list(input_path.glob("**/*"))),
        output_path=output_path,
    )

    def save_partial() -> None:
        progress_state.partial_results_path = output_path / ".progress.json"
        with open(progress_state.partial_results_path, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, indent=2, ensure_ascii=False, default=str)

    start_time = time.time()

    with GracefulInterrupt(progress_state, save_partial):
        console_manager.info("1단계: 파일 발견 중...")
        files = _discover_files(input_path)
        progress_state.total_files = len(files)
        console_manager.verbose(f"발견된 파일: {len(files)}개")

        console_manager.info("2단계: 녹취록 로드 중...")
        transcripts = _load_transcripts(files, console_manager)
        result.total_files = len(transcripts)
        result.total_segments = sum(len(getattr(t, "segments", [])) for t in transcripts)

        console_manager.info("3단계: 증거 추출 중...")
        evidence_list = _extract_evidence(transcripts, config, console_manager)
        result.total_evidence = len(evidence_list)

        console_manager.info("4단계: 통계 생성 중...")
        speaker_stats = _generate_speaker_stats(transcripts, evidence_list)
        for stats in speaker_stats:
            result.add_speaker_stats(stats)

        console_manager.info("5단계: 결과 저장 중...")
        _save_results(result, output_path, console_manager)

    result.processing_time_seconds = time.time() - start_time
    _display_summary(result, console, console_manager)


def _discover_files(input_path: Path) -> list[Path]:
    extensions = [".json", ".txt", ".csv", ".md"]
    files = []
    for ext in extensions:
        files.extend(input_path.glob(f"**/*{ext}"))
    return list(set(files))


def _load_transcripts(files: list[Path], console_manager) -> list:
    transcripts = []
    for file_path in files:
        if file_path.suffix == ".json":
            with suppress(Exception):
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and "segments" in data:
                    from forensic.models import Transcript

                    transcripts.append(Transcript.model_validate(data))
                    console_manager.verbose(f"로드됨: {file_path.name}")
    return transcripts


def _extract_evidence(transcripts: list, config: ForensicCLIConfig, console_manager) -> list:
    from forensic.evidence import EvidenceExtractor

    _ = config  # Reserved for future use

    extractor = EvidenceExtractor()
    evidence_list = []
    for transcript in transcripts:
        try:
            evidence = extractor.extract_from_transcript(transcript)
            evidence_list.extend(evidence)
        except Exception as e:
            console_manager.verbose(f"증거 추출 오류: {e}")
    return evidence_list


def _generate_speaker_stats(transcripts: list, evidence_list: list) -> list[SpeakerStats]:
    stats_dict = {}
    for transcript in transcripts:
        segments = getattr(transcript, "segments", [])
        for segment in segments:
            speaker_id = getattr(segment, "speaker_id", "unknown")
            if speaker_id not in stats_dict:
                stats_dict[speaker_id] = SpeakerStats(
                    speaker_id=speaker_id,
                    speaker_name=getattr(segment, "speaker_name", speaker_id),
                )
            stats = stats_dict[speaker_id]
            stats.total_segments += 1
            text = getattr(segment, "text", "")
            stats.total_words += len(text.split())

    for evidence in evidence_list:
        speaker_id = getattr(evidence, "speaker_id", None)
        if speaker_id and speaker_id in stats_dict:
            stats_dict[speaker_id].evidence_count += 1

    return list(stats_dict.values())


def _save_results(result: AnalyzeResult, output_path: Path, console_manager) -> None:
    results_file = output_path / "analysis_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(result.model_dump(), f, indent=2, ensure_ascii=False, default=str)
    console_manager.success(f"결과 저장됨: {results_file}")


def _display_summary(result: AnalyzeResult, console: Console, console_manager) -> None:
    _ = console_manager  # Reserved for future use
    panel = PanelFormatter.analysis_summary(result.model_dump())
    console.print(panel)
