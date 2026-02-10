import asyncio

from core.bootstrap import build_core
from core.registry.services import ServiceBinding, resolve_typed, service_key
from core.runtime.context import RuntimeContext
from core.contracts.services import TextComposer, TextComposeIn

from packages.providers.text_jinja2.provider import Jinja2TextComposer, Jinja2TextComposerConfig


async def main() -> None:
    app = build_core()

    provider = Jinja2TextComposer(
        Jinja2TextComposerConfig(
            templates={
                "hello": "Привет, {{ name }}! Заказ №{{ order_id }} принят."
            }
        ),
        provider_name="jinja2_v1",
    )

    app.services.register_provider("jinja2_v1", provider)

    tenant_id = "tenant_demo"
    app.services.set_tenant_bindings(
        tenant_id,
        {
            service_key(TextComposer): ServiceBinding(provider="jinja2_v1"),
        },
    )

    ctx = RuntimeContext.new(tenant_id=tenant_id, locale="ru")
    call = ctx.to_service_call(timeout_ms=1000)

    text_composer = resolve_typed(app.services, tenant_id, TextComposer)

    res = await text_composer.compose(
        call,
        TextComposeIn(locale="ru", template_key="hello", variables={"name": "Савин", "order_id": 123}),
    )

    print("status:", res.status)
    print("text:", res.data.text if res.data else None)
    print("provider:", res.meta.provider_name)
    print("error:", res.error.code if res.error else None)


if __name__ == "__main__":
    asyncio.run(main())
