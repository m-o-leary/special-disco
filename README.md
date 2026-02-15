# doc-parsing

Minimal document parsing service built with clean architecture principles. The core domain is framework-agnostic, while adapters (e.g., Docling) live at the edges.

## What this does
- Parse PDFs to Markdown
- Keep domain models independent from parser implementations
- Support multiple parsers via a registry + config models

## Architecture (high level)
- `domain/`: entities, value objects, and ports (protocols)
- `application/`: use cases
- `infrastructure/`: parser adapters and registry
- `cli.py`: CLI entrypoint

## CLI
Run with a YAML config or flags. Example:

```bash
uv run doc-parse --input /path/to/file.pdf --output /tmp/out.md
```

YAML config (optional):

```yaml
parser:
  kind: docling
input_path: /path/to/file.pdf
output_path: /tmp/out.md
```

```bash
uv run doc-parse --config /path/to/config.yaml
```

## Notes
- Parser configs are defined per adapter using Pydantic v2 models.
- New adapters can be added without changing the top-level config model.
