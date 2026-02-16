from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from doc_parsing.application.logging import get_logger
from doc_parsing.domain import (
    Document,
    DocumentContent,
    DocumentId,
    DocumentSource,
    ParseOptions,
    ParsingRequest,
    ParsingTask,
    PdfInspector,
    PdfParserConfig,
    PdfParserFactory,
    SourceType,
    TaskId,
    TriageDecision,
    TriageMetadata,
    TriagePolicy,
    TriageResult,
    TriageRoute,
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
        logger = get_logger(
            __name__,
            task_id=data.task_id.value,
            document_id=data.document_id.value,
            parser_name=data.parser_config.name,
        )
        parser = self._parser_factory.create(data.parser_config)

        if not data.file_path.exists():
            raise FileNotFoundError(str(data.file_path))

        logger.info("parse.start", extra={"path": str(data.file_path)})
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
        logger.info("parse.complete", extra={"chars": len(markdown)})
        document = Document(
            document_id=data.document_id,
            source=task.request.source,
            content=DocumentContent.from_markdown(markdown),
        )

        task.complete(document)
        return ParsePdfToMarkdownResult(task=task)


@dataclass(slots=True)
class TriagePdfInput:
    file_path: Path
    task_id: TaskId
    document_id: DocumentId

    def __post_init__(self) -> None:
        if not self.file_path:
            raise ValueError("file_path is required")
        if self.file_path.suffix.lower() != ".pdf":
            raise ValueError("file_path must point to a .pdf file")


@dataclass(slots=True)
class TriagePdfResult:
    result: TriageResult


class TriagePolicyChain(TriagePolicy):
    def __init__(self, policies: list[TriagePolicy]) -> None:
        self._policies = list(policies)

    def decide(self, metadata: TriageMetadata) -> TriageDecision | None:
        for policy in self._policies:
            decision = policy.decide(metadata)
            if decision is not None:
                return decision
        return None


class TriagePdf:
    def __init__(self, inspector: PdfInspector, policy: TriagePolicy) -> None:
        self._inspector = inspector
        self._policy = policy

    def execute(self, data: TriagePdfInput) -> TriagePdfResult:
        logger = get_logger(
            __name__,
            task_id=data.task_id.value,
            document_id=data.document_id.value,
        )

        if not data.file_path.exists():
            raise FileNotFoundError(str(data.file_path))

        with data.file_path.open("rb") as handle:
            header = handle.read(4)
        if header != b"%PDF":
            raise ValueError("file_path does not appear to be a PDF")

        logger.info("triage.start", extra={"path": str(data.file_path)})
        metadata = self._inspector.inspect(data.file_path)
        decision = self._policy.decide(metadata)
        if decision is None:
            decision = TriageDecision(
                route=TriageRoute.DLQ,
                reason="no_policy_match",
                policy="default",
                rule=None,
                hint=None,
            )
        logger.info(
            "triage.complete",
            extra={
                "route": decision.route.value,
                "policy": decision.policy,
                "rule": decision.rule,
            },
        )

        return TriagePdfResult(
            result=TriageResult(metadata=metadata, decision=decision)
        )
