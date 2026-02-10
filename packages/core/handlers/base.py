from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from ..contracts.results import ServiceResult
from ..runtime.context import RuntimeContext

In = TypeVar("In")
Out = TypeVar("Out")


@dataclass(frozen=True)
class HandlerResult(Generic[Out]):
    """
    What handler returns to the transport layer (Telegram/HTTP/etc).
    """
    result: ServiceResult[Out]


class BaseHandler(Generic[In, Out]):
    """
    Transport-level adapter.

    MUST NOT:
    - access providers
    - access registry directly
    - publish events
    """

    async def handle(self, ctx: RuntimeContext, inp: In) -> HandlerResult[Out]:
        raise NotImplementedError
