from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from pydantic import BaseModel

from doc_parsing.domain import PdfParser, PdfParserConfig, PdfParserFactory


@dataclass(frozen=True, slots=True)
class AdapterRegistration:
    name: str
    config_model: type[BaseModel]
    factory: PdfParserFactory

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("adapter name cannot be empty")


class ParserRegistry(PdfParserFactory):
    def __init__(self) -> None:
        self._factories: dict[str, Callable[[PdfParserConfig], PdfParser]] = {}
        self._adapters: dict[str, AdapterRegistration] = {}

    def register(
        self, name: str, factory: Callable[[PdfParserConfig], PdfParser]
    ) -> None:
        if not name.strip():
            raise ValueError("parser name cannot be empty")
        self._factories[name] = factory

    def create(self, config: PdfParserConfig) -> PdfParser:
        if config.name in self._adapters:
            return self._adapters[config.name].factory.create(config)
        try:
            factory = self._factories[config.name]
        except KeyError as exc:
            raise ValueError(f"unknown parser: {config.name}") from exc
        return factory(config)

    def available(self) -> Mapping[str, Callable[[PdfParserConfig], PdfParser]]:
        return dict(self._factories)

    def register_adapter(self, registration: AdapterRegistration) -> None:
        self._adapters[registration.name] = registration

    def config_models(self) -> Mapping[str, type[BaseModel]]:
        return {name: adapter.config_model for name, adapter in self._adapters.items()}
