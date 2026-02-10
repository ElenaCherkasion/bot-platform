import asyncio

from core.bootstrap import build_core
from core.contracts.services import TextComposer, TextComposeIn
from core.events.types import Subscription
from core.middleware.chain import MiddlewareChain
from core.middleware.logging_mw import logging_middleware
from core.modules.manager import ModuleManager
from core.registry.services import resolve_typed, service_key, ServiceNotConfigured
from core.runtime.config_manager import ConfigManager
from core.runtime.context import RuntimeContext
from core.services.deferred_store import InMemoryDeferredStore
from core.services.executor import ServiceExecutor

from packages.modules.text_templates.module import TextTemplatesModule


async def on_config(event):
    print("[config]", event.payload)


async def main() -> None:
    app = build_core()

    chain = MiddlewareChain()
    chain.add(logging_middleware)
    executor = ServiceExecutor(bus=app.bus, registry=app.services, chain=chain, deferred=InMemoryDeferredStore())

    app.bus.subscribe(Subscription(name="config.tenant_updated", handler=on_config, priority=10))

    mm = ModuleManager(app=app)
    mm.register(TextTemplatesModule())

    cm = ConfigManager(app=app, modules=mm)

    tenant_id = "tenant_demo"

    # 1) Enable module AND enable service binding via config
    cm.apply_tenant_config(
        tenant_id=tenant_id,
        trace_id="trc_1",
        request_id="req_1",
        services={
            service_key(TextComposer): "jinja2_v1",   # <-- bindings now come from config
        },
        modules={
            "text_templates": {
                "provider_name": "jinja2_v1",
                "templates": {"hello": "Привет, {{ name }}!"},
            }
        },
    )

    await asyncio.sleep(0.05)

    ctx = RuntimeContext.new(tenant_id=tenant_id, locale="ru")
    call = ctx.to_service_call(timeout_ms=1000, max_attempts=1)

    svc = resolve_typed(app.services, tenant_id, TextComposer)
    res1 = await executor.call(
        service_key=service_key(TextComposer),
        call=call,
        op_name="text_compose",
        fn=lambda: svc.compose(call, TextComposeIn(locale="ru", template_key="hello", variables={"name": "Савин"})),
    )
    print("enabled:", res1.status, res1.data.text if res1.data else None)

    # 2) Disable MODULE only, keep service binding
    cm.apply_tenant_config(
        tenant_id=tenant_id,
        trace_id="trc_2",
        request_id="req_2",
        services={
            service_key(TextComposer): "jinja2_v1",   # <-- binding stays
        },
        modules={},  # detach module + unsubscribe
    )

    await asyncio.sleep(0.05)

    ctx2 = RuntimeContext.new(tenant_id=tenant_id, locale="ru")
    call2 = ctx2.to_service_call(timeout_ms=1000, max_attempts=1)

    svc2 = resolve_typed(app.services, tenant_id, TextComposer)
    res2 = await executor.call(
        service_key=service_key(TextComposer),
        call=call2,
        op_name="text_compose",
        fn=lambda: svc2.compose(call2, TextComposeIn(locale="ru", template_key="hello", variables={"name": "Савин"})),
    )
    print("after module disable (service still works):", res2.status, res2.data.text if res2.data else None)
    print("NOTE: there should be NO [module:text_templates] lines after module disable")

    # 3) Disable SERVICE binding too
    cm.apply_tenant_config(
        tenant_id=tenant_id,
        trace_id="trc_3",
        request_id="req_3",
        services={},   # <-- now service is disabled
        modules={},
    )

    await asyncio.sleep(0.05)

    try:
        resolve_typed(app.services, tenant_id, TextComposer)
        print("unexpected: TextComposer still configured")
    except ServiceNotConfigured as exc:
        print("after service disable (expected):", str(exc))


if __name__ == "__main__":
    asyncio.run(main())
