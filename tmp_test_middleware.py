import asyncio

from core.bootstrap import build_core
from core.contracts.services import TextComposer, TextComposeIn
from core.middleware.chain import MiddlewareChain
from core.middleware.logging_mw import logging_middleware
from core.registry.services import ServiceBinding, resolve_typed, service_key
from core.runtime.context import RuntimeContext
from core.services.executor import ServiceExecutor

from packages.providers.text_jinja2.provider import Jinja2TextComposer, Jinja2TextComposerConfig


async def main() -> None:
    app = build_core()

    # build middleware chain
    chain = MiddlewareChain()
    chain.add(logging_middleware)

    # create executor with chain (do not mutate frozen CoreApp)
    executor = ServiceExecutor(bus=app.bus, registry=app.services, chain=chain)

    provider = Jinja2TextComposer(
        Jinja2TextComposerConfig(templates={"hello": "Привет, {{ name }}!"}),
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

    svc = resolve_typed(app.services, tenant_id, TextComposer)

    res = await executor.call(
        service_key=service_key(TextComposer),
        call=call,
        op_name="text_compose",
        fn=lambda: svc.compose(call, TextComposeIn(locale="ru", template_key="hello", variables={"name": "Савин"})),
    )

    print("final:", res.status, res.data.text if res.data else None)


if __name__ == "__main__":
    asyncio.run(main())
