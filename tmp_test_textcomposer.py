import asyncio

from core.runtime.context import RuntimeContext
from core.contracts.services import TextComposeIn
from packages.providers.text_jinja2.provider import Jinja2TextComposer, Jinja2TextComposerConfig


async def main() -> None:
    cfg = Jinja2TextComposerConfig(
        templates={
            "hello": "Привет, {{ name }}! Заказ №{{ order_id }} принят."
        }
    )
    provider = Jinja2TextComposer(cfg)

    ctx = RuntimeContext.new(tenant_id="tenant_demo", locale="ru")
    call = ctx.to_service_call(timeout_ms=1000)

    res = await provider.compose(
        call,
        TextComposeIn(locale="ru", template_key="hello", variables={"name": "Савин", "order_id": 123}),
    )

    print("status:", res.status)
    print("text:", res.data.text if res.data else None)
    print("error:", res.error.code if res.error else None)


if __name__ == "__main__":
    asyncio.run(main())
