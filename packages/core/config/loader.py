from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol


@dataclass(frozen=True)
class TenantConfig:
    tenant_id: str
    locale: str = "ru"

    # service_key -> provider_name
    services: Mapping[str, str] = None  # type: ignore[assignment]

    # module_key -> module config blob (module decides schema)
    modules: Mapping[str, Mapping[str, Any]] = None  # type: ignore[assignment]


class TenantConfigStore(Protocol):
    """
    Core does not assume where configs live (db/redis/file).
    """

    async def get_tenant_config(self, tenant_id: str) -> TenantConfig:
        ...
