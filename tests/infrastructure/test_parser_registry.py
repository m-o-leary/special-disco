from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict, Field

from doc_parsing.domain import PdfParser, PdfParserConfig, PdfParserFactory
from doc_parsing.infrastructure import AdapterRegistration, ParserRegistry


class FakeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = Field(default="fake")


class FakeParser(PdfParser):
    def parse(self, file_path: Path) -> str:
        return "# ok"


class FakeFactory(PdfParserFactory):
    config_model = FakeConfig

    def create(self, config: PdfParserConfig) -> PdfParser:
        return FakeParser()


def test_registry_returns_parser() -> None:
    registry = ParserRegistry()
    registry.register_adapter(
        AdapterRegistration(
            name="fake",
            config_model=FakeConfig,
            factory=FakeFactory(),
        )
    )

    parser = registry.create(PdfParserConfig(name="fake"))

    assert parser.parse(Path("/tmp/sample.pdf")) == "# ok"


def test_registry_rejects_unknown_parser() -> None:
    registry = ParserRegistry()

    with pytest.raises(ValueError):
        registry.create(PdfParserConfig(name="missing"))


def test_registry_exposes_config_models() -> None:
    registry = ParserRegistry()
    registry.register_adapter(
        AdapterRegistration(
            name="fake",
            config_model=FakeConfig,
            factory=FakeFactory(),
        )
    )

    models = registry.config_models()

    assert models["fake"] is FakeConfig
