"""
DGX Spark 환경 감지 유틸리티

NVIDIA DGX Spark 시스템의 특성을 감지하고 최적화 설정을 제공합니다.
- ARM64 아키텍처 감지
- CUDA 가용성 확인
- 메모리 용량 측정
- GPU 정보 수집
"""

import platform
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class DGXSparkInfo:
    """
    DGX Spark 시스템 정보

    Attributes:
        is_dgx_spark: DGX Spark 시스템 여부
        is_arm64: ARM64 아키텍처 여부
        cuda_available: CUDA 사용 가능 여부
        memory_gb: 시스템 메모리 (GB)
        gpu_name: GPU 이름 (감지된 경우)
    """

    is_dgx_spark: bool
    is_arm64: bool
    cuda_available: bool
    memory_gb: float
    gpu_name: str | None = None

    @property
    def is_optimized(self) -> bool:
        """DGX Spark 최적화 가능한 환경인지 확인합니다."""
        return self.is_dgx_spark or (self.is_arm64 and self.cuda_available)

    @property
    def can_use_gpu(self) -> bool:
        """GPU 가속을 사용할 수 있는지 확인합니다."""
        return self.cuda_available

    def has_sufficient_memory(self, required_gb: float = 64) -> bool:
        """
        충분한 메모리를 가지고 있는지 확인합니다.

        Args:
            required_gb: 필요한 메모리 (GB)

        Returns:
            충분한 메모리가 있으면 True
        """
        return self.memory_gb >= required_gb


class DGXSparkDetector:
    """
    DGX Spark 환경 감지기

    시스템의 하드웨어 및 소프트웨어 구성을 감지하여
    DGX Spark 최적화 가능 여부를 판단합니다.
    """

    # DGX Spark 특정 식별자
    DGX_SPARK_IDENTIFIERS = ["DGX Spark", "DGX-Spark", "dgx-spark"]

    def detect(self) -> DGXSparkInfo:
        """
        시스템 환경을 감지합니다.

        Returns:
            DGXSparkInfo: 감지된 시스템 정보
        """
        return DGXSparkInfo(
            is_dgx_spark=self._check_dgx_spark(),
            is_arm64=self._check_arm64(),
            cuda_available=self._check_cuda(),
            memory_gb=self._get_memory_gb(),
            gpu_name=self._get_gpu_name(),
        )

    def _check_arm64(self) -> bool:
        """
        ARM64 아키텍처인지 확인합니다.

        Returns:
            ARM64이면 True
        """
        machine = platform.machine().lower()
        return machine in ("aarch64", "arm64")

    def _check_dgx_spark(self) -> bool:
        """
        DGX Spark 시스템인지 확인합니다.

        Returns:
            DGX Spark이면 True
        """
        # 시스템 정보 확인
        try:
            # macOS: system_profiler
            if platform.system() == "Darwin":
                result = subprocess.run(
                    ["sysctl", "-n", "machdep.cpu.brand_string"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    cpu_brand = result.stdout.strip()
                    return any(
                        identifier.lower() in cpu_brand.lower()
                        for identifier in self.DGX_SPARK_IDENTIFIERS
                    )
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        # Linux: dmi Product Name
        try:
            if platform.system() == "Linux":
                result = subprocess.run(
                    ["cat", "/sys/class/dmi/id/product_name"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    product_name = result.stdout.strip()
                    return any(
                        identifier.lower() in product_name.lower()
                        for identifier in self.DGX_SPARK_IDENTIFIERS
                    )
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        # 환경 변수 확인
        import os

        return any(os.environ.get(key) for key in ["DGX_SPARK", "DGXSPARK"])

    def _check_cuda(self) -> bool:
        """
        CUDA 사용 가능 여부를 확인합니다.

        Returns:
            CUDA 사용 가능하면 True
        """
        try:
            import torch

            return torch.cuda.is_available()
        except Exception:
            return False

    def _get_memory_gb(self) -> float:
        """
        시스템 메모리 용량을 GB 단위로 반환합니다.

        Returns:
            메모리 용량 (GB)
        """
        try:
            import psutil

            return psutil.virtual_memory().total / (1024**3)
        except Exception:
            # 플랫폼별 기본값 반환
            system = platform.system()
            if system == "Darwin":
                # macOS: sysctl
                try:
                    result = subprocess.run(
                        ["sysctl", "-n", "hw.memsize"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        return int(result.stdout.strip()) / (1024**3)
                except (subprocess.SubprocessError, FileNotFoundError, ValueError):
                    pass
            elif system == "Linux":
                # Linux: meminfo
                try:
                    with open("/proc/meminfo") as f:
                        for line in f:
                            if line.startswith("MemTotal:"):
                                kb = int(line.split()[1])
                                return kb / (1024**2)
                except (OSError, ValueError, IndexError):
                    pass

            return 0.0

    def _get_gpu_name(self) -> str | None:
        """
        GPU 이름을 반환합니다.

        Returns:
            GPU 이름 또는 None
        """
        try:
            import torch

            if torch.cuda.is_available():
                return torch.cuda.get_device_name(0)
        except Exception:
            pass

        # nvidia-smi 시도
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        return None


# 전역 감지기 인스턴스
_detector: DGXSparkDetector | None = None
_cached_info: DGXSparkInfo | None = None


def get_detector() -> DGXSparkDetector:
    """전역 감지기 인스턴스를 반환합니다."""
    global _detector
    if _detector is None:
        _detector = DGXSparkDetector()
    return _detector


def detect_dgx_spark() -> DGXSparkInfo:
    """
    시스템 환경을 감지하고 결과를 캐시합니다.

    Returns:
        DGXSparkInfo: 감지된 시스템 정보
    """
    global _cached_info
    if _cached_info is None:
        detector = get_detector()
        _cached_info = detector.detect()
    return _cached_info


def clear_detection_cache() -> None:
    """감지 캐시를 초기화합니다."""
    global _cached_info
    _cached_info = None
