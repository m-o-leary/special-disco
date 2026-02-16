from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel

from doc_parsing.domain import TriagePolicy


@dataclass(frozen=True, slots=True)
class TriagePolicyRegistration:
    name: str
    config_model: type[BaseModel]
    factory: Callable[[BaseModel], TriagePolicy]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("policy name cannot be empty")
