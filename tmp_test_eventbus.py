import asyncio
import time
import uuid

from core.events.bus import EventBus
from core.events.types import Subscription
from core.contracts.events import EventEnvelope


def now_ms() -> int:
    return int(time.time() * 1000)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


async def handler_ok(event: EventEnvelope) -> None:
    print("[ok] got:", event.name, event.payload)


async def handler_fail(event: EventEnvelope) -> None:
    print("[fail] got:", event.name, "-> raising")
    raise RuntimeError("boom")


async def handler_error_logger(event: EventEnvelope) -> None:
    print("[sys] handler_error:", event.payload.get("failed_event"), event.payload.get("error_type"))


async def main() -> None:
    bus = EventBus()

    # subscribe handlers to domain event
    bus.subscribe(Subscription(name="demo.event", handler=handler_fail, priority=50, isolate_errors=True))
    bus.subscribe(Subscription(name="demo.event", handler=handler_ok, priority=100, isolate_errors=True))

    # subscribe system error handler
    bus.subscribe(Subscription(name="system.handler_error", handler=handler_error_logger, priority=10, isolate_errors=True))

    evt = EventEnvelope(
        name="demo.event",
        kind="domain",
        tenant_id="tenant_demo",
        event_id=new_id("evt"),
        trace_id=new_id("trc"),
        occurred_at_ms=now_ms(),
        payload={"x": 1},
        request_id=new_id("req"),
    )

    await bus.publish(evt)


if __name__ == "__main__":
    asyncio.run(main())
