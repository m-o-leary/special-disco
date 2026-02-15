from __future__ import annotations

import io
from typing import Any, cast

import pytest
from pydantic import TypeAdapter, ValidationError

from doc_parsing.cli import (
    _apply_overrides,
    _build_adapter_union,
    _build_cli_model,
    _load_yaml_config,
)
from doc_parsing.infrastructure import (
    AdapterRegistration,
    DoclingConfig,
    LazyDoclingPdfParserFactory,
    MockConfig,
    MockPdfParserFactory,
    ParserRegistry,
)


def _registry() -> ParserRegistry:
    registry = ParserRegistry()
    registry.register_adapter(
        AdapterRegistration(
            name="docling",
            config_model=DoclingConfig,
            factory=LazyDoclingPdfParserFactory(),
        )
    )
    registry.register_adapter(
        AdapterRegistration(
            name="mock",
            config_model=MockConfig,
            factory=MockPdfParserFactory(),
        )
    )
    return registry


def test_docling_yaml_round_trip() -> None:
    registry = _registry()
    adapter_union = _build_adapter_union(registry)
    cli_model = _build_cli_model(adapter_union)

    raw = {
        "parser": {"kind": "docling", "picture_description": True},
        "input_path": "/tmp/sample.pdf",
    }

    config = TypeAdapter(cli_model).validate_python(raw)
    parser = cast(Any, config).parser

    assert isinstance(parser, DoclingConfig)
    assert parser.picture_description is True


def test_unknown_adapter_rejected() -> None:
    registry = _registry()
    adapter_union = _build_adapter_union(registry)
    cli_model = _build_cli_model(adapter_union)

    raw = {"parser": {"kind": "missing"}, "input_path": "/tmp/sample.pdf"}

    with pytest.raises(ValidationError):
        TypeAdapter(cli_model).validate_python(raw)


def test_flags_override_yaml() -> None:
    registry = _registry()
    adapter_union = _build_adapter_union(registry)
    cli_model = _build_cli_model(adapter_union)

    raw = {
        "parser": {"kind": "docling", "picture_description": False},
        "input_path": "/tmp/sample.pdf",
    }
    config = TypeAdapter(cli_model).validate_python(raw)

    updated = _apply_overrides(
        config,
        input_path=None,
        output_path=None,
        task_id=None,
        document_id=None,
        parser_kind=None,
        parser_overrides={"picture_description": True},
    )

    updated_parser = cast(Any, updated).parser
    assert updated_parser.picture_description is True


def test_load_yaml_from_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = """
parser:
  kind: docling
  picture_description: true
input_path: /tmp/sample.pdf
"""
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))

    data = _load_yaml_config("-")

    assert data is not None
    assert data["parser"]["kind"] == "docling"


def test_open_closed_new_adapter() -> None:
    from typing import Literal

    from pydantic import BaseModel, ConfigDict, Field

    class FakeConfig(BaseModel):
        model_config = ConfigDict(extra="forbid")
        kind: Literal["fake"] = Field(default="fake")

    registry = ParserRegistry()
    registry.register_adapter(
        AdapterRegistration(
            name="fake",
            config_model=FakeConfig,
            factory=MockPdfParserFactory(),
        )
    )

    adapter_union = _build_adapter_union(registry)
    cli_model = _build_cli_model(adapter_union)

    raw = {"parser": {"kind": "fake"}, "input_path": "/tmp/sample.pdf"}

    config = TypeAdapter(cli_model).validate_python(raw)
    parser = cast(Any, config).parser

    assert parser.kind == "fake"
