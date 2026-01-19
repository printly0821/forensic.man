"""
설정 관리 시스템 단위 테스트

DGXSparkConfig, SpeakerConfig, AnalysisPeriod, ForensicConfig, ConfigLoader 클래스의 동작을 검증합니다.
"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from pydantic import ValidationError

from forensic.utils.config import (
    AnalysisPeriod,
    ConfigLoader,
    DGXSparkConfig,
    ForensicConfig,
    SpeakerConfig,
    get_config,
    get_config_loader,
    load_config,
)


class TestDGXSparkConfig:
    """DGXSparkConfig 모델 테스트"""

    def test_create_valid_config(self) -> None:
        """유효한 DGX Spark 설정 생성을 검증합니다."""
        config = DGXSparkConfig(
            enabled=True,
            auto_detect=True,
            gpu_acceleration=True,
            memory_limit_gb=100,
            batch_size=50,
        )

        assert config.enabled is True
        assert config.auto_detect is True
        assert config.gpu_acceleration is True
        assert config.memory_limit_gb == 100
        assert config.batch_size == 50

    def test_config_defaults(self) -> None:
        """기본값 설정을 검증합니다."""
        config = DGXSparkConfig()

        assert config.enabled is True
        assert config.auto_detect is True
        assert config.gpu_acceleration is True
        assert config.memory_limit_gb == 100
        assert config.batch_size == 50

    def test_memory_limit_validation(self) -> None:
        """메모리 제약 범위 검증을 합니다."""
        # 유효한 범위
        DGXSparkConfig(memory_limit_gb=1)
        DGXSparkConfig(memory_limit_gb=128)

        # 범위를 벗어난 경우
        with pytest.raises(ValidationError):
            DGXSparkConfig(memory_limit_gb=0)

        with pytest.raises(ValidationError):
            DGXSparkConfig(memory_limit_gb=129)

    def test_batch_size_validation(self) -> None:
        """배치 크기 범위 검증을 합니다."""
        # 유효한 범위
        DGXSparkConfig(batch_size=1)
        DGXSparkConfig(batch_size=1000)

        # 범위를 벗어난 경우
        with pytest.raises(ValidationError):
            DGXSparkConfig(batch_size=0)

        with pytest.raises(ValidationError):
            DGXSparkConfig(batch_size=1001)

    def test_get_effective_memory_limit(self) -> None:
        """실제 메모리 제한 계산을 검증합니다."""
        config = DGXSparkConfig(memory_limit_gb=100)

        # 시스템 메모리가 충분한 경우
        assert config.get_effective_memory_limit(128.0) == 100

        # 시스템 메모리가 부족한 경우 (90% 적용)
        assert config.get_effective_memory_limit(80.0) == 72


class TestSpeakerConfig:
    """SpeakerConfig 모델 테스트"""

    def test_create_valid_speaker(self) -> None:
        """유효한 화자 설정 생성을 검증합니다."""
        speaker = SpeakerConfig(
            id="speaker_1",
            name="홍길동",
            aliases=["길동", "홍씨"],
        )

        assert speaker.id == "speaker_1"
        assert speaker.name == "홍길동"
        assert speaker.aliases == ["길동", "홍씨"]

    def test_speaker_defaults(self) -> None:
        """화자 기본값을 검증합니다."""
        speaker = SpeakerConfig(id="speaker_1", name="홍길동")

        assert speaker.aliases == []

    def test_matches_by_name(self) -> None:
        """이름 일치 확인을 검증합니다."""
        speaker = SpeakerConfig(
            id="speaker_1",
            name="홍길동",
            aliases=["길동", "홍씨"],
        )

        assert speaker.matches("홍길동") is True
        assert speaker.matches("길동") is True
        assert speaker.matches("홍씨") is True
        assert speaker.matches("김철수") is False


class TestAnalysisPeriod:
    """AnalysisPeriod 모델 테스트"""

    def test_create_valid_period(self) -> None:
        """유효한 분석 기간 생성을 검증합니다."""
        period = AnalysisPeriod(start="2025-06-01", end="2025-12-31")

        assert period.start == "2025-06-01"
        assert period.end == "2025-12-31"

    def test_date_format_validation(self) -> None:
        """날짜 형식 검증을 합니다."""
        # 유효한 형식
        AnalysisPeriod(start="2025-06-01", end="2025-12-31")

        # 잘못된 형식
        with pytest.raises(ValidationError, match="Invalid date format"):
            AnalysisPeriod(start="2025/06/01", end="2025-12-31")

        with pytest.raises(ValidationError, match="Invalid date format"):
            AnalysisPeriod(start="06-01-2025", end="2025-12-31")

    def test_date_properties(self) -> None:
        """날짜 속성을 검증합니다."""
        period = AnalysisPeriod(start="2025-06-01", end="2025-12-31")

        assert period.start_date == datetime(2025, 6, 1)
        assert period.end_date == datetime(2025, 12, 31)

    def test_contains_date(self) -> None:
        """날짜 포함 확인을 검증합니다."""
        period = AnalysisPeriod(start="2025-06-01", end="2025-12-31")

        # 범위 내
        assert period.contains(datetime(2025, 6, 1)) is True
        assert period.contains(datetime(2025, 8, 15)) is True
        assert period.contains(datetime(2025, 12, 31)) is True

        # 범위 외
        assert period.contains(datetime(2025, 5, 31)) is False
        assert period.contains(datetime(2026, 1, 1)) is False


class TestForensicConfig:
    """ForensicConfig 모델 테스트"""

    def test_create_valid_config(self) -> None:
        """유효한 전체 설정 생성을 검증합니다."""
        config = ForensicConfig(
            version="0.1.0",
            dgx_spark=DGXSparkConfig(enabled=True),
            speakers=[
                SpeakerConfig(id="speaker_1", name="홍길동"),
                SpeakerConfig(id="speaker_2", name="김철수"),
            ],
            analysis_period=AnalysisPeriod(start="2025-06-01", end="2025-12-31"),
        )

        assert config.version == "0.1.0"
        assert config.dgx_spark.enabled is True
        assert len(config.speakers) == 2
        assert config.analysis_period is not None

    def test_config_defaults(self) -> None:
        """기본값 설정을 검증합니다."""
        config = ForensicConfig()

        assert config.version == "0.1.0"
        assert config.dgx_spark.enabled is True
        assert config.speakers == []
        assert config.analysis_period is None

    def test_get_speaker_by_id(self) -> None:
        """ID로 화자 찾기를 검증합니다."""
        config = ForensicConfig(
            speakers=[
                SpeakerConfig(id="speaker_1", name="홍길동"),
                SpeakerConfig(id="speaker_2", name="김철수"),
            ]
        )

        speaker1 = config.get_speaker_by_id("speaker_1")
        assert speaker1 is not None
        assert speaker1.name == "홍길동"

        speaker_none = config.get_speaker_by_id("speaker_3")
        assert speaker_none is None

    def test_get_speaker_by_name(self) -> None:
        """이름으로 화자 찾기를 검증합니다."""
        config = ForensicConfig(
            speakers=[
                SpeakerConfig(id="speaker_1", name="홍길동", aliases=["길동"]),
                SpeakerConfig(id="speaker_2", name="김철수"),
            ]
        )

        # 이름으로 찾기
        speaker1 = config.get_speaker_by_name("홍길동")
        assert speaker1 is not None
        assert speaker1.id == "speaker_1"

        # 별칭으로 찾기
        speaker2 = config.get_speaker_by_name("길동")
        assert speaker2 is not None
        assert speaker2.id == "speaker_1"

        # 없는 이름
        speaker_none = config.get_speaker_by_name("없는사람")
        assert speaker_none is None

    def test_add_speaker(self) -> None:
        """화자 추가를 검증합니다."""
        config = ForensicConfig()

        speaker = SpeakerConfig(id="speaker_1", name="홍길동")
        config.add_speaker(speaker)

        assert len(config.speakers) == 1
        assert config.speakers[0].id == "speaker_1"

    def test_add_speaker_no_duplicate(self) -> None:
        """중복 화자 미추가를 검증합니다."""
        config = ForensicConfig(
            speakers=[SpeakerConfig(id="speaker_1", name="홍길동")]
        )

        # 동일 ID로 추가 시도
        new_speaker = SpeakerConfig(id="speaker_1", name="홍길동2")
        config.add_speaker(new_speaker)

        # 중복 추가되지 않음
        assert len(config.speakers) == 1
        assert config.speakers[0].name == "홍길동"

    def test_should_use_gpu(self) -> None:
        """GPU 사용 여부 판단을 검증합니다."""
        # GPU 사용 가능
        config1 = ForensicConfig(dgx_spark=DGXSparkConfig(enabled=True, gpu_acceleration=True))
        assert config1.should_use_gpu(cuda_available=True) is True

        # CUDA가 없는 경우
        assert config1.should_use_gpu(cuda_available=False) is False

        # GPU 비활성화
        config2 = ForensicConfig(dgx_spark=DGXSparkConfig(enabled=False))
        assert config2.should_use_gpu(cuda_available=True) is False

        # GPU 가속 비활성화
        config3 = ForensicConfig(dgx_spark=DGXSparkConfig(gpu_acceleration=False))
        assert config3.should_use_gpu(cuda_available=True) is False

    def test_should_auto_detect(self) -> None:
        """자동 감지 여부를 검증합니다."""
        config1 = ForensicConfig(dgx_spark=DGXSparkConfig(enabled=True, auto_detect=True))
        assert config1.should_auto_detect() is True

        config2 = ForensicConfig(dgx_spark=DGXSparkConfig(enabled=False))
        assert config2.should_auto_detect() is False

        config3 = ForensicConfig(dgx_spark=DGXSparkConfig(auto_detect=False))
        assert config3.should_auto_detect() is False


class TestConfigLoader:
    """ConfigLoader 클래스 테스트"""

    def test_init_with_path(self) -> None:
        """경로와 함께 초기화를 검증합니다."""
        path = Path("/test/config.yaml")
        loader = ConfigLoader(path)

        assert loader.config_path == path

    def test_init_without_path(self) -> None:
        """경로 없이 초기화를 검증합니다."""
        loader = ConfigLoader()
        assert loader.config_path is None

    def test_load_nonexistent_file_returns_default(self) -> None:
        """존재하지 않는 파일 로드 시 기본값 반환을 검증합니다."""
        loader = ConfigLoader(Path("/nonexistent/config.yaml"))
        config = loader.load()

        assert isinstance(config, ForensicConfig)
        assert config.version == "0.1.0"
        assert config.dgx_spark.enabled is True

    def test_load_valid_yaml_file(self) -> None:
        """유효한 YAML 파일 로드를 검증합니다."""
        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""forensic:
  version: "0.2.0"
  dgx_spark:
    enabled: true
    gpu_acceleration: true
    memory_limit_gb: 80
    batch_size: 30
  speakers:
    - id: speaker_1
      name: 홍길동
      aliases: [길동]
  analysis_period:
    start: "2025-06-01"
    end: "2025-12-31"
""")
            temp_path = Path(f.name)

        try:
            loader = ConfigLoader(temp_path)
            config = loader.load()

            assert config.version == "0.2.0"
            assert config.dgx_spark.memory_limit_gb == 80
            assert config.dgx_spark.batch_size == 30
            assert len(config.speakers) == 1
            assert config.speakers[0].name == "홍길동"
            assert config.analysis_period is not None

        finally:
            temp_path.unlink(missing_ok=True)

    def test_load_empty_yaml_returns_default(self) -> None:
        """빈 YAML 파일 로드 시 기본값 반환을 검증합니다."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            temp_path = Path(f.name)

        try:
            loader = ConfigLoader(temp_path)
            config = loader.load()

            assert isinstance(config, ForensicConfig)
            assert config.version == "0.1.0"
        finally:
            temp_path.unlink(missing_ok=True)

    def test_find_config_path(self) -> None:
        """설정 파일 찾기를 검증합니다."""
        # 임시 디렉터리에 파일 생성
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # 파일 없음
            loader = ConfigLoader()
            with patch.object(ConfigLoader, "DEFAULT_CONFIG_PATHS", [tmpdir_path / "config.yaml"]):
                result = loader.find_config_path()
                assert result is None

            # 파일 있음
            config_file = tmpdir_path / "forensic.yaml"
            config_file.touch()

            with patch.object(ConfigLoader, "DEFAULT_CONFIG_PATHS", [config_file]):
                result = loader.find_config_path()
                assert result == config_file

    def test_reload(self) -> None:
        """설정 재로드를 검증합니다."""
        loader = ConfigLoader()
        # config1 = loader.load()

        # 설정 수정 (실제로는 파일이 변경되지 않으므로 동일한 객체)
        config2 = loader.reload()

        assert isinstance(config2, ForensicConfig)

    def test_get_dot_notation(self) -> None:
        """점 표기법으로 값 가져오기를 검증합니다."""
        loader = ConfigLoader()
        loader.load()

        # dgx_spark.enabled
        enabled = loader.get("dgx_spark.enabled")
        assert enabled is True

        # 존재하지 않는 키
        missing = loader.get("missing.key", default="default_value")
        assert missing == "default_value"

    def test_load_top_level_config(self) -> None:
        """최상위 수준 설정 로드를 검증합니다."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""version: "0.2.0"
dgx_spark:
  enabled: false
""")
            temp_path = Path(f.name)

        try:
            loader = ConfigLoader(temp_path)
            config = loader.load()

            assert config.version == "0.2.0"
            assert config.dgx_spark.enabled is False
        finally:
            temp_path.unlink(missing_ok=True)


class TestModuleFunctions:
    """모듈 수준 함수 테스트"""

    @patch("forensic.utils.config._global_loader", None)
    @patch("forensic.utils.config.ConfigLoader")
    def test_get_config_loader_creates_instance(self, mock_loader_class: Mock) -> None:
        """get_config_loader가 인스턴스를 생성하는지 검증합니다."""
        mock_instance = MagicMock()
        mock_loader_class.return_value = mock_instance

        loader = get_config_loader()
        assert loader is not None

    @patch("forensic.utils.config.get_config_loader")
    def test_load_config_delegates_to_loader(self, mock_get_loader: Mock) -> None:
        """load_config가 로더에 위임하는지 검증합니다."""
        mock_loader = MagicMock()
        mock_config = ForensicConfig()
        mock_loader.load.return_value = mock_config
        mock_get_loader.return_value = mock_loader

        config = load_config(Path("/test/config.yaml"))

        assert config is not None
        mock_loader.load.assert_called_once()

    @patch("forensic.utils.config.get_config_loader")
    def test_get_config_returns_cached(self, mock_get_loader: Mock) -> None:
        """get_config가 캐시된 설정을 반환하는지 검증합니다."""
        mock_loader = MagicMock()
        mock_config = ForensicConfig()
        mock_loader.config = mock_config
        mock_get_loader.return_value = mock_loader

        config = get_config()
        assert config is mock_config
