from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Protocol

from .results import ServiceResult


@dataclass(frozen=True)
class ServiceCall:
    tenant_id: str
    request_id: str
    trace_id: str

    timeout_ms: int = 3_000
    max_attempts: int = 2
    idempotency_key: Optional[str] = None

    # arbitrary, safe metadata (no secrets)
    tags: Mapping[str, str] = field(default_factory=dict)


# --- Neutral “intellectual” services (no provider assumptions) ---

@dataclass(frozen=True)
class TextComposeIn:
    locale: str
    template_key: str
    variables: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TextComposeOut:
    text: str
    format: str = "plain"  # "plain" | "markdown" | "html" (core just passes through)


class TextComposer(Protocol):
    async def compose(self, call: ServiceCall, inp: TextComposeIn) -> ServiceResult[TextComposeOut]:
        ...


@dataclass(frozen=True)
class IntentResolveIn:
    text: str
    locale: str
    channel: str = "telegram"
    context: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IntentResolveOut:
    intent: str
    confidence: float
    slots: Mapping[str, Any] = field(default_factory=dict)


class IntentResolver(Protocol):
    async def resolve(self, call: ServiceCall, inp: IntentResolveIn) -> ServiceResult[IntentResolveOut]:
        ...


@dataclass(frozen=True)
class KnowledgeRespondIn:
    question: str
    locale: str
    context: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeRespondOut:
    answer_text: str
    sources: list[str] = field(default_factory=list)  # ids/keys only


class KnowledgeResponder(Protocol):
    async def respond(self, call: ServiceCall, inp: KnowledgeRespondIn) -> ServiceResult[KnowledgeRespondOut]:
        ...
