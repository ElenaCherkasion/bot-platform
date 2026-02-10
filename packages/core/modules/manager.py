from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping

from ..bootstrap import CoreApp
from .contracts import CoreModule, ModuleHandle


@dataclass
class ModuleManager:
    """
    Attaches/detaches modules per tenant and tracks handles.
    """
    app: CoreApp
    modules: Dict[str, CoreModule] = field(default_factory=dict)

    # tenant_id -> module_key -> handle
    _handles: Dict[str, Dict[str, ModuleHandle]] = field(default_factory=dict)

    def register(self, module: CoreModule) -> None:
        self.modules[module.module_key] = module

    def attach(self, *, tenant_id: str, module_key: str, cfg: Mapping[str, Any]) -> None:
        mod = self.modules[module_key]
        handle = mod.attach(self.app, tenant_id=tenant_id, cfg=cfg)

        self._handles.setdefault(tenant_id, {})[module_key] = handle

    def detach(self, *, tenant_id: str, module_key: str) -> None:
        handle = self._handles.get(tenant_id, {}).get(module_key)
        if not handle:
            return

        mod = self.modules[module_key]
        mod.detach(self.app, handle)

        self._handles[tenant_id].pop(module_key, None)
        if not self._handles[tenant_id]:
            self._handles.pop(tenant_id, None)

    def refresh(self, *, tenant_id: str, desired: Mapping[str, Mapping[str, Any]]) -> None:
        """
        desired: module_key -> cfg
        - detach missing
        - attach new
        - reattach changed (simple strategy)
        """
        current = self._handles.get(tenant_id, {})

        # detach modules not desired anymore
        for mk in list(current.keys()):
            if mk not in desired:
                self.detach(tenant_id=tenant_id, module_key=mk)

        # attach / reattach
        for mk, cfg in desired.items():
            if mk not in self.modules:
                continue

            if mk not in current:
                self.attach(tenant_id=tenant_id, module_key=mk, cfg=cfg)
            else:
                # naive: always reattach when refresh called (later: compare cfg hash)
                self.detach(tenant_id=tenant_id, module_key=mk)
                self.attach(tenant_id=tenant_id, module_key=mk, cfg=cfg)
