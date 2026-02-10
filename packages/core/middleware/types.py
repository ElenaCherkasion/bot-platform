from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Generic, Protocol, TypeVar

from ..contracts.results import ServiceResult
from ..contracts.services import ServiceCall

T = TypeVar("T")


@dataclass(frozen=True)
class ServiceOp(Generic[T]):
    """
    Describes a service operation being executed.
    """
    service_key: str
    op_name: str
    call: ServiceCall


Next = Callable[[], Awaitable[ServiceResult[T]]]


class ServiceMiddleware(Protocol, Generic[T]):
    async def __call__(self, op: ServiceOp[T], nxt: Next[T]) -> ServiceResult[T]:
        ...
