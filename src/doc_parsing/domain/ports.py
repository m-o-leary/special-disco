from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class PdfParserConfig:
    name: str
    options: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("parser name cannot be empty")


@runtime_checkable
class PdfParser(Protocol):
    def parse(self, file_path: Path) -> str: ...


@runtime_checkable
class PdfParserFactory(Protocol):
    def create(self, config: PdfParserConfig) -> PdfParser: ...
