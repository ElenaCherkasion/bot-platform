from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from typing import DefaultDict, List

from .types import Subscription
from ..contracts.events import EventEnvelope

logger = logging.getLogger(__name__)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


class EventBus:
    """
    Simple in-memory event bus.

    - deterministic order by priority
    - error isolation per handler
    - emits system event on handler failure
    - supports unsubscribe (needed for runtime module detach)
    """

    def __init__(self) -> None:
        self._subscriptions: DefaultDict[str, List[Subscription]] = defaultdict(list)

    def subscribe(self, sub: Subscription) -> None:
        self._subscriptions[sub.name].append(sub)
        self._subscriptions[sub.name].sort(key=lambda s: s.priority)

        logger.debug(
            "Subscribed handler=%s to event=%s priority=%s",
            sub.handler,
            sub.name,
            sub.priority,
        )

    def unsubscribe(self, name: str, handler) -> int:
        """
        Remove subscriptions for event name and handler.
        Returns number of removed subscriptions.
        """
        subs = self._subscriptions.get(name, [])
        if not subs:
            return 0

        before = len(subs)
        subs = [s for s in subs if s.handler is not handler]
        removed = before - len(subs)

        if subs:
            self._subscriptions[name] = subs
        else:
            self._subscriptions.pop(name, None)

        return removed

    async def publish(self, event: EventEnvelope) -> None:
        subs = list(self._subscriptions.get(event.name, []))

        if not subs:
            logger.debug("No subscribers for event %s", event.name)
            return

        for sub in subs:
            try:
                await sub.handler(event)

            except Exception as exc:
                logger.exception(
                    "Error in handler=%s for event=%s",
                    sub.handler,
                    event.name,
                )

                if sub.isolate_errors:
                    err_event = EventEnvelope(
                        name="system.handler_error",
                        kind="system",
                        tenant_id=event.tenant_id,
                        event_id=_new_id("evt"),
                        trace_id=event.trace_id,
                        occurred_at_ms=_now_ms(),
                        request_id=event.request_id,
                        ticket_id=event.ticket_id,
                        payload={
                            "failed_event": event.name,
                            "handler": repr(sub.handler),
                            "error_type": type(exc).__name__,
                            "error_message": str(exc),
                        },
                    )
                    await self._publish_internal(err_event)

                    if sub.stop_on_error:
                        break
                    continue

                raise

    async def _publish_internal(self, event: EventEnvelope) -> None:
        subs = list(self._subscriptions.get(event.name, []))
        for sub in subs:
            try:
                await sub.handler(event)
            except Exception:
                logger.exception("Error in system handler=%s for event=%s", sub.handler, event.name)
                # swallow
