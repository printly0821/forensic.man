"""
Memory monitoring module for DGX Spark optimized file processing.

Provides real-time memory usage tracking with threshold-based
automatic adjustments for chunk sizes and batch processing.
"""

import gc
from dataclasses import dataclass
from typing import Protocol

import psutil

from forensic.utils.dgx_detector import DGXSparkInfo, detect_dgx_spark

# Memory thresholds in GB
MEMORY_WARNING_THRESHOLD_GB: float = 80.0
MEMORY_CRITICAL_THRESHOLD_GB: float = 100.0

# Chunk sizes in bytes
DEFAULT_CHUNK_SIZE: int = 1024 * 1024  # 1MB
DGX_SPARK_CHUNK_SIZE: int = 4 * 1024 * 1024  # 4MB
WARNING_CHUNK_SIZE: int = 512 * 1024  # 512KB
CRITICAL_CHUNK_SIZE: int = 256 * 1024  # 256KB

# Batch sizes
DEFAULT_BATCH_SIZE: int = 10
DGX_SPARK_BATCH_SIZE: int = 50
WARNING_BATCH_SIZE: int = 5
CRITICAL_BATCH_SIZE: int = 1

# DGX Spark memory threshold for optimization
DGX_SPARK_MEMORY_THRESHOLD_GB: float = 64.0


class MemoryMonitorProtocol(Protocol):
    """Memory monitoring interface protocol."""

    def get_usage_gb(self) -> float:
        """Return current memory usage in GB."""
        ...

    def get_available_gb(self) -> float:
        """Return available memory in GB."""
        ...

    def should_reduce_chunk_size(self) -> bool:
        """Return True if chunk size should be reduced (>80GB usage)."""
        ...

    def force_gc(self) -> int:
        """Force garbage collection and return freed bytes."""
        ...


@dataclass
class MemoryState:
    """
    Current memory state information.

    Attributes:
        usage_gb: Current memory usage in GB.
        available_gb: Available memory in GB.
        total_gb: Total system memory in GB.
        level: Memory pressure level ('normal', 'warning', 'critical').
    """

    usage_gb: float
    available_gb: float
    total_gb: float
    level: str


class MemoryMonitor:
    """
    Memory monitor for DGX Spark optimized file processing.

    Monitors system memory usage and provides adaptive chunk size
    recommendations based on memory pressure levels.

    Attributes:
        dgx_info: DGX Spark system information.
    """

    def __init__(self, dgx_info: DGXSparkInfo | None = None) -> None:
        """
        Initialize memory monitor.

        Args:
            dgx_info: Optional DGX Spark info. Auto-detected if not provided.
        """
        self._dgx_info = dgx_info if dgx_info is not None else detect_dgx_spark()

    @property
    def dgx_info(self) -> DGXSparkInfo:
        """Return DGX Spark system information."""
        return self._dgx_info

    def get_usage_gb(self) -> float:
        """
        Return current memory usage in GB.

        Returns:
            Current memory usage in gigabytes.
        """
        memory = psutil.virtual_memory()
        return memory.used / (1024**3)

    def get_available_gb(self) -> float:
        """
        Return available memory in GB.

        Returns:
            Available memory in gigabytes.
        """
        memory = psutil.virtual_memory()
        return memory.available / (1024**3)

    def get_total_gb(self) -> float:
        """
        Return total system memory in GB.

        Returns:
            Total system memory in gigabytes.
        """
        memory = psutil.virtual_memory()
        return memory.total / (1024**3)

    def get_memory_state(self) -> MemoryState:
        """
        Return current memory state with pressure level.

        Returns:
            MemoryState with usage, available, total, and level.
        """
        memory = psutil.virtual_memory()
        usage_gb = memory.used / (1024**3)
        available_gb = memory.available / (1024**3)
        total_gb = memory.total / (1024**3)

        level = self._determine_level(usage_gb)

        return MemoryState(
            usage_gb=usage_gb,
            available_gb=available_gb,
            total_gb=total_gb,
            level=level,
        )

    def _determine_level(self, usage_gb: float) -> str:
        """
        Determine memory pressure level based on usage.

        Args:
            usage_gb: Current memory usage in GB.

        Returns:
            Memory pressure level ('normal', 'warning', 'critical').
        """
        if usage_gb > MEMORY_CRITICAL_THRESHOLD_GB:
            return "critical"
        elif usage_gb > MEMORY_WARNING_THRESHOLD_GB:
            return "warning"
        return "normal"

    def should_reduce_chunk_size(self) -> bool:
        """
        Return True if chunk size should be reduced.

        Chunk size reduction is recommended when memory usage
        exceeds 80GB (warning threshold).

        Returns:
            True if memory usage exceeds warning threshold.
        """
        return self.get_usage_gb() > MEMORY_WARNING_THRESHOLD_GB

    def should_force_gc(self) -> bool:
        """
        Return True if forced garbage collection is needed.

        Forced GC is recommended when memory usage exceeds
        100GB (critical threshold).

        Returns:
            True if memory usage exceeds critical threshold.
        """
        return self.get_usage_gb() > MEMORY_CRITICAL_THRESHOLD_GB

    def force_gc(self) -> int:
        """
        Force garbage collection and return freed bytes.

        Executes full garbage collection across all generations
        to reclaim memory.

        Returns:
            Number of bytes freed (estimated).
        """
        memory_before = psutil.virtual_memory().used
        gc.collect()
        memory_after = psutil.virtual_memory().used

        freed = memory_before - memory_after
        return max(0, freed)

    def get_recommended_chunk_size(self) -> int:
        """
        Get recommended chunk size based on current memory state.

        Chunk size recommendations:
        - Normal + DGX Spark (64GB+ available): 4MB
        - Normal: 1MB
        - Warning: 512KB
        - Critical: 256KB

        Returns:
            Recommended chunk size in bytes.
        """
        state = self.get_memory_state()

        if state.level == "critical":
            return CRITICAL_CHUNK_SIZE
        elif state.level == "warning":
            return WARNING_CHUNK_SIZE

        # Normal state - check DGX Spark optimization
        if self._is_dgx_spark_optimized():
            return DGX_SPARK_CHUNK_SIZE

        return DEFAULT_CHUNK_SIZE

    def get_recommended_batch_size(self) -> int:
        """
        Get recommended batch size based on current memory state.

        Batch size recommendations:
        - Normal + DGX Spark (64GB+ available): 50
        - Normal: 10
        - Warning: 5
        - Critical: 1

        Returns:
            Recommended batch size.
        """
        state = self.get_memory_state()

        if state.level == "critical":
            return CRITICAL_BATCH_SIZE
        elif state.level == "warning":
            return WARNING_BATCH_SIZE

        # Normal state - check DGX Spark optimization
        if self._is_dgx_spark_optimized():
            return DGX_SPARK_BATCH_SIZE

        return DEFAULT_BATCH_SIZE

    def _is_dgx_spark_optimized(self) -> bool:
        """
        Check if DGX Spark optimization is available.

        Returns True if running on DGX Spark with sufficient
        available memory (>= 64GB).

        Returns:
            True if DGX Spark optimization is available.
        """
        if not self._dgx_info.is_optimized:
            return False

        return self.get_available_gb() >= DGX_SPARK_MEMORY_THRESHOLD_GB


# Module-level convenience functions
_monitor: MemoryMonitor | None = None


def get_memory_monitor() -> MemoryMonitor:
    """
    Get global memory monitor instance.

    Returns:
        Global MemoryMonitor instance.
    """
    global _monitor
    if _monitor is None:
        _monitor = MemoryMonitor()
    return _monitor


def clear_memory_monitor() -> None:
    """Clear global memory monitor instance."""
    global _monitor
    _monitor = None
