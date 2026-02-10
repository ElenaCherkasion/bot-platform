from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Protocol, Type, TypeVar, cast

T = TypeVar("T")


class ServiceNotConfigured(Exception):
    pass


class ServiceNotRegistered(Exception):
    pass


@dataclass(frozen=True)
class ServiceBinding:
    """
    Binding: service interface -> provider instance name for a tenant.
    Example: TextComposer -> "jinja2_v1"
    """
    provider: str


class ServiceRegistry:
    """
    In-memory registry.
    Core does not assume where config is stored.
    """

    def __init__(self) -> None:
        # key: provider_name -> provider instance (object with async methods)
        self._providers: Dict[str, Any] = {}

        # key: tenant_id -> { service_key -> binding }
        self._bindings: Dict[str, Dict[str, ServiceBinding]] = {}

    def register_provider(self, name: str, provider: Any) -> None:
        """
        Register a provider instance by name.
        Providers live in external modules, core only stores references.
        """
        self._providers[name] = provider

    def set_tenant_bindings(self, tenant_id: str, bindings: Mapping[str, ServiceBinding]) -> None:
        """
        Apply runtime bindings for a tenant (can be refreshed without restart).
        """
        self._bindings[tenant_id] = dict(bindings)

    def resolve(self, tenant_id: str, service_key: str) -> Any:
        """
        Resolve provider for a given tenant and service key.
        """
        tenant_map = self._bindings.get(tenant_id)
        if not tenant_map or service_key not in tenant_map:
            raise ServiceNotConfigured(f"Service '{service_key}' not configured for tenant '{tenant_id}'")

        binding = tenant_map[service_key]
        provider = self._providers.get(binding.provider)
        if provider is None:
            raise ServiceNotRegistered(f"Provider '{binding.provider}' not registered")

        return provider


# --- Helper to keep call sites typed (optional) ---

def service_key(t: Type[Any]) -> str:
    """
    Stable service key based on interface name.
    (Can be replaced by explicit keys later.)
    """
    return t.__name__


P = TypeVar("P")


def resolve_typed(registry: ServiceRegistry, tenant_id: str, proto: Type[P]) -> P:
    return cast(P, registry.resolve(tenant_id, service_key(proto)))
