from __future__ import annotations

from dataclasses import dataclass

from .events.bus import EventBus
from .registry.services import ServiceRegistry
from .services.executor import ServiceExecutor


@dataclass(frozen=True)
class CoreApp:
    """
    Core runtime container (no IO/framework dependencies).
    """
    bus: EventBus
    services: ServiceRegistry
    executor: ServiceExecutor


def build_core() -> CoreApp:
    """
    Build core components.
    Providers/modules are attached outside core via runtime configuration.
    """
    bus = EventBus()
    services = ServiceRegistry()
    executor = ServiceExecutor(bus=bus, registry=services)
    return CoreApp(bus=bus, services=services, executor=executor)
