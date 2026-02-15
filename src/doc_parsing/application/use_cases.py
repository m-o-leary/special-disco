from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from doc_parsing.domain import (
    Document,
    DocumentContent,
    DocumentId,
    DocumentSource,
    ParseOptions,
    ParsingRequest,
    ParsingTask,
    PdfParserConfig,
    PdfParserFactory,
    SourceType,
    TaskId,
)


@dataclass(slots=True)
class ParsePdfToMarkdownInput:
    file_path: Path
    parser_config: PdfParserConfig
    task_id: TaskId
    document_id: DocumentId
    options: ParseOptions = ParseOptions()

    def __post_init__(self) -> None:
        if not self.file_path:
            raise ValueError("file_path is required")
        if self.file_path.suffix.lower() != ".pdf":
            raise ValueError("file_path must point to a .pdf file")


@dataclass(slots=True)
class ParsePdfToMarkdownResult:
    task: ParsingTask


class ParsePdfToMarkdown:
    def __init__(self, parser_factory: PdfParserFactory) -> None:
        self._parser_factory = parser_factory

    def execute(self, data: ParsePdfToMarkdownInput) -> ParsePdfToMarkdownResult:
        parser = self._parser_factory.create(data.parser_config)

        if not data.file_path.exists():
            raise FileNotFoundError(str(data.file_path))

        task = ParsingTask(
            request=ParsingRequest(
                task_id=data.task_id,
                source=DocumentSource(
                    uri=str(data.file_path), source_type=SourceType.LOCAL_FILE
                ),
                options=data.options,
            )
        )
        task.start()

        markdown = parser.parse(data.file_path)
        document = Document(
            document_id=data.document_id,
            source=task.request.source,
            content=DocumentContent.from_markdown(markdown),
        )

        task.complete(document)
        return ParsePdfToMarkdownResult(task=task)
