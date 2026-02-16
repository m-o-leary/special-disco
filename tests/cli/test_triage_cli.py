from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfWriter
from typer.testing import CliRunner

from doc_parsing.cli import app
from doc_parsing.infrastructure.triage.registry import TriagePolicyRegistry
from doc_parsing.infrastructure.triage.rules_policy import policy as rules_policy


def _write_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with path.open("wb") as handle:
        writer.write(handle)


def test_triage_cli_outputs_json(tmp_path: Path, monkeypatch) -> None:
    def _load_entrypoints(self) -> None:
        self.register_adapter(rules_policy)

    monkeypatch.setattr(
        TriagePolicyRegistry,
        "load_from_entrypoints",
        _load_entrypoints,
    )

    pdf_path = tmp_path / "sample.pdf"
    _write_pdf(pdf_path)

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        f"""
input_path: {pdf_path}
inspection:
  kind: pypdf
  scanned_page_ratio_threshold: 0.7
  min_text_chars: 20
  language_sample_pages: 1
  language_min_chars: 1000
triage:
  policies:
    - kind: rules
      name: "rules"
      rules:
        - name: "one-page"
          when:
            min_pages: 1
            max_pages: 1
            scanned: false
          action:
            route: parse
            parser:
              kind: docling
"""
    )

    runner = CliRunner()
    result = runner.invoke(app, ["triage", "--config", str(config_path)])

    assert result.exit_code == 0

    payload = json.loads(result.stdout)
    assert payload["metadata"]["page_count"] == 1
    assert payload["metadata"]["scanned"] is False
    assert payload["decision"]["route"] == "parse"
    assert payload["decision"]["policy"] == "rules"
