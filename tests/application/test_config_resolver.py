from __future__ import annotations

import io
from typing import Any, Literal, cast

import pytest
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from doc_parsing.application.config_resolver import ConfigResolver
from doc_parsing.infrastructure import AdapterRegistration, ParserRegistry


class FakeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["fake"] = Field(default="fake")
    flag: bool = False


class FakeFactory:
    config_model = FakeConfig

    def create(self, config):  # pragma: no cover - not used
        raise NotImplementedError


def _registry() -> ParserRegistry:
    registry = ParserRegistry()
    registry.register_adapter(
        AdapterRegistration(
            name="fake",
            config_model=FakeConfig,
            factory=FakeFactory(),
        )
    )
    return registry


def test_dynamic_union_and_validation() -> None:
    resolver = ConfigResolver(_registry())
    raw = {"parser": {"kind": "fake", "flag": True}, "input_path": "/tmp/a.pdf"}

    config = resolver.parse(raw)
    parser = cast(Any, config).parser

    assert isinstance(parser, FakeConfig)
    assert parser.flag is True


def test_unknown_adapter_rejected() -> None:
    resolver = ConfigResolver(_registry())
    cli_model = resolver.build_cli_model()

    raw = {"parser": {"kind": "missing"}, "input_path": "/tmp/a.pdf"}

    with pytest.raises(ValidationError):
        TypeAdapter(cli_model).validate_python(raw)


def test_set_overrides_parser() -> None:
    resolver = ConfigResolver(_registry())
    raw = {"parser": {"kind": "fake"}, "input_path": "/tmp/a.pdf"}
    config = resolver.parse(raw)

    updated = resolver.apply_overrides(
        config,
        overrides=["parser.flag=true"],
    )

    parser = cast(Any, updated).parser
    assert parser.flag is True


def test_set_overrides_top_level() -> None:
    resolver = ConfigResolver(_registry())
    raw = {"parser": {"kind": "fake"}, "input_path": "/tmp/a.pdf"}
    config = resolver.parse(raw)

    updated = resolver.apply_overrides(
        config,
        overrides=["task_id=task-9"],
    )

    assert cast(Any, updated).task_id == "task-9"


def test_set_overrides_logging() -> None:
    resolver = ConfigResolver(_registry())
    raw = {"parser": {"kind": "fake"}, "input_path": "/tmp/a.pdf"}
    config = resolver.parse(raw)

    updated = resolver.apply_overrides(
        config,
        overrides=["logging.level=DEBUG"],
    )

    logging_cfg = cast(Any, updated).logging
    assert logging_cfg.level == "DEBUG"


def test_load_yaml_from_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = """
parser:
  kind: fake
input_path: /tmp/a.pdf
"""
    monkeypatch.setattr("sys.stdin", io.StringIO(payload))
    import doc_parsing.cli as cli

    data = cli._load_yaml_config("-")

    assert data is not None
    assert data["parser"]["kind"] == "fake"
