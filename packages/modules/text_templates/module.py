from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from core.bootstrap import CoreApp
from core.events.types import Subscription
from core.modules.contracts import CoreModule, ModuleHandle

from packages.providers.text_jinja2.provider import Jinja2TextComposer, Jinja2TextComposerConfig


@dataclass(frozen=True)
class TextTemplatesModuleConfig:
    provider_name: str
    templates: Mapping[str, str]


async def _log_service_event(event) -> None:
    print("[module:text_templates]", event.name, event.payload)


class TextTemplatesModule(CoreModule):
    module_key = "text_templates"

    def attach(self, app: CoreApp, *, tenant_id: str, cfg: Mapping[str, Any]) -> ModuleHandle:
        typed = TextTemplatesModuleConfig(
            provider_name=str(cfg.get("provider_name", "jinja2_v1")),
            templates=dict(cfg.get("templates", {})),
        )

        handle = ModuleHandle(module_key=self.module_key, tenant_id=tenant_id)

        # 1) register provider instance
        provider = Jinja2TextComposer(
            Jinja2TextComposerConfig(templates=typed.templates),
            provider_name=typed.provider_name,
        )
        app.services.register_provider(typed.provider_name, provider)
        handle.provider_names.append(typed.provider_name)

        # 2) module subscriptions (optional)
        s1 = Subscription(name="service.text_compose.ok", handler=_log_service_event, priority=50)
        s2 = Subscription(name="service.text_compose.error", handler=_log_service_event, priority=50)

        app.bus.subscribe(s1)
        app.bus.subscribe(s2)

        handle.subscriptions.extend([s1, s2])
        return handle

    def detach(self, app: CoreApp, handle: ModuleHandle) -> None:
        for sub in handle.subscriptions:
            app.bus.unsubscribe(sub.name, sub.handler)
