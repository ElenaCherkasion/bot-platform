import asyncio

from core.bootstrap import build_core
from core.contracts.services import TextComposer, TextComposeIn
from core.events.types import Subscription
from core.registry.services import ServiceBinding, resolve_typed, service_key
from core.runtime.context import RuntimeContext

from packages.providers.text_jinja2.provider import Jinja2TextComposer, Jinja2TextComposerConfig


async def log_service_event(event):
    print("[svc-event]", event.name, event.payload)


async def main() -> None:
    app = build_core()

    # subscribe to all 3 possible statuses we use in executor
    app.bus.subscribe(Subscription(name="service.text_compose.ok", handler=log_service_event, priority=10))
    app.bus.subscribe(Subscription(name="service.text_compose.error", handler=log_service_event, priority=10))
    app.bus.subscribe(Subscription(name="service.text_compose.deferred", handler=log_service_event, priority=10))
    app.bus.subscribe(Subscription(name="service.text_compose.partial", handler=log_service_event, priority=10))

    # provider + tenant bindings
    provider = Jinja2TextComposer(
        Jinja2TextComposerConfig(
            templates={"hello": "Привет, {{ name }}! Заказ №{{ order_id }} принят."}
        ),
        provider_name="jinja2_v1",
    )
    app.services.register_provider("jinja2_v1", provider)

    tenant_id = "tenant_demo"
    app.services.set_tenant_bindings(
        tenant_id,
        {service_key(TextComposer): ServiceBinding(provider="jinja2_v1")},
    )

    ctx = RuntimeContext.new(tenant_id=tenant_id, locale="ru")
    call = ctx.to_service_call(timeout_ms=1000, max_attempts=1)

    # resolve typed service, but call via executor
    text_composer = resolve_typed(app.services, tenant_id, TextComposer)

    res = await app.executor.call(
        service_key=service_key(TextComposer),
        call=call,
        op_name="text_compose",
        fn=lambda: text_composer.compose(call, TextComposeIn(locale="ru", template_key="hello", variables={"name": "Савин", "order_id": 123})),
    )

    print("status:", res.status)
    print("text:", res.data.text if res.data else None)


if __name__ == "__main__":
    asyncio.run(main())
