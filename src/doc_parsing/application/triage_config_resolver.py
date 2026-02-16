from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    create_model,
    model_validator,
)

from doc_parsing.application.logging import LoggingConfig
from doc_parsing.infrastructure.triage.pypdf_inspector import PypdfInspectorConfig
from doc_parsing.infrastructure.triage.registry import TriagePolicyRegistry


@dataclass(frozen=True, slots=True)
class TriageCliConfig:
    triage: BaseModel
    inspection: PypdfInspectorConfig
    task_id: str
    document_id: str
    input_path: Path
    output_path: Path | None
    logging: LoggingConfig


class TriageConfigResolver:
    def __init__(self, registry: TriagePolicyRegistry) -> None:
        self._registry = registry

    def build_cli_model(self) -> type[BaseModel]:
        policy_union = self._build_policy_union()
        triage_model = create_model(
            "TriageConfig",
            __base__=_TriageSectionBase,
            policies=(list[policy_union], ...),
        )
        return create_model(
            "TriageCliConfig",
            __base__=_TriageCliBase,
            triage=(triage_model, ...),
            inspection=(PypdfInspectorConfig, PypdfInspectorConfig()),
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
        if logging_overrides:
            logging_raw = dict(raw.get("logging", {}))
            logging_raw.update(logging_overrides)
            raw["logging"] = logging_raw
        return type(model).model_validate(raw)

    def apply_overrides(self, model: BaseModel, *, overrides: list[str]) -> BaseModel:
        raw = model.model_dump()
        for entry in overrides:
            key, value = _parse_override(entry)
            if key == "triage":
                raise ValueError("--set must target a field, e.g. triage.policies")
            if key.startswith("triage."):
                triage_raw = dict(raw.get("triage", {}))
                triage_raw[key.removeprefix("triage.")] = value
                raw["triage"] = triage_raw
            elif key.startswith("inspection."):
                inspection_raw = dict(raw.get("inspection", {}))
                inspection_raw[key.removeprefix("inspection.")] = value
                raw["inspection"] = inspection_raw
            elif key.startswith("logging."):
                logging_raw = dict(raw.get("logging", {}))
                logging_raw[key.removeprefix("logging.")] = value
                raw["logging"] = logging_raw
            else:
                raw[key] = value
        return type(model).model_validate(raw)

    def _build_policy_union(self) -> Any:
        models = list(self._registry.config_models().values())
        if not models:
            raise ValueError("no triage policies registered")
        union_type = models[0]
        for model in models[1:]:
            union_type = union_type | model
        return Annotated[union_type, Field(discriminator="kind")]


class _TriageCliBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _TriageSectionBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _ensure_policies(self) -> _TriageSectionBase:
        policies = getattr(self, "policies", None)
        if policies is not None and not policies:
            raise ValueError("triage policies cannot be empty")
        return self


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
