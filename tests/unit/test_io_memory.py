"""
Memory monitoring module unit tests.

Tests for MemoryMonitor class and related functions.
"""

from unittest.mock import MagicMock, patch

import pytest

from forensic.io.memory import (
    CRITICAL_BATCH_SIZE,
    CRITICAL_CHUNK_SIZE,
    DEFAULT_BATCH_SIZE,
    DEFAULT_CHUNK_SIZE,
    DGX_SPARK_BATCH_SIZE,
    DGX_SPARK_CHUNK_SIZE,
    MEMORY_CRITICAL_THRESHOLD_GB,
    MEMORY_WARNING_THRESHOLD_GB,
    WARNING_BATCH_SIZE,
    WARNING_CHUNK_SIZE,
    MemoryMonitor,
    MemoryState,
    clear_memory_monitor,
    get_memory_monitor,
)
from forensic.utils.dgx_detector import DGXSparkInfo


class TestMemoryState:
    """MemoryState dataclass tests."""

    def test_create_memory_state(self) -> None:
        """Test MemoryState creation."""
        state = MemoryState(
            usage_gb=50.0,
            available_gb=78.0,
            total_gb=128.0,
            level="normal",
        )

        assert state.usage_gb == 50.0
        assert state.available_gb == 78.0
        assert state.total_gb == 128.0
        assert state.level == "normal"


class TestMemoryMonitor:
    """MemoryMonitor class tests."""

    @pytest.fixture
    def dgx_spark_info(self) -> DGXSparkInfo:
        """Create DGX Spark info fixture."""
        return DGXSparkInfo(
            is_dgx_spark=True,
            is_arm64=True,
            cuda_available=True,
            memory_gb=128.0,
            gpu_name="Blackwell",
        )

    @pytest.fixture
    def regular_system_info(self) -> DGXSparkInfo:
        """Create regular system info fixture."""
        return DGXSparkInfo(
            is_dgx_spark=False,
            is_arm64=False,
            cuda_available=False,
            memory_gb=16.0,
            gpu_name=None,
        )

    def test_init_with_dgx_info(self, dgx_spark_info: DGXSparkInfo) -> None:
        """Test initialization with provided DGX info."""
        monitor = MemoryMonitor(dgx_info=dgx_spark_info)

        assert monitor.dgx_info is dgx_spark_info
        assert monitor.dgx_info.is_dgx_spark is True

    def test_init_without_dgx_info(self) -> None:
        """Test initialization with auto-detection."""
        monitor = MemoryMonitor()

        assert monitor.dgx_info is not None
        assert hasattr(monitor.dgx_info, "is_dgx_spark")

    @patch("forensic.io.memory.psutil.virtual_memory")
    def test_get_usage_gb(self, mock_memory: MagicMock) -> None:
        """Test get_usage_gb returns correct value."""
        mock_memory.return_value = MagicMock(used=50 * (1024**3))
        monitor = MemoryMonitor()

        usage = monitor.get_usage_gb()

        assert usage == pytest.approx(50.0, rel=0.01)

    @patch("forensic.io.memory.psutil.virtual_memory")
    def test_get_available_gb(self, mock_memory: MagicMock) -> None:
        """Test get_available_gb returns correct value."""
        mock_memory.return_value = MagicMock(available=78 * (1024**3))
        monitor = MemoryMonitor()

        available = monitor.get_available_gb()

        assert available == pytest.approx(78.0, rel=0.01)

    @patch("forensic.io.memory.psutil.virtual_memory")
    def test_get_total_gb(self, mock_memory: MagicMock) -> None:
        """Test get_total_gb returns correct value."""
        mock_memory.return_value = MagicMock(total=128 * (1024**3))
        monitor = MemoryMonitor()

        total = monitor.get_total_gb()

        assert total == pytest.approx(128.0, rel=0.01)

    @patch("forensic.io.memory.psutil.virtual_memory")
    def test_get_memory_state_normal(self, mock_memory: MagicMock) -> None:
        """Test get_memory_state returns normal level."""
        mock_memory.return_value = MagicMock(
            used=50 * (1024**3),
            available=78 * (1024**3),
            total=128 * (1024**3),
        )
        monitor = MemoryMonitor()

        state = monitor.get_memory_state()

        assert state.level == "normal"
        assert state.usage_gb == pytest.approx(50.0, rel=0.01)

    @patch("forensic.io.memory.psutil.virtual_memory")
    def test_get_memory_state_warning(self, mock_memory: MagicMock) -> None:
        """Test get_memory_state returns warning level."""
        mock_memory.return_value = MagicMock(
            used=85 * (1024**3),
            available=43 * (1024**3),
            total=128 * (1024**3),
        )
        monitor = MemoryMonitor()

        state = monitor.get_memory_state()

        assert state.level == "warning"
        assert state.usage_gb > MEMORY_WARNING_THRESHOLD_GB

    @patch("forensic.io.memory.psutil.virtual_memory")
    def test_get_memory_state_critical(self, mock_memory: MagicMock) -> None:
        """Test get_memory_state returns critical level."""
        mock_memory.return_value = MagicMock(
            used=105 * (1024**3),
            available=23 * (1024**3),
            total=128 * (1024**3),
        )
        monitor = MemoryMonitor()

        state = monitor.get_memory_state()

        assert state.level == "critical"
        assert state.usage_gb > MEMORY_CRITICAL_THRESHOLD_GB

    @patch("forensic.io.memory.psutil.virtual_memory")
    def test_should_reduce_chunk_size_false(self, mock_memory: MagicMock) -> None:
        """Test should_reduce_chunk_size returns False when usage < 80GB."""
        mock_memory.return_value = MagicMock(used=50 * (1024**3))
        monitor = MemoryMonitor()

        assert monitor.should_reduce_chunk_size() is False

    @patch("forensic.io.memory.psutil.virtual_memory")
    def test_should_reduce_chunk_size_true(self, mock_memory: MagicMock) -> None:
        """Test should_reduce_chunk_size returns True when usage > 80GB."""
        mock_memory.return_value = MagicMock(used=85 * (1024**3))
        monitor = MemoryMonitor()

        assert monitor.should_reduce_chunk_size() is True

    @patch("forensic.io.memory.psutil.virtual_memory")
    def test_should_force_gc_false(self, mock_memory: MagicMock) -> None:
        """Test should_force_gc returns False when usage < 100GB."""
        mock_memory.return_value = MagicMock(used=85 * (1024**3))
        monitor = MemoryMonitor()

        assert monitor.should_force_gc() is False

    @patch("forensic.io.memory.psutil.virtual_memory")
    def test_should_force_gc_true(self, mock_memory: MagicMock) -> None:
        """Test should_force_gc returns True when usage > 100GB."""
        mock_memory.return_value = MagicMock(used=105 * (1024**3))
        monitor = MemoryMonitor()

        assert monitor.should_force_gc() is True

    @patch("forensic.io.memory.gc.collect")
    @patch("forensic.io.memory.psutil.virtual_memory")
    def test_force_gc_returns_freed_bytes(
        self, mock_memory: MagicMock, mock_gc: MagicMock
    ) -> None:
        """Test force_gc returns freed bytes."""
        # Simulate memory freed by GC
        mock_memory.side_effect = [
            MagicMock(used=100 * (1024**3)),  # Before GC
            MagicMock(used=90 * (1024**3)),  # After GC
        ]
        monitor = MemoryMonitor()

        freed = monitor.force_gc()

        assert freed == 10 * (1024**3)
        mock_gc.assert_called_once()

    @patch("forensic.io.memory.gc.collect")
    @patch("forensic.io.memory.psutil.virtual_memory")
    def test_force_gc_returns_zero_when_no_freed(
        self, mock_memory: MagicMock, mock_gc: MagicMock
    ) -> None:
        """Test force_gc returns 0 when no memory freed."""
        mock_memory.return_value = MagicMock(used=100 * (1024**3))
        monitor = MemoryMonitor()

        freed = monitor.force_gc()

        assert freed == 0
        mock_gc.assert_called_once()


class TestMemoryMonitorChunkRecommendations:
    """Tests for chunk and batch size recommendations."""

    @pytest.fixture
    def dgx_spark_monitor(self) -> MemoryMonitor:
        """Create DGX Spark enabled monitor."""
        dgx_info = DGXSparkInfo(
            is_dgx_spark=True,
            is_arm64=True,
            cuda_available=True,
            memory_gb=128.0,
        )
        return MemoryMonitor(dgx_info=dgx_info)

    @pytest.fixture
    def regular_monitor(self) -> MemoryMonitor:
        """Create regular system monitor."""
        dgx_info = DGXSparkInfo(
            is_dgx_spark=False,
            is_arm64=False,
            cuda_available=False,
            memory_gb=16.0,
        )
        return MemoryMonitor(dgx_info=dgx_info)

    @patch("forensic.io.memory.psutil.virtual_memory")
    def test_recommended_chunk_size_normal_regular(
        self, mock_memory: MagicMock, regular_monitor: MemoryMonitor
    ) -> None:
        """Test recommended chunk size for regular system in normal state."""
        mock_memory.return_value = MagicMock(
            used=10 * (1024**3),
            available=6 * (1024**3),
            total=16 * (1024**3),
        )

        chunk_size = regular_monitor.get_recommended_chunk_size()

        assert chunk_size == DEFAULT_CHUNK_SIZE

    @patch("forensic.io.memory.psutil.virtual_memory")
    def test_recommended_chunk_size_normal_dgx_spark(
        self, mock_memory: MagicMock, dgx_spark_monitor: MemoryMonitor
    ) -> None:
        """Test recommended chunk size for DGX Spark in normal state with 64GB+ available."""
        mock_memory.return_value = MagicMock(
            used=50 * (1024**3),
            available=78 * (1024**3),
            total=128 * (1024**3),
        )

        chunk_size = dgx_spark_monitor.get_recommended_chunk_size()

        assert chunk_size == DGX_SPARK_CHUNK_SIZE

    @patch("forensic.io.memory.psutil.virtual_memory")
    def test_recommended_chunk_size_warning(
        self, mock_memory: MagicMock, dgx_spark_monitor: MemoryMonitor
    ) -> None:
        """Test recommended chunk size in warning state."""
        mock_memory.return_value = MagicMock(
            used=85 * (1024**3),
            available=43 * (1024**3),
            total=128 * (1024**3),
        )

        chunk_size = dgx_spark_monitor.get_recommended_chunk_size()

        assert chunk_size == WARNING_CHUNK_SIZE

    @patch("forensic.io.memory.psutil.virtual_memory")
    def test_recommended_chunk_size_critical(
        self, mock_memory: MagicMock, dgx_spark_monitor: MemoryMonitor
    ) -> None:
        """Test recommended chunk size in critical state."""
        mock_memory.return_value = MagicMock(
            used=105 * (1024**3),
            available=23 * (1024**3),
            total=128 * (1024**3),
        )

        chunk_size = dgx_spark_monitor.get_recommended_chunk_size()

        assert chunk_size == CRITICAL_CHUNK_SIZE

    @patch("forensic.io.memory.psutil.virtual_memory")
    def test_recommended_batch_size_normal_regular(
        self, mock_memory: MagicMock, regular_monitor: MemoryMonitor
    ) -> None:
        """Test recommended batch size for regular system in normal state."""
        mock_memory.return_value = MagicMock(
            used=10 * (1024**3),
            available=6 * (1024**3),
            total=16 * (1024**3),
        )

        batch_size = regular_monitor.get_recommended_batch_size()

        assert batch_size == DEFAULT_BATCH_SIZE

    @patch("forensic.io.memory.psutil.virtual_memory")
    def test_recommended_batch_size_normal_dgx_spark(
        self, mock_memory: MagicMock, dgx_spark_monitor: MemoryMonitor
    ) -> None:
        """Test recommended batch size for DGX Spark in normal state."""
        mock_memory.return_value = MagicMock(
            used=50 * (1024**3),
            available=78 * (1024**3),
            total=128 * (1024**3),
        )

        batch_size = dgx_spark_monitor.get_recommended_batch_size()

        assert batch_size == DGX_SPARK_BATCH_SIZE

    @patch("forensic.io.memory.psutil.virtual_memory")
    def test_recommended_batch_size_warning(
        self, mock_memory: MagicMock, dgx_spark_monitor: MemoryMonitor
    ) -> None:
        """Test recommended batch size in warning state."""
        mock_memory.return_value = MagicMock(
            used=85 * (1024**3),
            available=43 * (1024**3),
            total=128 * (1024**3),
        )

        batch_size = dgx_spark_monitor.get_recommended_batch_size()

        assert batch_size == WARNING_BATCH_SIZE

    @patch("forensic.io.memory.psutil.virtual_memory")
    def test_recommended_batch_size_critical(
        self, mock_memory: MagicMock, dgx_spark_monitor: MemoryMonitor
    ) -> None:
        """Test recommended batch size in critical state."""
        mock_memory.return_value = MagicMock(
            used=105 * (1024**3),
            available=23 * (1024**3),
            total=128 * (1024**3),
        )

        batch_size = dgx_spark_monitor.get_recommended_batch_size()

        assert batch_size == CRITICAL_BATCH_SIZE


class TestModuleFunctions:
    """Tests for module-level functions."""

    def test_get_memory_monitor_returns_singleton(self) -> None:
        """Test get_memory_monitor returns singleton."""
        clear_memory_monitor()

        monitor1 = get_memory_monitor()
        monitor2 = get_memory_monitor()

        assert monitor1 is monitor2

    def test_clear_memory_monitor(self) -> None:
        """Test clear_memory_monitor resets singleton."""
        monitor1 = get_memory_monitor()
        clear_memory_monitor()
        monitor2 = get_memory_monitor()

        assert monitor1 is not monitor2
