from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Mapping

from ..contracts.services import ServiceCall


def now_ms() -> int:
    return int(time.time() * 1000)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass(frozen=True)
class RuntimeContext:
    tenant_id: str
    request_id: str
    trace_id: str
    started_at_ms: int = field(default_factory=now_ms)

    locale: str = "ru"
    tags: Mapping[str, str] = field(default_factory=dict)

    @staticmethod
    def new(tenant_id: str, locale: str = "ru", tags: Mapping[str, str] | None = None) -> "RuntimeContext":
        return RuntimeContext(
            tenant_id=tenant_id,
            request_id=new_id("req"),
            trace_id=new_id("trc"),
            locale=locale,
            tags=tags or {},
        )

    def to_service_call(
        self,
        *,
        timeout_ms: int = 3_000,
        max_attempts: int = 2,
        idempotency_key: str | None = None,
    ) -> ServiceCall:
        return ServiceCall(
            tenant_id=self.tenant_id,
            request_id=self.request_id,
            trace_id=self.trace_id,
            timeout_ms=timeout_ms,
            max_attempts=max_attempts,
            idempotency_key=idempotency_key,
            tags=self.tags,
        )
