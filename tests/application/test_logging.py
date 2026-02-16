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
    doc_logger = logging.getLogger("doc_parsing")

    assert root.level == logging.CRITICAL
    assert not root.handlers
    assert doc_logger.handlers
    assert doc_logger.level == logging.INFO
    assert doc_logger.propagate is False
    assert any(
        handler.formatter.__class__.__name__ == "_JsonFormatter"
        for handler in doc_logger.handlers
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

    doc_logger = logging.getLogger("doc_parsing")
    doc_logger.addHandler(caplog.handler)
    caplog.set_level(logging.INFO, logger="doc_parsing")
    try:
        use_case.execute(data)
    finally:
        doc_logger.removeHandler(caplog.handler)

    assert any(
        getattr(record, "task_id", None) == "task-1" for record in caplog.records
    )
    assert any(
        getattr(record, "document_id", None) == "doc-1" for record in caplog.records
    )
