from __future__ import annotations

from typing import TypeVar

from ..contracts.results import ErrorInfo, ResultMeta, ServiceResult
from .idempotency_store import IdempotencyStore
from .types import Next, ServiceOp

T = TypeVar("T")


def make_idempotency_middleware(
    *,
    store: IdempotencyStore[T],
    ttl_seconds: int = 300,
    lock_ttl_seconds: int = 30,
):
    async def mw(op: ServiceOp[T], nxt: Next[T]) -> ServiceResult[T]:
        key = op.call.idempotency_key
        if not key:
            return await nxt()

        cached = await store.get(key)
        if cached is not None:
            return cached

        acquired = await store.lock(key, ttl_seconds=lock_ttl_seconds)
        if not acquired:
            # Someone else is working; return a deterministic retryable error
            meta = ResultMeta(
                request_id=op.call.request_id,
                tenant_id=op.call.tenant_id,
                trace_id=op.call.trace_id,
                started_at_ms=op.call.tags.get("started_at_ms", 0) if isinstance(op.call.tags, dict) else 0,
                finished_at_ms=None,
                provider_name=None,
                attempt=1,
                idempotency_key=key,
                tags=op.call.tags,
            )
            return ServiceResult(
                status="error",
                meta=meta,
                error=ErrorInfo(code="in_progress", message="Operation in progress", retryable=True),
            )

        try:
            res = await nxt()
            await store.put(key, res, ttl_seconds=ttl_seconds)
            return res
        finally:
            await store.unlock(key)

    return mw
