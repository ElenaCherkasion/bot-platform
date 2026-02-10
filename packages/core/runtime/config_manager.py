from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Mapping

from ..bootstrap import CoreApp
from ..contracts.events import EventEnvelope
from ..registry.services import ServiceBinding
from ..modules.manager import ModuleManager


def _now_ms() -> int:
    return int(time.time() * 1000)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class ConfigManager:
    app: CoreApp
    modules: ModuleManager

    def apply_tenant_config(
        self,
        *,
        tenant_id: str,
        trace_id: str,
        request_id: str,
        services: Mapping[str, str],
        modules: Mapping[str, Mapping[str, Any]],
    ) -> None:
        """
        Apply runtime config without restart.

        services: service_key -> provider_name
        modules: module_key -> module_cfg_blob
        """
        # 1) apply service bindings
        self.app.services.set_tenant_bindings(
            tenant_id,
            {k: ServiceBinding(provider=v) for k, v in services.items()},
        )

        # 2) refresh modules
        self.modules.refresh(tenant_id=tenant_id, desired=modules)

        # 3) emit config event
        evt = EventEnvelope(
            name="config.tenant_updated",
            kind="system",
            tenant_id=tenant_id,
            event_id=_new_id("evt"),
            trace_id=trace_id,
            occurred_at_ms=_now_ms(),
            request_id=request_id,
            payload={
                "services": dict(services),
                "modules": {k: dict(v) for k, v in modules.items()},
            },
        )
        # fire and forget is ok here (sync method), caller can await publish if needed
        # we keep it simple for now:
        import asyncio
        asyncio.get_event_loop().create_task(self.app.bus.publish(evt))
