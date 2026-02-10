import asyncio

from core.bootstrap import build_core
from core.contracts.services import TextComposer, TextComposeIn
from core.middleware.chain import MiddlewareChain
from core.middleware.idempotency_mw import make_idempotency_middleware
from core.middleware.idempotency_store import InMemoryIdempotencyStore
from core.middleware.logging_mw import logging_middleware
from core.registry.services import ServiceBinding, resolve_typed, service_key
from core.runtime.context import RuntimeContext
from core.services.executor import ServiceExecutor

from packages.providers.text_jinja2.provider import Jinja2TextComposer, Jinja2TextComposerConfig


async def main() -> None:
    app = build_core()

    store = InMemoryIdempotencyStore()
    chain = MiddlewareChain()
    chain.add(logging_middleware)
    chain.add(make_idempotency_middleware(store=store, ttl_seconds=300, lock_ttl_seconds=30))

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

    svc = resolve_typed(app.services, tenant_id, TextComposer)

    # Two calls with the same idempotency_key
    ctx1 = RuntimeContext.new(tenant_id=tenant_id, locale="ru")
    call1 = ctx1.to_service_call(timeout_ms=1000, max_attempts=1, idempotency_key="idem_123")

    res1 = await executor.call(
        service_key=service_key(TextComposer),
        call=call1,
        op_name="text_compose",
        fn=lambda: svc.compose(call1, TextComposeIn(locale="ru", template_key="hello", variables={"name": "Савин"})),
    )

    ctx2 = RuntimeContext.new(tenant_id=tenant_id, locale="ru")
    call2 = ctx2.to_service_call(timeout_ms=1000, max_attempts=1, idempotency_key="idem_123")

    res2 = await executor.call(
        service_key=service_key(TextComposer),
        call=call2,
        op_name="text_compose",
        fn=lambda: svc.compose(call2, TextComposeIn(locale="ru", template_key="hello", variables={"name": "Савин"})),
    )

    print("first:", res1.status, res1.data.text if res1.data else None)
    print("second:", res2.status, res2.data.text if res2.data else None)
    print("same object reused:", res1 is res2)


if __name__ == "__main__":
    asyncio.run(main())
