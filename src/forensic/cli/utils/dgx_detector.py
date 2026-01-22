"""DGX Spark detection utility"""
import platform
from pathlib import Path


class DGXSparkDetector:
    """Detects if running on NVIDIA DGX Spark system"""

    def __init__(self) -> None:
        self._cached_result: bool | None = None

    def is_dgx_spark(self) -> bool:
        """Check if running on DGX Spark"""
        if self._cached_result is not None:
            return self._cached_result

        # Check for NVIDIA GPU
        try:
            import torch
            if torch.cuda.is_available():
                self._cached_result = True
                return True
        except ImportError:
            pass

        # Check for common DGX indicators
        if self._check_dgx_files():
            self._cached_result = True
            return True

        self._cached_result = False
        return False

    def _check_dgx_files(self) -> bool:
        """Check for DGX-specific files"""
        dgx_paths = [
            "/etc/dgx",
            "/usr/share/dgx",
            "/opt/mellanox/dgx",
        ]
        return any(Path(p).exists() for p in dgx_paths)

    def detect(self) -> dict:
        """Detect DGX Spark system information"""
        info = {}

        if not self.is_dgx_spark():
            return info

        info["is_dgx"] = True
        info["platform"] = platform.system()

        try:
            import torch
            info["gpu_count"] = torch.cuda.device_count()
            info["gpu_name"] = torch.cuda.get_device_name(0) if info["gpu_count"] > 0 else None
            info["cuda_version"] = torch.version.cuda
        except ImportError:
            pass

        return info
