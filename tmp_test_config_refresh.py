import asyncio

from core.bootstrap import build_core
from core.contracts.services import TextComposer, TextComposeIn
from core.events.types import Subscription
from core.modules.manager import ModuleManager
from core.registry.services import resolve_typed, service_key, ServiceNotConfigured
from core.runtime.config_manager import ConfigManager
from core.runtime.context import RuntimeContext
from core.services.executor import ServiceExecutor
from core.middleware.chain import MiddlewareChain
from core.middleware.logging_mw import logging_middleware
from core.services.deferred_store import InMemoryDeferredStore

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

    # 1) enable module via config
    cm.apply_tenant_config(
        tenant_id=tenant_id,
        trace_id="trc_1",
        request_id="req_1",
        services={},  # module binds TextComposer in attach (MVP approach)
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

    # 2) disable module via config refresh (also clears service bindings)
    cm.apply_tenant_config(
        tenant_id=tenant_id,
        trace_id="trc_2",
        request_id="req_2",
        services={},   # clearing bindings is expected here
        modules={},    # detach modules + unsubscribe
    )

    await asyncio.sleep(0.05)

    # After disable: service may be not configured -> expect exception.
    try:
        svc2 = resolve_typed(app.services, tenant_id, TextComposer)
        ctx2 = RuntimeContext.new(tenant_id=tenant_id, locale="ru")
        call2 = ctx2.to_service_call(timeout_ms=1000, max_attempts=1)

        res2 = await executor.call(
            service_key=service_key(TextComposer),
            call=call2,
            op_name="text_compose",
            fn=lambda: svc2.compose(call2, TextComposeIn(locale="ru", template_key="hello", variables={"name": "Савин"})),
        )
        print("after disable (unexpected):", res2.status, res2.data.text if res2.data else None)

    except ServiceNotConfigured as exc:
        print("after disable (expected):", str(exc))

    print("NOTE: after disable there should be NO [module:text_templates] lines printed")


if __name__ == "__main__":
    asyncio.run(main())
