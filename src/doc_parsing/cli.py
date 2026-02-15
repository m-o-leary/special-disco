from __future__ import annotations

import pdb
import sys
import traceback
from pathlib import Path
from typing import Any, cast

import typer
import yaml
from rich.console import Console
from rich.panel import Panel

from doc_parsing.application import ParsePdfToMarkdown, ParsePdfToMarkdownInput
from doc_parsing.application.config_resolver import ConfigResolver
from doc_parsing.domain import (
    DocumentId,
    PdfParserConfig,
    TaskId,
)
from doc_parsing.infrastructure import ParserRegistry

app = typer.Typer(add_completion=False)
console = Console()

CONFIG_OPT = typer.Option(None, "--config", "-c")
INPUT_OPT = typer.Option(None, "--input", "-i")
OUTPUT_OPT = typer.Option(None, "--output", "-o")
PARSER_OPT = typer.Option(None, "--parser", "-p")
SET_OPT = typer.Option(None, "--set")
TASK_ID_OPT = typer.Option(None, "--task-id")
DOCUMENT_ID_OPT = typer.Option(None, "--document-id")
PDB_OPT = typer.Option(False, "--pdb", help="Drop into pdb on error")


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


@app.command("parse")
def parse_pdf(
    config_path: str | None = CONFIG_OPT,
    input_path: Path | None = INPUT_OPT,
    parser: str | None = PARSER_OPT,
    output_path: Path | None = OUTPUT_OPT,
    task_id: str | None = TASK_ID_OPT,
    document_id: str | None = DOCUMENT_ID_OPT,
    set_values: list[str] | None = SET_OPT,
    pdb_on_error: bool = PDB_OPT,
) -> None:
    """Parse a PDF into markdown using a configured parser."""
    registry = ParserRegistry()
    registry.load_from_entrypoints()

    use_case = ParsePdfToMarkdown(registry)
    resolver = ConfigResolver(registry)
    raw_config = _load_yaml_config(config_path)

    if raw_config is None:
        raw_config = {}
    if "parser" not in raw_config:
        raw_config["parser"] = {"kind": "docling"}
    if "input_path" not in raw_config:
        if input_path is None:
            raise ValueError("input_path is required (use --input or config)")
        raw_config["input_path"] = input_path

    config_model = resolver.parse(raw_config)
    updated_config = resolver.apply_base_overrides(
        config_model,
        input_path=input_path,
        output_path=output_path,
        task_id=task_id,
        document_id=document_id,
        parser_kind=parser,
    )
    if set_values:
        updated_config = resolver.apply_overrides(
            updated_config,
            overrides=set_values,
        )

    parser_model = cast(Any, updated_config).parser
    parser_name = getattr(parser_model, "kind", None)
    if parser_name is None:
        raise ValueError("parser kind is required")

    parser_options = parser_model.model_dump(exclude={"kind"})
    parser_config = PdfParserConfig(name=parser_name, options=parser_options)

    try:
        result = use_case.execute(
            ParsePdfToMarkdownInput(
                file_path=cast(Any, updated_config).input_path,
                parser_config=parser_config,
                task_id=TaskId(cast(Any, updated_config).task_id),
                document_id=DocumentId(cast(Any, updated_config).document_id),
            )
        )
    except Exception as exc:
        console.print(Panel(str(exc), title="Parse Failed", style="red"))
        if pdb_on_error:
            traceback.print_exc()
            pdb.post_mortem(exc.__traceback__)
        raise typer.Exit(code=1) from exc

    markdown = result.task.document.markdown if result.task.document else None
    if markdown is None:
        console.print(
            Panel("No markdown produced", title="Parse Result", style="yellow")
        )
        raise typer.Exit(code=1)

    output_path = cast(Any, updated_config).output_path
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
