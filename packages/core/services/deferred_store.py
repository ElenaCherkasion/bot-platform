from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Dict, Generic, Optional, Protocol, Tuple, TypeVar

from ..contracts.results import ServiceResult

T = TypeVar("T")


class DeferredStore(Protocol, Generic[T]):
    """
    Stores deferred results by ticket_id.
    """

    async def put_pending(self, ticket_id: str, *, ttl_seconds: int) -> None:
        ...

    async def complete(self, ticket_id: str, result: ServiceResult[T], *, ttl_seconds: int) -> None:
        ...

    async def get(self, ticket_id: str) -> Optional[ServiceResult[T]]:
        ...


@dataclass
class InMemoryDeferredStore(Generic[T]):
    def __init__(self) -> None:
        # ticket_id -> (expires_at_ms, result_or_none)
        self._data: Dict[str, Tuple[int, Optional[ServiceResult[T]]]] = {}
        self._mx = asyncio.Lock()

    def _now_ms(self) -> int:
        return int(time.time() * 1000)

    async def put_pending(self, ticket_id: str, *, ttl_seconds: int) -> None:
        async with self._mx:
            self._data[ticket_id] = (self._now_ms() + ttl_seconds * 1000, None)

    async def complete(self, ticket_id: str, result: ServiceResult[T], *, ttl_seconds: int) -> None:
        async with self._mx:
            self._data[ticket_id] = (self._now_ms() + ttl_seconds * 1000, result)

    async def get(self, ticket_id: str) -> Optional[ServiceResult[T]]:
        async with self._mx:
            item = self._data.get(ticket_id)
            if not item:
                return None
            expires_at, res = item
            if self._now_ms() >= expires_at:
                self._data.pop(ticket_id, None)
                return None
            return res
