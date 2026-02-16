from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel

from doc_parsing.domain import TriagePolicy

from .entrypoints import load_entrypoints
from .registration import TriagePolicyRegistration


class TriagePolicyRegistry:
    def __init__(self) -> None:
        self._policies: dict[str, TriagePolicyRegistration] = {}

    def register_adapter(self, registration: TriagePolicyRegistration) -> None:
        self._policies[registration.name] = registration

    def register_many(self, registrations: list[TriagePolicyRegistration]) -> None:
        for registration in registrations:
            self.register_adapter(registration)

    def load_from_entrypoints(self) -> None:
        self.register_many(load_entrypoints())

    def config_models(self) -> Mapping[str, type[BaseModel]]:
        return {name: reg.config_model for name, reg in self._policies.items()}

    def create(self, config: BaseModel) -> TriagePolicy:
        kind = getattr(config, "kind", None)
        if not kind:
            raise ValueError("policy kind is required")
        if kind not in self._policies:
            raise ValueError(f"unknown policy: {kind}")
        return self._policies[kind].factory(config)
