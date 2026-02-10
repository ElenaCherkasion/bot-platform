from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Generic, Literal, Mapping, Optional, TypeVar

T = TypeVar("T")

ResultStatus = Literal["ok", "error", "deferred", "partial"]


@dataclass(frozen=True)
class ResultMeta:
    request_id: str
    tenant_id: str
    trace_id: str
    started_at_ms: int
    finished_at_ms: Optional[int] = None

    provider_name: Optional[str] = None
    attempt: int = 1
    idempotency_key: Optional[str] = None

    # for debugging/observability, never store secrets
    tags: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ErrorInfo:
    code: str               # stable machine code, e.g. "timeout", "bad_config"
    message: str            # safe human message
    retryable: bool = False
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ServiceResult(Generic[T]):
    status: ResultStatus
    meta: ResultMeta
    data: Optional[T] = None
    error: Optional[ErrorInfo] = None

    # optional streaming channel (for long operations)
    stream: Optional[AsyncIterator[T]] = None

    # if deferred, core returns ticket_id and later emits an event when completed
    ticket_id: Optional[str] = None
