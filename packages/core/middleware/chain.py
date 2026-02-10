from __future__ import annotations

from dataclasses import dataclass, field
from typing import Awaitable, Callable, Generic, List, TypeVar

from ..contracts.results import ServiceResult
from .types import Next, ServiceMiddleware, ServiceOp

T = TypeVar("T")


@dataclass
class MiddlewareChain:
    middlewares: List[Callable[[ServiceOp[T], Next[T]], Awaitable[ServiceResult[T]]]] = field(default_factory=list)

    def add(self, mw: Callable[[ServiceOp[T], Next[T]], Awaitable[ServiceResult[T]]]) -> None:
        self.middlewares.append(mw)

    async def run(self, op: ServiceOp[T], terminal: Next[T]) -> ServiceResult[T]:
        """
        Run middlewares around terminal operation.
        """
        async def call_at(i: int) -> ServiceResult[T]:
            if i >= len(self.middlewares):
                return await terminal()

            mw = self.middlewares[i]

            async def nxt() -> ServiceResult[T]:
                return await call_at(i + 1)

            return await mw(op, nxt)

        return await call_at(0)
