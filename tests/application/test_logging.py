from __future__ import annotations

import logging
from pathlib import Path

import pytest

from doc_parsing.application.logging import LoggingConfig, configure_logging
from doc_parsing.application.use_cases import (
    ParsePdfToMarkdown,
    ParsePdfToMarkdownInput,
)
from doc_parsing.domain import (
    DocumentId,
    ParseOptions,
    PdfParser,
    PdfParserConfig,
    PdfParserFactory,
    TaskId,
)


class FakeParser(PdfParser):
    def parse(self, file_path: Path) -> str:
        return "# ok"


class FakeFactory(PdfParserFactory):
    def create(self, config: PdfParserConfig) -> PdfParser:
        return FakeParser()


def test_configure_logging_json(caplog: pytest.LogCaptureFixture) -> None:
    configure_logging(LoggingConfig(level="INFO", format="json"))
    root = logging.getLogger()

    assert root.level == logging.INFO
    assert root.handlers
    assert any(
        handler.formatter.__class__.__name__ == "_JsonFormatter"
        for handler in root.handlers
    )


def test_use_case_logs_context(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    use_case = ParsePdfToMarkdown(FakeFactory())

    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    data = ParsePdfToMarkdownInput(
        file_path=pdf_path,
        parser_config=PdfParserConfig(name="fake"),
        task_id=TaskId("task-1"),
        document_id=DocumentId("doc-1"),
        options=ParseOptions(),
    )

    with caplog.at_level(logging.INFO):
        use_case.execute(data)

    assert any(
        getattr(record, "task_id", None) == "task-1" for record in caplog.records
    )
    assert any(
        getattr(record, "document_id", None) == "doc-1" for record in caplog.records
    )
