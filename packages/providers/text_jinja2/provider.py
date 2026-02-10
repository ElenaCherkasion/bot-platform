from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Mapping

from jinja2 import Environment, StrictUndefined

from core.contracts.results import ErrorInfo, ResultMeta, ServiceResult
from core.contracts.services import ServiceCall, TextComposeIn, TextComposeOut


@dataclass
class Jinja2TextComposerConfig:
    templates: Mapping[str, str]


class Jinja2TextComposer:
    """
    Deterministic TextComposer provider based on Jinja2 templates.
    No external IO. Safe for core usage through registry.
    """

    def __init__(self, cfg: Jinja2TextComposerConfig, provider_name: str = "jinja2_v1") -> None:
        self._cfg = cfg
        self._provider_name = provider_name
        self._env = Environment(undefined=StrictUndefined, autoescape=False)

    async def compose(self, call: ServiceCall, inp: TextComposeIn) -> ServiceResult[TextComposeOut]:
        started = int(time.time() * 1000)

        meta = ResultMeta(
            request_id=call.request_id,
            tenant_id=call.tenant_id,
            trace_id=call.trace_id,
            started_at_ms=started,
            provider_name=self._provider_name,
            attempt=1,
            idempotency_key=call.idempotency_key,
            tags=call.tags,
        )

        try:
            tpl_src = self._cfg.templates.get(inp.template_key)
            if not tpl_src:
                return ServiceResult(
                    status="error",
                    meta=meta,
                    error=ErrorInfo(
                        code="template_not_found",
                        message=f"Template '{inp.template_key}' not found",
                        retryable=False,
                    ),
                )

            template = self._env.from_string(tpl_src)
            text = template.render(**dict(inp.variables))

            finished = int(time.time() * 1000)
            meta2 = ResultMeta(
                **{**meta.__dict__, "finished_at_ms": finished}
            )

            return ServiceResult(
                status="ok",
                meta=meta2,
                data=TextComposeOut(text=text, format="plain"),
            )

        except Exception as exc:
            finished = int(time.time() * 1000)
            meta2 = ResultMeta(
                **{**meta.__dict__, "finished_at_ms": finished}
            )

            return ServiceResult(
                status="error",
                meta=meta2,
                error=ErrorInfo(
                    code="render_failed",
                    message=str(exc),
                    retryable=False,
                ),
            )
