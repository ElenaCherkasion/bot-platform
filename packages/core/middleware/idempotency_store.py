from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Dict, Generic, Optional, Protocol, Tuple, TypeVar

from ..contracts.results import ServiceResult

T = TypeVar("T")


class IdempotencyStore(Protocol, Generic[T]):
    """
    Stores results by idempotency key.

    Contract:
    - get(key) -> cached result or None
    - put(key, result, ttl) -> saves result for later reuse
    - lock(key) -> prevents concurrent duplicate work (best-effort)
    """

    async def get(self, key: str) -> Optional[ServiceResult[T]]:
        ...

    async def put(self, key: str, result: ServiceResult[T], *, ttl_seconds: int) -> None:
        ...

    async def lock(self, key: str, *, ttl_seconds: int) -> bool:
        ...

    async def unlock(self, key: str) -> None:
        ...


@dataclass
class InMemoryIdempotencyStore(Generic[T]):
    """
    Dev/test store. For prod we'll implement Redis/PostgreSQL-backed store.
    """

    def __init__(self) -> None:
        # key -> (expires_at_ms, result)
        self._data: Dict[str, Tuple[int, ServiceResult[T]]] = {}
        # key -> lock_expires_at_ms
        self._locks: Dict[str, int] = {}
        self._mx = asyncio.Lock()

    def _now_ms(self) -> int:
        return int(time.time() * 1000)

    async def get(self, key: str) -> Optional[ServiceResult[T]]:
        async with self._mx:
            item = self._data.get(key)
            if not item:
                return None
            expires_at, res = item
            if self._now_ms() >= expires_at:
                self._data.pop(key, None)
                return None
            return res

    async def put(self, key: str, result: ServiceResult[T], *, ttl_seconds: int) -> None:
        async with self._mx:
            expires_at = self._now_ms() + ttl_seconds * 1000
            self._data[key] = (expires_at, result)

    async def lock(self, key: str, *, ttl_seconds: int) -> bool:
        """
        Best-effort lock:
        - returns True if lock acquired
        - returns False if someone already holds a non-expired lock
        """
        async with self._mx:
            now = self._now_ms()
            exp = self._locks.get(key)
            if exp is not None and now < exp:
                return False
            self._locks[key] = now + ttl_seconds * 1000
            return True

    async def unlock(self, key: str) -> None:
        async with self._mx:
            self._locks.pop(key, None)
