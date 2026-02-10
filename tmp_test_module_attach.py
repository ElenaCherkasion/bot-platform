import asyncio

from core.bootstrap import build_core
from core.contracts.services import TextComposer, TextComposeIn
from core.registry.services import resolve_typed, service_key
from core.runtime.context import RuntimeContext

from packages.modules.text_templates.module import TextTemplatesModuleConfig, attach


async def main() -> None:
    app = build_core()

    tenant_id = "tenant_demo"
    attach(
        app,
        tenant_id=tenant_id,
        cfg=TextTemplatesModuleConfig(
            provider_name="jinja2_v1",
            templates={"hello": "Привет, {{ name }}!"},
        ),
    )

    ctx = RuntimeContext.new(tenant_id=tenant_id, locale="ru")
    call = ctx.to_service_call(timeout_ms=1000, max_attempts=1)

    svc = resolve_typed(app.services, tenant_id, TextComposer)

    res = await app.executor.call(
        service_key=service_key(TextComposer),
        call=call,
        op_name="text_compose",
        fn=lambda: svc.compose(call, TextComposeIn(locale="ru", template_key="hello", variables={"name": "Савин"})),
    )

    print("final:", res.status, res.data.text if res.data else None)


if __name__ == "__main__":
    asyncio.run(main())
