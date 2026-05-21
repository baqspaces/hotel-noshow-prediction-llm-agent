from dataclasses import dataclass
from time import time
from typing import Any

from .config import get_settings


@dataclass
class CacheEntry:
    value: Any
    expires_at: float


class TTLCache:
    def __init__(self) -> None:
        self._items: dict[str, CacheEntry] = {}

    def get(self, key: str) -> Any | None:
        entry = self._items.get(key)
        if not entry:
            return None
        if entry.expires_at < time():
            self._items.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> Any:
        ttl = ttl_seconds or get_settings().cache_ttl_seconds
        self._items[key] = CacheEntry(value=value, expires_at=time() + ttl)
        return value

    def stats(self) -> dict:
        now = time()
        active = sum(1 for entry in self._items.values() if entry.expires_at >= now)
        return {"active_keys": active, "ttl_seconds": get_settings().cache_ttl_seconds}


cache = TTLCache()
