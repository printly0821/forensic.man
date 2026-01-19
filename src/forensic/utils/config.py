"""
forensic.man 설정 관리 시스템

YAML 기반 설정 파일 로딩 및 관리를 제공합니다.
DGX Spark 최적화 설정, 화자 설정, 분석 기간 등을 포함합니다.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


class DGXSparkConfig(BaseModel):
    """
    DGX Spark 최적화 설정

    Attributes:
        enabled: DGX Spark 최적화 사용 여부
        auto_detect: 자동 환경 감지 여부
        gpu_acceleration: GPU 가속 사용 여부
        memory_limit_gb: 메모리 제한 (GB)
        batch_size: 배치 처리 크기
    """

    enabled: bool = True
    auto_detect: bool = True
    gpu_acceleration: bool = True
    memory_limit_gb: int = Field(ge=1, le=128, default=100)
    batch_size: int = Field(ge=1, le=1000, default=50)

    @field_validator("memory_limit_gb")
    @classmethod
    def validate_memory_limit(cls, v: int) -> int:
        """메모리 제한이 시스템 메모리를 초과하지 않도록 검증합니다."""
# 런타임에 시스템 메모리를 확인할 수 있도록 함
        return v

    def get_effective_memory_limit(self, system_memory_gb: float) -> int:
        """
        시스템 메모리를 고려한 실제 메모리 제한을 반환합니다.

        Args:
            system_memory_gb: 시스템 전체 메모리 (GB)

        Returns:
            실제 메모리 제한 (GB)
        """
        return min(self.memory_limit_gb, int(system_memory_gb * 0.9))


class SpeakerConfig(BaseModel):
    """
    화자 설정

    Attributes:
        id: 화자 고유 ID
        name: 화자 표준 이름
        aliases: 화자 별칭 목록
    """

    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)

    def matches(self, name: str) -> bool:
        """
        주어진 이름이 이 화자와 일치하는지 확인합니다.

        Args:
            name: 확인할 이름

        Returns:
            일치하면 True
        """
        return name == self.name or name in self.aliases


class AnalysisPeriod(BaseModel):
    """
    분석 기간 설정

    Attributes:
        start: 시작 날짜 (YYYY-MM-DD 형식)
        end: 종료 날짜 (YYYY-MM-DD 형식)
    """

    start: str
    end: str

    @field_validator("start", "end")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """날짜 형식을 검증합니다."""
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(
                f"Invalid date format '{v}'. Expected YYYY-MM-DD format."
            ) from e
        return v

    @property
    def start_date(self) -> datetime:
        """시작 날짜를 datetime 객체로 반환합니다."""
        return datetime.strptime(self.start, "%Y-%m-%d")

    @property
    def end_date(self) -> datetime:
        """종료 날짜를 datetime 객체로 반환합니다."""
        return datetime.strptime(self.end, "%Y-%m-%d")

    def contains(self, date: datetime) -> bool:
        """
        주어진 날짜가 분석 기간 내에 있는지 확인합니다.

        Args:
            date: 확인할 날짜

        Returns:
            기간 내에 있으면 True
        """
        return self.start_date <= date <= self.end_date


class ForensicConfig(BaseModel):
    """
    forensic.man 기본 설정

    Attributes:
        version: 설정 버전
        dgx_spark: DGX Spark 최적화 설정
        speakers: 화자 설정 목록
        analysis_period: 분석 기간 (선택)
    """

    version: str = "0.1.0"
    dgx_spark: DGXSparkConfig = Field(default_factory=DGXSparkConfig)
    speakers: list[SpeakerConfig] = Field(default_factory=list)
    analysis_period: AnalysisPeriod | None = None

    def get_speaker_by_id(self, speaker_id: str) -> SpeakerConfig | None:
        """
        ID로 화자 설정을 찾습니다.

        Args:
            speaker_id: 화자 ID

        Returns:
            일치하는 화자 설정 또는 None
        """
        for speaker in self.speakers:
            if speaker.id == speaker_id:
                return speaker
        return None

    def get_speaker_by_name(self, name: str) -> SpeakerConfig | None:
        """
        이름으로 화자 설정을 찾습니다.

        Args:
            name: 화자 이름 또는 별칭

        Returns:
            일치하는 화자 설정 또는 None
        """
        for speaker in self.speakers:
            if speaker.matches(name):
                return speaker
        return None

    def add_speaker(self, speaker: SpeakerConfig) -> None:
        """
        화자 설정을 추가합니다.

        Args:
            speaker: 추가할 화자 설정
        """
        # 중복 확인
        if self.get_speaker_by_id(speaker.id) is None:
            self.speakers.append(speaker)

    def should_use_gpu(self, cuda_available: bool) -> bool:
        """
        GPU를 사용해야 하는지 확인합니다.

        Args:
            cuda_available: CUDA 사용 가능 여부

        Returns:
            GPU 사용이 적절하면 True
        """
        return self.dgx_spark.enabled and self.dgx_spark.gpu_acceleration and cuda_available

    def should_auto_detect(self) -> bool:
        """자동 환경 감지를 사용해야 하는지 확인합니다."""
        return self.dgx_spark.enabled and self.dgx_spark.auto_detect


class ConfigLoader:
    """
    설정 로더

    YAML 파일에서 설정을 로드하고 관리합니다.
    """

    DEFAULT_CONFIG_PATHS = [
        Path("forensic.yaml"),
        Path("forensic.yml"),
        Path("config/forensic.yaml"),
        Path("config/forensic.yml"),
        Path(".forensic.yaml"),
        Path(".forensic.yml"),
    ]

    def __init__(self, config_path: Path | None = None):
        """
        설정 로더를 초기화합니다.

        Args:
            config_path: 설정 파일 경로 (None인 경우 기본 경로 검색)
        """
        self.config_path = config_path
        self._config: ForensicConfig | None = None

    def find_config_path(self) -> Path | None:
        """
        기본 경로에서 설정 파일을 찾습니다.

        Returns:
            찾은 설정 파일 경로 또는 None
        """
        for path in self.DEFAULT_CONFIG_PATHS:
            if path.exists():
                return path
        return None

    def load(self, path: Path | None = None) -> ForensicConfig:
        """
        설정 파일을 로드합니다.

        Args:
            path: 설정 파일 경로 (None인 경우 초기화 시 경로 사용)

        Returns:
            로드된 설정
        """
        load_path = path or self.config_path or self.find_config_path()

        if load_path is None or not load_path.exists():
            # 기본 설정 반환
            self._config = ForensicConfig()
            return self._config

        try:
            import yaml

            with open(load_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            # forensic 섹션 추출 (최상위 수준 지원)
            if "forensic" in data:
                data = data["forensic"]

            self._config = self._parse_config(data)
            return self._config

        except ImportError:
            # YAML 모듈이 없는 경우 기본 설정 반환
            self._config = ForensicConfig()
            return self._config
        except Exception:
            # 파싱 오류 시 기본 설정 반환
            self._config = ForensicConfig()
            return self._config

    def _parse_config(self, data: dict[str, Any]) -> ForensicConfig:
        """
        설정 데이터를 파싱합니다.

        Args:
            data: YAML에서 로드된 데이터

        Returns:
            파싱된 설정
        """
        # DGX Spark 설정 파싱
        dgx_spark_data = data.get("dgx_spark", {})
        dgx_spark = DGXSparkConfig(**dgx_spark_data) if dgx_spark_data else DGXSparkConfig()

        # 화자 설정 파싱
        speakers_data = data.get("speakers", [])
        speakers = [SpeakerConfig(**s) for s in speakers_data] if speakers_data else []

        # 분석 기간 파싱
        analysis_period = None
        if "analysis_period" in data:
            period_data = data["analysis_period"]
            if period_data:
                analysis_period = AnalysisPeriod(**period_data)

        return ForensicConfig(
            version=data.get("version", "0.1.0"),
            dgx_spark=dgx_spark,
            speakers=speakers,
            analysis_period=analysis_period,
        )

    def reload(self) -> ForensicConfig:
        """
        설정을 다시 로드합니다.

        Returns:
            다시 로드된 설정
        """
        self._config = None
        return self.load()

    def get(self, key: str, default: Any = None) -> Any:
        """
        설정 값을 가져옵니다.

        Args:
            key: 설정 키 (점 표기법 지원: 'dgx_spark.enabled')
            default: 기본값

        Returns:
            설정 값 또는 기본값
        """
        if self._config is None:
            self.load()

        keys = key.split(".")
        value = self._config

        for k in keys:
            if hasattr(value, k):
                value = getattr(value, k)
            else:
                return default

        return value

    @property
    def config(self) -> ForensicConfig:
        """현재 로드된 설정을 반환합니다."""
        if self._config is None:
            self.load()
        return self._config


# 전역 설정 로더 인스턴스
_global_loader: ConfigLoader | None = None


def get_config_loader(config_path: Path | None = None) -> ConfigLoader:
    """
    전역 설정 로더를 반환합니다.

    Args:
        config_path: 설정 파일 경로

    Returns:
        설정 로더 인스턴스
    """
    global _global_loader
    if _global_loader is None or config_path is not None:
        _global_loader = ConfigLoader(config_path)
    return _global_loader


def load_config(path: Path | None = None) -> ForensicConfig:
    """
    설정을 로드합니다.

    Args:
        path: 설정 파일 경로

    Returns:
        로드된 설정
    """
    return get_config_loader(path).load()


def get_config() -> ForensicConfig:
    """
    현재 로드된 설정을 반환합니다.

    Returns:
        현재 설정
    """
    return get_config_loader().config
