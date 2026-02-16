from __future__ import annotations

from pathlib import Path

from doc_parsing.application.use_cases import TriagePdf, TriagePdfInput
from doc_parsing.domain import (
    DocumentId,
    PdfInspector,
    TaskId,
    TriageDecision,
    TriageMetadata,
    TriagePolicy,
    TriageRoute,
)


class FakeInspector(PdfInspector):
    def __init__(self, metadata: TriageMetadata) -> None:
        self._metadata = metadata

    def inspect(self, file_path: Path) -> TriageMetadata:
        return self._metadata


class FakePolicy(TriagePolicy):
    def __init__(self, decision: TriageDecision | None) -> None:
        self._decision = decision

    def decide(self, metadata: TriageMetadata) -> TriageDecision | None:
        return self._decision


def _write_pdf(path: Path) -> None:
    path.write_bytes(b"%PDF-1.4\n")


def test_triage_pdf_returns_decision(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    _write_pdf(pdf_path)

    metadata = TriageMetadata(
        page_count=1,
        language="en",
        scanned=False,
        image_only_pages=0,
        image_only_page_ratio=0.0,
    )
    decision = TriageDecision(
        route=TriageRoute.PARSE,
        reason=None,
        policy="fake",
        rule="rule-1",
        hint="default",
    )

    use_case = TriagePdf(FakeInspector(metadata), FakePolicy(decision))
    result = use_case.execute(
        TriagePdfInput(
            file_path=pdf_path,
            task_id=TaskId("task-1"),
            document_id=DocumentId("doc-1"),
        )
    )

    assert result.result.metadata == metadata
    assert result.result.decision == decision


def test_triage_pdf_defaults_to_dlq(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    _write_pdf(pdf_path)

    metadata = TriageMetadata(
        page_count=2,
        language=None,
        scanned=True,
        image_only_pages=2,
        image_only_page_ratio=1.0,
    )

    use_case = TriagePdf(FakeInspector(metadata), FakePolicy(None))
    result = use_case.execute(
        TriagePdfInput(
            file_path=pdf_path,
            task_id=TaskId("task-2"),
            document_id=DocumentId("doc-2"),
        )
    )

    decision = result.result.decision
    assert decision.route == TriageRoute.DLQ
    assert decision.reason == "no_policy_match"
    assert decision.policy == "default"
