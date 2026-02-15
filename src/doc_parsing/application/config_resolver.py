from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, create_model

from doc_parsing.application.logging import LoggingConfig
from doc_parsing.infrastructure.parsers.registry import ParserRegistry


@dataclass(frozen=True, slots=True)
class CliConfig:
    parser: BaseModel
    task_id: str
    document_id: str
    input_path: Path
    output_path: Path | None
    logging: LoggingConfig


class ConfigResolver:
    def __init__(self, registry: ParserRegistry) -> None:
        self._registry = registry

    def build_cli_model(self) -> type[BaseModel]:
        adapter_union = self._build_adapter_union()
        return create_model(
            "CliConfig",
            __base__=_CliConfigBase,
            parser=(adapter_union, ...),
            task_id=(str, "task-1"),
            document_id=(str, "doc-1"),
            input_path=(Path, ...),
            output_path=(Path | None, None),
            logging=(LoggingConfig, LoggingConfig()),
        )

    def parse(self, raw_config: dict[str, Any]) -> BaseModel:
        cli_model = self.build_cli_model()
        return TypeAdapter(cli_model).validate_python(raw_config)

    def apply_base_overrides(
        self,
        model: BaseModel,
        *,
        input_path: Path | None,
        output_path: Path | None,
        task_id: str | None,
        document_id: str | None,
        parser_kind: str | None,
        logging_overrides: dict[str, Any] | None = None,
    ) -> BaseModel:
        raw = model.model_dump()
        if input_path is not None:
            raw["input_path"] = input_path
        if output_path is not None:
            raw["output_path"] = output_path
        if task_id is not None:
            raw["task_id"] = task_id
        if document_id is not None:
            raw["document_id"] = document_id
        if parser_kind is not None:
            raw["parser"] = {"kind": parser_kind}
        if logging_overrides:
            logging_raw = dict(raw.get("logging", {}))
            logging_raw.update(logging_overrides)
            raw["logging"] = logging_raw
        return type(model).model_validate(raw)

    def apply_overrides(self, model: BaseModel, *, overrides: list[str]) -> BaseModel:
        raw = model.model_dump()
        for entry in overrides:
            key, value = _parse_override(entry)
            if key == "parser":
                raise ValueError("--set must target a field, e.g. parser.kind")
            if key.startswith("parser."):
                parser_raw = dict(raw.get("parser", {}))
                parser_raw[key.removeprefix("parser.")] = value
                raw["parser"] = parser_raw
            elif key.startswith("logging."):
                logging_raw = dict(raw.get("logging", {}))
                logging_raw[key.removeprefix("logging.")] = value
                raw["logging"] = logging_raw
            else:
                raw[key] = value
        return type(model).model_validate(raw)

    def _build_adapter_union(self) -> Any:
        models = list(self._registry.config_models().values())
        if not models:
            raise ValueError("no adapters registered")
        union_type = models[0]
        for model in models[1:]:
            union_type = union_type | model
        return Annotated[union_type, Field(discriminator="kind")]


class _CliConfigBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _parse_override(entry: str) -> tuple[str, Any]:
    if "=" not in entry:
        raise ValueError("--set must be in the form key=value")
    key, raw_value = entry.split("=", 1)
    key = key.strip()
    raw_value = raw_value.strip()
    if not key:
        raise ValueError("--set key cannot be empty")
    return key, _coerce_value(raw_value)


def _coerce_value(raw: str) -> Any:
    lowered = raw.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none"}:
        return None
    try:
        if "." in raw:
            return float(raw)
        return int(raw)
    except ValueError:
        pass
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw
