from __future__ import annotations

import importlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Protocol, cast

import typer
import yaml
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, create_model
from rich.console import Console
from rich.panel import Panel

from doc_parsing.application import ParsePdfToMarkdown, ParsePdfToMarkdownInput
from doc_parsing.domain import (
    DocumentId,
    PdfParserConfig,
    PdfParserFactory,
    TaskId,
)
from doc_parsing.infrastructure import (
    AdapterRegistration,
    DoclingConfig,
    LazyDoclingPdfParserFactory,
    MockConfig,
    MockPdfParserFactory,
    ParserRegistry,
)

app = typer.Typer(add_completion=False)
console = Console()

CONFIG_OPT = typer.Option(None, "--config", "-c")
INPUT_OPT = typer.Option(None, "--input", "-i")
OUTPUT_OPT = typer.Option(None, "--output", "-o")
PARSER_OPT = typer.Option(None, "--parser", "-p")
OPTIONS_OPT = typer.Option(None, "--options", help="JSON object")
FACTORY_OPT = typer.Option(
    None,
    "--factory",
    help="Factory import path: 'module:attribute'",
)
TASK_ID_OPT = typer.Option(None, "--task-id")
DOCUMENT_ID_OPT = typer.Option(None, "--document-id")
DOCLING_PIC_DESC_OPT = typer.Option(
    None,
    "--docling-picture-description/--no-docling-picture-description",
)
DOCLING_PIC_PROMPT_OPT = typer.Option(None, "--docling-picture-prompt")
DOCLING_IMAGES_SCALE_OPT = typer.Option(None, "--docling-images-scale")
DOCLING_GEN_PIC_OPT = typer.Option(
    None,
    "--docling-generate-picture-images/--no-docling-generate-picture-images",
)


@dataclass(frozen=True, slots=True)
class _LoadedFactory:
    factory: PdfParserFactory
    config_model: type[BaseModel]


class _ModuleLoadError(ValueError):
    pass


class _CliConfigBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _CliConfigProtocol(Protocol):
    parser: BaseModel
    input_path: Path
    output_path: Path | None
    task_id: str
    document_id: str


def _load_factory(factory_path: str) -> _LoadedFactory:
    if ":" not in factory_path:
        raise _ModuleLoadError("factory must be in the form 'module:attribute'")

    module_name, attr_name = factory_path.split(":", 1)
    module = importlib.import_module(module_name)
    attr = getattr(module, attr_name, None)
    if attr is None:
        raise _ModuleLoadError(f"factory attribute not found: {factory_path}")

    if isinstance(attr, PdfParserFactory):
        config_model = getattr(attr, "config_model", None)
        if not isinstance(config_model, type) or not issubclass(
            config_model, BaseModel
        ):
            raise _ModuleLoadError("factory must expose config_model: BaseModel type")
        return _LoadedFactory(factory=attr, config_model=config_model)

    if isinstance(attr, type) and issubclass(attr, PdfParserFactory):
        instance = attr()
        config_model = getattr(instance, "config_model", None)
        if not isinstance(config_model, type) or not issubclass(
            config_model, BaseModel
        ):
            raise _ModuleLoadError("factory must expose config_model: BaseModel type")
        return _LoadedFactory(factory=instance, config_model=config_model)

    raise _ModuleLoadError("factory must be a PdfParserFactory or PdfParser")


def _parse_options(options_json: str | None) -> dict[str, Any] | None:
    if options_json is None:
        return None
    try:
        parsed = json.loads(options_json)
    except json.JSONDecodeError as exc:
        raise ValueError("options must be valid JSON") from exc
    if parsed is None:
        return None
    if not isinstance(parsed, dict):
        raise ValueError("options must be a JSON object")
    return parsed


def _build_adapter_union(registry: ParserRegistry) -> Any:
    models = list(registry.config_models().values())
    if not models:
        raise ValueError("no adapters registered")
    union_type = models[0]
    for model in models[1:]:
        union_type = union_type | model
    return Annotated[union_type, Field(discriminator="kind")]  # type: ignore[invalid-type-form]


def _build_cli_model(adapter_union: Any) -> type[BaseModel]:
    return create_model(
        "CliConfig",
        __base__=_CliConfigBase,
        parser=(adapter_union, ...),
        task_id=(str, "task-1"),
        document_id=(str, "doc-1"),
        input_path=(Path, ...),
        output_path=(Path | None, None),
    )


def _load_yaml_config(config: str | None) -> dict[str, Any] | None:
    if config is None:
        return None
    if config == "-":
        content = sys.stdin.read()
    else:
        content = Path(config).read_text()
    if not content.strip():
        return None
    data = yaml.safe_load(content)
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError("config must be a YAML mapping")
    return data


def _apply_overrides(
    config_model: BaseModel,
    *,
    input_path: Path | None,
    output_path: Path | None,
    task_id: str | None,
    document_id: str | None,
    parser_kind: str | None,
    parser_overrides: dict[str, Any] | None,
) -> BaseModel:
    raw = config_model.model_dump()
    if input_path is not None:
        raw["input_path"] = input_path
    if output_path is not None:
        raw["output_path"] = output_path
    if task_id is not None:
        raw["task_id"] = task_id
    if document_id is not None:
        raw["document_id"] = document_id

    if parser_kind is not None or parser_overrides is not None:
        parser_raw = dict(raw.get("parser", {}))
        if parser_kind is not None:
            existing_kind = parser_raw.get("kind")
            if existing_kind is not None and existing_kind != parser_kind:
                parser_raw = {"kind": parser_kind}
            else:
                parser_raw["kind"] = parser_kind
        if parser_overrides:
            parser_raw.update(parser_overrides)
        raw["parser"] = parser_raw

    model_type = type(config_model)
    return model_type.model_validate(raw)


@app.command("parse")
def parse_pdf(
    config_path: str | None = CONFIG_OPT,
    input_path: Path | None = INPUT_OPT,
    parser: str | None = PARSER_OPT,
    options: str | None = OPTIONS_OPT,
    factory: str | None = FACTORY_OPT,
    output_path: Path | None = OUTPUT_OPT,
    task_id: str | None = TASK_ID_OPT,
    document_id: str | None = DOCUMENT_ID_OPT,
    docling_picture_description: bool | None = DOCLING_PIC_DESC_OPT,
    docling_picture_prompt: str | None = DOCLING_PIC_PROMPT_OPT,
    docling_images_scale: float | None = DOCLING_IMAGES_SCALE_OPT,
    docling_generate_picture_images: bool | None = DOCLING_GEN_PIC_OPT,
) -> None:
    """Parse a PDF into markdown using a configured parser."""
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

    if factory is not None:
        loaded = _load_factory(factory)
        name = parser or "docling"
        registry.register_adapter(
            AdapterRegistration(
                name=name,
                config_model=loaded.config_model,
                factory=loaded.factory,
            )
        )

    use_case = ParsePdfToMarkdown(registry)
    adapter_union = _build_adapter_union(registry)
    cli_model = _build_cli_model(adapter_union)
    raw_config = _load_yaml_config(config_path)

    if raw_config is None:
        raw_config = {}
    if "parser" not in raw_config:
        raw_config["parser"] = {"kind": "docling"}
    if "input_path" not in raw_config:
        if input_path is None:
            raise ValueError("input_path is required (use --input or config)")
        raw_config["input_path"] = input_path

    config_model = cast(
        _CliConfigProtocol, TypeAdapter(cli_model).validate_python(raw_config)
    )

    docling_overrides: dict[str, Any] = {}
    if docling_picture_description is not None:
        docling_overrides["picture_description"] = docling_picture_description
    if docling_picture_prompt is not None:
        docling_overrides["picture_prompt"] = docling_picture_prompt
    if docling_images_scale is not None:
        docling_overrides["images_scale"] = docling_images_scale
    if docling_generate_picture_images is not None:
        docling_overrides["generate_picture_images"] = docling_generate_picture_images

    options_overrides = _parse_options(options)
    parser_overrides: dict[str, Any] = {}
    if options_overrides:
        parser_overrides.update(options_overrides)

    parser_kind = parser or None
    if docling_overrides:
        if parser_kind is not None and parser_kind != "docling":
            raise ValueError("docling flags require parser=docling")
        parser_overrides.update(docling_overrides)
    updated_config = cast(
        _CliConfigProtocol,
        _apply_overrides(
            cast(BaseModel, config_model),
            input_path=input_path,
            output_path=output_path,
            task_id=task_id,
            document_id=document_id,
            parser_kind=parser_kind,
            parser_overrides=parser_overrides or None,
        ),
    )

    parser_model = updated_config.parser
    parser_name = getattr(parser_model, "kind", None)
    if parser_name is None:
        raise ValueError("parser kind is required")

    parser_options = parser_model.model_dump(exclude={"kind"})
    parser_config = PdfParserConfig(name=parser_name, options=parser_options)

    try:
        result = use_case.execute(
            ParsePdfToMarkdownInput(
                file_path=updated_config.input_path,
                parser_config=parser_config,
                task_id=TaskId(updated_config.task_id),
                document_id=DocumentId(updated_config.document_id),
            )
        )
    except Exception as exc:
        console.print(Panel(str(exc), title="Parse Failed", style="red"))
        raise typer.Exit(code=1) from exc

    markdown = result.task.document.markdown if result.task.document else None
    if markdown is None:
        console.print(
            Panel("No markdown produced", title="Parse Result", style="yellow")
        )
        raise typer.Exit(code=1)

    output_path = updated_config.output_path
    if output_path is not None:
        output_path.write_text(markdown)
        console.print(
            Panel(
                f"Markdown written to {output_path}",
                title="Parse Result",
                style="green",
            )
        )
    else:
        console.print(markdown)


if __name__ == "__main__":
    app()
