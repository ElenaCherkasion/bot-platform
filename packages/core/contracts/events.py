from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Literal, Optional


EventName = str
EventKind = Literal["domain", "service", "system"]


@dataclass(frozen=True)
class EventEnvelope:
    name: EventName
    kind: EventKind

    tenant_id: str
    event_id: str
    trace_id: str
    occurred_at_ms: int

    payload: Mapping[str, Any] = field(default_factory=dict)

    # optional correlation to a previous request/ticket
    request_id: Optional[str] = None
    ticket_id: Optional[str] = None
