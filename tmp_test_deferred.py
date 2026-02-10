import asyncio
import time
import uuid

from core.bootstrap import build_core
from core.contracts.results import ResultMeta, ServiceResult
from core.middleware.chain import MiddlewareChain
from core.middleware.logging_mw import logging_middleware
from core.runtime.context import RuntimeContext
from core.services.deferred_store import InMemoryDeferredStore
from core.services.executor import ServiceExecutor


def now_ms() -> int:
    return int(time.time() * 1000)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


async def main() -> None:
    app = build_core()

    store = InMemoryDeferredStore()
    chain = MiddlewareChain()
    chain.add(logging_middleware)

    executor = ServiceExecutor(bus=app.bus, registry=app.services, chain=chain, deferred=store)

    # subscribe to deferred + completed events
    async def on_deferred(event):
        print("[evt]", event.name, event.payload)

    async def on_completed(event):
        print("[evt]", event.name, event.payload)

    from core.events.types import Subscription
    app.bus.subscribe(Subscription(name="service.demo_op.deferred", handler=on_deferred, priority=10))
    app.bus.subscribe(Subscription(name="service.demo_op.completed", handler=on_completed, priority=10))

    ctx = RuntimeContext.new(tenant_id="tenant_demo", locale="ru")
    call = ctx.to_service_call(timeout_ms=1000, max_attempts=1, idempotency_key="idem_deferred_1")

    ticket_id = new_id("tkt")

    async def fake_service_call():
        meta = ResultMeta(
            request_id=call.request_id,
            tenant_id=call.tenant_id,
            trace_id=call.trace_id,
            started_at_ms=now_ms(),
            finished_at_ms=now_ms(),
            provider_name="demo_provider",
            attempt=1,
            idempotency_key=call.idempotency_key,
            tags=call.tags,
        )
        return ServiceResult(status="deferred", meta=meta, ticket_id=ticket_id)

    # 1) call returns deferred ticket
    res = await executor.call(
        service_key="DemoService",
        call=call,
        op_name="demo_op",
        fn=fake_service_call,
    )
    print("call result:", res.status, res.ticket_id)

    # 2) later we complete it
    await asyncio.sleep(0.2)

    meta2 = ResultMeta(
        request_id=call.request_id,
        tenant_id=call.tenant_id,
        trace_id=call.trace_id,
        started_at_ms=now_ms(),
        finished_at_ms=now_ms(),
        provider_name="demo_provider",
        attempt=1,
        idempotency_key=call.idempotency_key,
        tags=call.tags,
    )
    final = ServiceResult(status="ok", meta=meta2, data={"answer": "готово"})

    await executor.complete_deferred(
        tenant_id=call.tenant_id,
        trace_id=call.trace_id,
        request_id=call.request_id,
        op_name="demo_op",
        ticket_id=ticket_id,
        result=final,
    )

    cached = await store.get(ticket_id)
    print("stored:", cached.status if cached else None, cached.data if cached else None)


if __name__ == "__main__":
    asyncio.run(main())
