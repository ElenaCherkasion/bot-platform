from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

from ..bootstrap import CoreApp
from ..events.types import Subscription


@dataclass
class ModuleHandle:
    """
    Tracks what module attached so we can detach safely.
    """
    module_key: str
    tenant_id: str

    # what the module subscribed to (so we can unsubscribe later)
    subscriptions: list[Subscription] = field(default_factory=list)

    # providers registered by module (name list, so we can optionally clean up)
    provider_names: list[str] = field(default_factory=list)

    # bindings keys applied by module (service_key list)
    service_keys: list[str] = field(default_factory=list)


class CoreModule(Protocol):
    module_key: str

    def attach(self, app: CoreApp, *, tenant_id: str, cfg: Mapping[str, Any]) -> ModuleHandle:
        ...

    def detach(self, app: CoreApp, handle: ModuleHandle) -> None:
        ...
