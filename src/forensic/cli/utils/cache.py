"""Cache management for CLI operations"""

import hashlib
import pickle
from contextlib import suppress
from datetime import datetime, timedelta
from pathlib import Path

from forensic.cli.models.config import CacheConfig


class CacheManager:
    def __init__(self, config: CacheConfig | None = None) -> None:
        self.config = config or CacheConfig()
        self.cache_dir = Path(self.config.directory)
        if self.config.enabled:
            with suppress(OSError):
                self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, key: str) -> Path:
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"

    def _is_expired(self, metadata: dict) -> bool:
        if "created_at" not in metadata:
            return True
        created_at = datetime.fromisoformat(metadata["created_at"])
        expiry = created_at + timedelta(days=self.config.ttl_days)
        return datetime.now() > expiry

    def get(self, key: str, default=None):
        if not self.config.enabled:
            return default
        cache_path = self._get_cache_path(key)
        if not cache_path.exists():
            return default
        with suppress(Exception), open(cache_path, "rb") as f:
            return pickle.load(f)
        return default

    def set(self, key: str, value) -> None:
        if not self.config.enabled:
            return
        cache_path = self._get_cache_path(key)
        with suppress(Exception), open(cache_path, "wb") as f:
            pickle.dump(value, f)

    def delete(self, key: str) -> bool:
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            with suppress(OSError):
                cache_path.unlink()
            return True
        return False

    def clear(self) -> int:
        count = 0
        for file_path in self.cache_dir.glob("*.cache"):
            with suppress(OSError):
                file_path.unlink()
                count += 1
        return count

    @staticmethod
    def generate_key(*args, **kwargs) -> str:
        key_parts = [str(a) for a in args]
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        key_string = ":".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()[:32]
