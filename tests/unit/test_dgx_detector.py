"""
DGX Spark 환경 감지 유틸리티 단위 테스트

DGXSparkDetector, DGXSparkInfo 클래스의 동작을 검증합니다.
"""

import os as os_module
import platform
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

from forensic.utils.dgx_detector import (
    DGXSparkDetector,
    DGXSparkInfo,
    clear_detection_cache,
    detect_dgx_spark,
    get_detector,
)


class TestDGXSparkInfo:
    """DGXSparkInfo 데이터클래스 테스트"""

    def test_create_dgx_spark_info(self) -> None:
        """DGXSparkInfo 생성을 검증합니다."""
        info = DGXSparkInfo(
            is_dgx_spark=True,
            is_arm64=True,
            cuda_available=True,
            memory_gb=128.0,
            gpu_name="Blackwell",
        )

        assert info.is_dgx_spark is True
        assert info.is_arm64 is True
        assert info.cuda_available is True
        assert info.memory_gb == 128.0
        assert info.gpu_name == "Blackwell"

    def test_is_optimized_property(self) -> None:
        """is_optimized 속성을 검증합니다."""
        # DGX Spark인 경우
        dgx_info = DGXSparkInfo(
            is_dgx_spark=True,
            is_arm64=True,
            cuda_available=True,
            memory_gb=128.0,
        )
        assert dgx_info.is_optimized is True

        # DGX Spark는 아니지만 ARM64 + CUDA인 경우
        arm64_cuda_info = DGXSparkInfo(
            is_dgx_spark=False,
            is_arm64=True,
            cuda_available=True,
            memory_gb=64.0,
        )
        assert arm64_cuda_info.is_optimized is True

        # ARM64지만 CUDA가 없는 경우
        arm64_only_info = DGXSparkInfo(
            is_dgx_spark=False,
            is_arm64=True,
            cuda_available=False,
            memory_gb=64.0,
        )
        assert arm64_only_info.is_optimized is False

        # x86_64인 경우
        x64_info = DGXSparkInfo(
            is_dgx_spark=False,
            is_arm64=False,
            cuda_available=True,
            memory_gb=64.0,
        )
        assert x64_info.is_optimized is False

    def test_can_use_gpu_property(self) -> None:
        """can_use_gpu 속성을 검증합니다."""
        # CUDA 가능
        cuda_info = DGXSparkInfo(
            is_dgx_spark=False,
            is_arm64=True,
            cuda_available=True,
            memory_gb=64.0,
        )
        assert cuda_info.can_use_gpu is True

        # CUDA 불가능
        no_cuda_info = DGXSparkInfo(
            is_dgx_spark=False,
            is_arm64=True,
            cuda_available=False,
            memory_gb=64.0,
        )
        assert no_cuda_info.can_use_gpu is False

    def test_has_sufficient_memory_property(self) -> None:
        """has_sufficient_memory 속성을 검증합니다."""
        info = DGXSparkInfo(
            is_dgx_spark=False,
            is_arm64=True,
            cuda_available=True,
            memory_gb=128.0,
        )

        assert info.has_sufficient_memory(64) is True
        assert info.has_sufficient_memory(128) is True
        assert info.has_sufficient_memory(200) is False

    def test_optional_gpu_name(self) -> None:
        """선택적 gpu_name을 검증합니다."""
        info_with_gpu = DGXSparkInfo(
            is_dgx_spark=False,
            is_arm64=True,
            cuda_available=True,
            memory_gb=64.0,
            gpu_name="RTX 4090",
        )
        assert info_with_gpu.gpu_name == "RTX 4090"

        info_without_gpu = DGXSparkInfo(
            is_dgx_spark=False,
            is_arm64=True,
            cuda_available=False,
            memory_gb=64.0,
        )
        assert info_without_gpu.gpu_name is None


class TestDGXSparkDetector:
    """DGXSparkDetector 클래스 테스트"""

    def test_detect_returns_dgx_spark_info(self) -> None:
        """detect 메서드가 DGXSparkInfo를 반환하는지 검증합니다."""
        detector = DGXSparkDetector()
        info = detector.detect()

        assert isinstance(info, DGXSparkInfo)
        assert hasattr(info, "is_dgx_spark")
        assert hasattr(info, "is_arm64")
        assert hasattr(info, "cuda_available")
        assert hasattr(info, "memory_gb")

    def test_check_arm64_true(self) -> None:
        """ARM64 아키텍처 감지를 검증합니다."""
        detector = DGXSparkDetector()

        with patch.object(platform, "machine", return_value="aarch64"):
            assert detector._check_arm64() is True

        with patch.object(platform, "machine", return_value="arm64"):
            assert detector._check_arm64() is True

    def test_check_arm64_false(self) -> None:
        """ARM64가 아닌 아키텍처 감지를 검증합니다."""
        detector = DGXSparkDetector()

        with patch.object(platform, "machine", return_value="x86_64"):
            assert detector._check_arm64() is False

        with patch.object(platform, "machine", return_value="AMD64"):
            assert detector._check_arm64() is False

    def test_check_cuda_available_with_mock(self) -> None:
        """sys.modules를 사용한 CUDA 사용 가능 감지 테스트."""
        # Mock torch 모듈 생성
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True

        # sys.modules에 mock 추가
        sys.modules["torch"] = mock_torch

        try:
            # 모듈 재로드를 통해 mock 적용
            import importlib

            import forensic.utils.dgx_detector
            importlib.reload(forensic.utils.dgx_detector)

            from forensic.utils.dgx_detector import DGXSparkDetector
            detector = DGXSparkDetector()
            result = detector._check_cuda()
            assert result is True
        finally:
            # mock 제거
            sys.modules.pop("torch", None)
            # 원래 모듈 복구
            import importlib

            import forensic.utils.dgx_detector
            importlib.reload(forensic.utils.dgx_detector)

    def test_check_cuda_not_available(self) -> None:
        """torch가 없을 때 CUDA 사용 불가 감지를 검증합니다."""
        # torch가 sys.modules에 없는 상황 시뮬레이션
        torch_backup = sys.modules.get("torch")
        sys.modules["torch"] = None

        try:
            import importlib

            import forensic.utils.dgx_detector
            importlib.reload(forensic.utils.dgx_detector)

            from forensic.utils.dgx_detector import DGXSparkDetector
            detector = DGXSparkDetector()
            result = detector._check_cuda()
            assert result is False
        finally:
            if torch_backup is not None:
                sys.modules["torch"] = torch_backup
            else:
                sys.modules.pop("torch", None)
            import importlib

            import forensic.utils.dgx_detector
            importlib.reload(forensic.utils.dgx_detector)

    def test_get_memory_gb_with_psutil(self) -> None:
        """psutil을 통한 메모리 감지를 검증합니다."""
        # Mock psutil 모듈 생성
        mock_psutil = MagicMock()
        mock_memory = MagicMock()
        mock_memory.total = 128 * (1024**3)
        mock_psutil.virtual_memory.return_value = mock_memory

        # sys.modules에 mock 추가
        sys.modules["psutil"] = mock_psutil

        try:
            import importlib

            import forensic.utils.dgx_detector
            importlib.reload(forensic.utils.dgx_detector)

            from forensic.utils.dgx_detector import DGXSparkDetector
            detector = DGXSparkDetector()
            memory = detector._get_memory_gb()
            assert memory == pytest.approx(128.0, rel=0.01)
        finally:
            sys.modules.pop("psutil", None)
            import importlib

            import forensic.utils.dgx_detector
            importlib.reload(forensic.utils.dgx_detector)

    @patch("forensic.utils.dgx_detector.subprocess.run")
    def test_get_memory_gb_fallback(self, mock_run: Mock) -> None:
        """psutil 없을 때 메모리 감지 fallback을 검증합니다."""
        psutil_backup = sys.modules.get("psutil")
        sys.modules["psutil"] = None

        try:
            import importlib

            import forensic.utils.dgx_detector
            importlib.reload(forensic.utils.dgx_detector)

            # Mock subprocess to prevent sysctl fallback
            mock_run.return_value = MagicMock(returncode=1)

            from forensic.utils.dgx_detector import DGXSparkDetector
            detector = DGXSparkDetector()
            memory = detector._get_memory_gb()
            # fallback은 0.0을 반환
            assert memory == 0.0
        finally:
            if psutil_backup is not None:
                sys.modules["psutil"] = psutil_backup
            else:
                sys.modules.pop("psutil", None)
            import importlib

            import forensic.utils.dgx_detector
            importlib.reload(forensic.utils.dgx_detector)

    @patch("forensic.utils.dgx_detector.subprocess.run")
    @patch("forensic.utils.dgx_detector.platform")
    def test_check_dgx_spark_macos_positive(
        self, mock_platform: Mock, mock_run: Mock
    ) -> None:
        """macOS에서 DGX Spark 감지를 검증합니다."""
        detector = DGXSparkDetector()

        mock_platform.system.return_value = "Darwin"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout.strip.return_value = "NVIDIA DGX Spark"
        mock_run.return_value = mock_result

        result = detector._check_dgx_spark()
        assert result is True

    @patch("forensic.utils.dgx_detector.subprocess.run")
    @patch("forensic.utils.dgx_detector.platform")
    def test_check_dgx_spark_linux_positive(
        self, mock_platform: Mock, mock_run: Mock
    ) -> None:
        """Linux에서 DGX Spark 감지를 검증합니다."""
        detector = DGXSparkDetector()

        mock_platform.system.return_value = "Linux"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout.strip.return_value = "DGX Spark"
        mock_run.return_value = mock_result

        result = detector._check_dgx_spark()
        assert result is True

    @patch("forensic.utils.dgx_detector.subprocess.run")
    @patch("forensic.utils.dgx_detector.platform")
    def test_check_dgx_spark_env_variable(self, mock_platform: Mock, mock_run: Mock) -> None:
        """환경 변수를 통한 DGX Spark 감지를 검증합니다."""
        # 환경 변수 설정 및 테스트
        old_env = os_module.environ.get("DGX_SPARK")
        os_module.environ["DGX_SPARK"] = "1"

        try:
            # Platform-specific checks fail
            mock_platform.system.return_value = "Darwin"
            mock_result = MagicMock()
            mock_result.returncode = 1  # Command fails
            mock_run.return_value = mock_result

            from forensic.utils.dgx_detector import DGXSparkDetector
            detector = DGXSparkDetector()
            result = detector._check_dgx_spark()
            assert result is True
        finally:
            if old_env is None:
                os_module.environ.pop("DGX_SPARK", None)
            else:
                os_module.environ["DGX_SPARK"] = old_env

    @patch("forensic.utils.dgx_detector.subprocess.run")
    @patch("forensic.utils.dgx_detector.platform")
    def test_check_dgx_spark_negative(
        self, mock_platform: Mock, mock_run: Mock
    ) -> None:
        """DGX Spark가 아닌 시스템 감지를 검증합니다."""
        detector = DGXSparkDetector()

        mock_platform.system.return_value = "Darwin"
        mock_result = MagicMock()
        mock_result.returncode = 1  # Command failed
        mock_run.return_value = mock_result

        result = detector._check_dgx_spark()
        assert result is False

    def test_get_gpu_name_with_torch(self) -> None:
        """PyTorch를 통한 GPU 이름 감지를 검증합니다."""
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.get_device_name.return_value = "Blackwell GPU"

        sys.modules["torch"] = mock_torch

        try:
            import importlib

            import forensic.utils.dgx_detector
            importlib.reload(forensic.utils.dgx_detector)

            from forensic.utils.dgx_detector import DGXSparkDetector
            detector = DGXSparkDetector()
            gpu_name = detector._get_gpu_name()
            assert gpu_name == "Blackwell GPU"
        finally:
            sys.modules.pop("torch", None)
            import importlib

            import forensic.utils.dgx_detector
            importlib.reload(forensic.utils.dgx_detector)

    @patch("forensic.utils.dgx_detector.subprocess.run")
    def test_get_gpu_name_with_nvidia_smi(self, mock_run: Mock) -> None:
        """nvidia-smi를 통한 GPU 이름 감지를 검증합니다."""
        # torch 없는 상황 시뮬레이션
        torch_backup = sys.modules.get("torch")
        sys.modules["torch"] = None

        try:
            import importlib

            import forensic.utils.dgx_detector
            importlib.reload(forensic.utils.dgx_detector)

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout.strip.return_value = "NVIDIA Blackwell"
            mock_run.return_value = mock_result

            from forensic.utils.dgx_detector import DGXSparkDetector
            detector = DGXSparkDetector()
            gpu_name = detector._get_gpu_name()
            assert gpu_name == "NVIDIA Blackwell"
        finally:
            if torch_backup is not None:
                sys.modules["torch"] = torch_backup
            else:
                sys.modules.pop("torch", None)
            import importlib

            import forensic.utils.dgx_detector
            importlib.reload(forensic.utils.dgx_detector)

    @patch("forensic.utils.dgx_detector.subprocess.run")
    def test_get_gpu_name_none(self, mock_run: Mock) -> None:
        """GPU를 찾을 수 없을 때를 검증합니다."""
        torch_backup = sys.modules.get("torch")
        sys.modules["torch"] = None

        try:
            import importlib

            import forensic.utils.dgx_detector
            importlib.reload(forensic.utils.dgx_detector)

            mock_result = MagicMock()
            mock_result.returncode = 1  # nvidia-smi failed
            mock_run.return_value = mock_result

            from forensic.utils.dgx_detector import DGXSparkDetector
            detector = DGXSparkDetector()
            gpu_name = detector._get_gpu_name()
            assert gpu_name is None
        finally:
            if torch_backup is not None:
                sys.modules["torch"] = torch_backup
            else:
                sys.modules.pop("torch", None)
            import importlib

            import forensic.utils.dgx_detector
            importlib.reload(forensic.utils.dgx_detector)


class TestModuleFunctions:
    """모듈 수준 함수 테스트"""

    def test_get_detector_returns_singleton(self) -> None:
        """get_detector가 싱글톤을 반환하는지 검증합니다."""
        # 캐시 초기화
        clear_detection_cache()

        detector1 = get_detector()
        detector2 = get_detector()

        assert detector1 is detector2

    def test_detect_dgx_spark_returns_info(self) -> None:
        """detect_dgx_spark가 DGXSparkInfo를 반환하는지 검증합니다."""
        clear_detection_cache()
        info = detect_dgx_spark()
        # Check attributes instead of isinstance to avoid reload issues
        assert hasattr(info, "is_dgx_spark")
        assert hasattr(info, "is_arm64")
        assert hasattr(info, "cuda_available")
        assert hasattr(info, "memory_gb")

    def test_clear_detection_cache(self) -> None:
        """캐시 초기화를 검증합니다."""
        # 첫 번째 감지
        info1 = detect_dgx_spark()

        # 캐시 초기화
        clear_detection_cache()

        # 두 번째 감지
        info2 = detect_dgx_spark()

        # 두 결과 모두 필요한 속성을 가져야 함
        assert hasattr(info1, "is_dgx_spark")
        assert hasattr(info2, "is_dgx_spark")
