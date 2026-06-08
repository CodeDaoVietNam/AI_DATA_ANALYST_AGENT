from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class CacheLookup:
    hit: bool
    value: Any = None
    key: str | None = None


class TTLCache:
    def __init__(self, ttl_seconds: int):
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> CacheLookup:
        item = self._items.get(key)
        if item is None:
            return CacheLookup(hit=False, key=key)
        expires_at, value = item
        if expires_at < time.time():
            self._items.pop(key, None)
            return CacheLookup(hit=False, key=key)
        return CacheLookup(hit=True, value=value, key=key)

    def set(self, key: str, value: Any) -> Any:
        self._items[key] = (time.time() + self.ttl_seconds, value)
        return value

    def get_or_set(self, key: str, factory: Callable[[], Any]) -> tuple[Any, bool]:
        lookup = self.get(key)
        if lookup.hit:
            return lookup.value, True
        value = factory()
        self.set(key, value)
        return value, False

    def invalidate_prefix(self, prefix: str) -> None:
        for key in list(self._items):
            if key.startswith(prefix):
                self._items.pop(key, None)

    def clear(self) -> None:
        self._items.clear()

    def stats(self) -> dict[str, int]:
        now = time.time()
        expired = [key for key, (expires_at, _) in self._items.items() if expires_at < now]
        for key in expired:
            self._items.pop(key, None)
        return {"items": len(self._items)}


semantic_profile_cache = TTLCache(ttl_seconds=30 * 60)
dashboard_cache = TTLCache(ttl_seconds=10 * 60)
tool_result_cache = TTLCache(ttl_seconds=10 * 60)


def stable_cache_key(namespace: str, *parts: Any) -> str:
    encoded = json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str)
    return f"{namespace}:{encoded}"


def invalidate_dataset_cache(dataset_id: str) -> None:
    prefix = f'{json.dumps([dataset_id], ensure_ascii=False, sort_keys=True, default=str)[:-1]}'
    for cache, namespace in [
        (semantic_profile_cache, "semantic"),
        (dashboard_cache, "dashboard"),
        (tool_result_cache, "tool"),
    ]:
        cache.invalidate_prefix(f"{namespace}:{prefix}")
