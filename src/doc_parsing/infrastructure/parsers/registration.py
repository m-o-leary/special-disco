from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from doc_parsing.domain import PdfParserFactory


@dataclass(frozen=True, slots=True)
class AdapterRegistration:
    name: str
    config_model: type[BaseModel]
    factory: PdfParserFactory

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("adapter name cannot be empty")
