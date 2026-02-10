from __future__ import annotations

import time
from typing import Awaitable, Callable, TypeVar

from ..contracts.results import ServiceResult
from .types import Next, ServiceOp

T = TypeVar("T")


async def logging_middleware(op: ServiceOp[T], nxt: Next[T]) -> ServiceResult[T]:
    started = int(time.time() * 1000)
    print(f"[mw] start {op.op_name} tenant={op.call.tenant_id} req={op.call.request_id}")

    res = await nxt()

    finished = int(time.time() * 1000)
    dur = finished - started
    print(f"[mw] end {op.op_name} status={res.status} ms={dur} provider={res.meta.provider_name}")

    return res
