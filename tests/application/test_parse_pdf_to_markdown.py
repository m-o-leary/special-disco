from __future__ import annotations

from pathlib import Path

import pytest

from doc_parsing.application import ParsePdfToMarkdown, ParsePdfToMarkdownInput
from doc_parsing.domain import (
    DocumentId,
    PdfParser,
    PdfParserConfig,
    PdfParserFactory,
    TaskId,
)


class FakePdfParser(PdfParser):
    def __init__(self, markdown: str) -> None:
        self._markdown = markdown

    def parse(self, file_path: Path) -> str:
        return self._markdown


class FakePdfParserFactory(PdfParserFactory):
    def __init__(self, parser: PdfParser) -> None:
        self._parser = parser

    def create(self, config: PdfParserConfig) -> PdfParser:
        return self._parser


def test_parse_pdf_to_markdown(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    parser = FakePdfParser("# Title\n\nBody")
    use_case = ParsePdfToMarkdown(FakePdfParserFactory(parser))
    result = use_case.execute(
        ParsePdfToMarkdownInput(
            file_path=pdf_path,
            parser_config=PdfParserConfig(name="fake"),
            task_id=TaskId("task-1"),
            document_id=DocumentId("doc-1"),
        )
    )

    assert result.task.document is not None
    assert result.task.document.markdown == "# Title\n\nBody"
    assert result.task.document.pages == []


def test_parse_pdf_to_markdown_rejects_non_pdf(tmp_path: Path) -> None:
    text_path = tmp_path / "sample.txt"
    text_path.write_text("not a pdf")

    use_case = ParsePdfToMarkdown(FakePdfParserFactory(FakePdfParser("#")))

    with pytest.raises(ValueError):
        use_case.execute(
            ParsePdfToMarkdownInput(
                file_path=text_path,
                parser_config=PdfParserConfig(name="fake"),
                task_id=TaskId("task-1"),
                document_id=DocumentId("doc-1"),
            )
        )


def test_parse_pdf_to_markdown_requires_file(tmp_path: Path) -> None:
    pdf_path = tmp_path / "missing.pdf"
    use_case = ParsePdfToMarkdown(FakePdfParserFactory(FakePdfParser("#")))

    with pytest.raises(FileNotFoundError):
        use_case.execute(
            ParsePdfToMarkdownInput(
                file_path=pdf_path,
                parser_config=PdfParserConfig(name="fake"),
                task_id=TaskId("task-1"),
                document_id=DocumentId("doc-1"),
            )
        )
