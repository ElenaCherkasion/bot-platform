from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from ..contracts.events import EventEnvelope, EventName


EventHandler = Callable[[EventEnvelope], Awaitable[None]]


@dataclass(frozen=True)
class Subscription:
    name: EventName
    handler: EventHandler
    # lower is earlier
    priority: int = 100
    # whether handler failures should stop further processing
    stop_on_error: bool = False
    # isolation: errors are captured and emitted as system events by bus
    isolate_errors: bool = True
