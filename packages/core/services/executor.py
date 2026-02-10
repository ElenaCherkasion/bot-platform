from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, TypeVar

from ..contracts.events import EventEnvelope
from ..contracts.results import ErrorInfo, ResultMeta, ServiceResult
from ..contracts.services import ServiceCall
from ..events.bus import EventBus
from ..middleware.chain import MiddlewareChain
from ..middleware.types import ServiceOp
from ..registry.services import ServiceRegistry
from .deferred_store import DeferredStore

T = TypeVar("T")


@dataclass(frozen=True)
class ServiceExecutor:
    """
    Единственная точка вызова сервисов.

    - timeout/retry
    - service events in bus
    - middleware chain
    - deferred tickets (optional)
    """

    bus: EventBus
    registry: ServiceRegistry
    chain: MiddlewareChain | None = None
    deferred: DeferredStore[Any] | None = None  # store is type-erased at core level

    async def call(
        self,
        *,
        service_key: str,
        call: ServiceCall,
        op_name: str,
        fn: Callable[[], Awaitable[ServiceResult[T]]],
        deferred_ttl_seconds: int = 3600,
    ) -> ServiceResult[T]:
        started = int(time.time() * 1000)
        last_error: Optional[ServiceResult[T]] = None
        attempts = max(1, call.max_attempts)

        for attempt in range(1, attempts + 1):
            try:
                op = ServiceOp(service_key=service_key, op_name=op_name, call=call)

                async def terminal() -> ServiceResult[T]:
                    return await fn()

                if self.chain is not None:
                    coro = self.chain.run(op, terminal)
                else:
                    coro = terminal()

                res = await asyncio.wait_for(coro, timeout=call.timeout_ms / 1000.0)

                # if deferred -> remember pending ticket (if store configured)
                if res.status == "deferred" and res.ticket_id and self.deferred is not None:
                    await self.deferred.put_pending(res.ticket_id, ttl_seconds=deferred_ttl_seconds)

                await self._publish_service_event(
                    tenant_id=call.tenant_id,
                    trace_id=call.trace_id,
                    request_id=call.request_id,
                    name=f"service.{op_name}.{res.status}",
                    payload={
                        "service_key": service_key,
                        "attempt": attempt,
                        "provider": res.meta.provider_name,
                        "ticket_id": res.ticket_id,
                    },
                )
                return res

            except asyncio.TimeoutError:
                meta = ResultMeta(
                    request_id=call.request_id,
                    tenant_id=call.tenant_id,
                    trace_id=call.trace_id,
                    started_at_ms=started,
                    finished_at_ms=int(time.time() * 1000),
                    provider_name=None,
                    attempt=attempt,
                    idempotency_key=call.idempotency_key,
                    tags=call.tags,
                )
                last_error = ServiceResult(
                    status="error",
                    meta=meta,
                    error=ErrorInfo(code="timeout", message="Service timeout", retryable=(attempt < attempts)),
                )

            except Exception as exc:
                meta = ResultMeta(
                    request_id=call.request_id,
                    tenant_id=call.tenant_id,
                    trace_id=call.trace_id,
                    started_at_ms=started,
                    finished_at_ms=int(time.time() * 1000),
                    provider_name=None,
                    attempt=attempt,
                    idempotency_key=call.idempotency_key,
                    tags=call.tags,
                )
                last_error = ServiceResult(
                    status="error",
                    meta=meta,
                    error=ErrorInfo(code="exception", message=str(exc), retryable=(attempt < attempts)),
                )

            await self._publish_service_event(
                tenant_id=call.tenant_id,
                trace_id=call.trace_id,
                request_id=call.request_id,
                name=f"service.{op_name}.error",
                payload={
                    "service_key": service_key,
                    "attempt": attempt,
                    "provider": None,
                    "error_code": last_error.error.code if last_error and last_error.error else "unknown",
                },
            )

            if not last_error or not last_error.error or not last_error.error.retryable:
                break

        return last_error  # type: ignore[return-value]

    async def complete_deferred(
        self,
        *,
        tenant_id: str,
        trace_id: str,
        request_id: str,
        op_name: str,
        ticket_id: str,
        result: ServiceResult[Any],
        ttl_seconds: int = 3600,
    ) -> None:
        """
        Complete a deferred operation and publish completed event.
        """
        if self.deferred is not None:
            await self.deferred.complete(ticket_id, result, ttl_seconds=ttl_seconds)

        await self._publish_service_event(
            tenant_id=tenant_id,
            trace_id=trace_id,
            request_id=request_id,
            name=f"service.{op_name}.completed",
            payload={
                "ticket_id": ticket_id,
                "status": result.status,
                "provider": result.meta.provider_name,
            },
        )

    async def _publish_service_event(
        self,
        *,
        tenant_id: str,
        trace_id: str,
        request_id: str,
        name: str,
        payload: dict[str, Any],
    ) -> None:
        evt = EventEnvelope(
            name=name,
            kind="service",
            tenant_id=tenant_id,
            event_id=f"evt_{int(time.time() * 1000)}",
            trace_id=trace_id,
            occurred_at_ms=int(time.time() * 1000),
            request_id=request_id,
            payload=payload,
        )
        await self.bus.publish(evt)
