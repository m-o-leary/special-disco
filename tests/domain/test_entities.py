from __future__ import annotations

import pytest

from doc_parsing.domain import (
    BoundingBox,
    Document,
    DocumentContent,
    DocumentContentKind,
    DocumentId,
    DocumentSource,
    Page,
    ParsingRequest,
    ParsingTask,
    SourceType,
    TableBlock,
    TaskId,
    TextBlock,
)


def test_bounding_box_rejects_invalid_ranges() -> None:
    with pytest.raises(ValueError):
        BoundingBox(x0=0.5, y0=0.1, x1=0.4, y1=0.9)

    with pytest.raises(ValueError):
        BoundingBox(x0=-0.1, y0=0.0, x1=0.5, y1=0.5)


def test_document_rejects_duplicate_page_numbers() -> None:
    source = DocumentSource(uri="/tmp/sample.pdf", source_type=SourceType.LOCAL_FILE)
    document = Document(document_id=DocumentId("doc-1"), source=source)

    document.add_page(Page(number=1))

    with pytest.raises(ValueError):
        document.add_page(Page(number=1))


def test_document_allows_markdown_only() -> None:
    source = DocumentSource(uri="/tmp/sample.md", source_type=SourceType.LOCAL_FILE)
    content = DocumentContent.from_markdown("# Heading")
    document = Document(
        document_id=DocumentId("doc-md"), source=source, content=content
    )

    assert document.markdown == "# Heading"
    assert document.pages == []
    assert document.content.kind == DocumentContentKind.MARKDOWN

    with pytest.raises(ValueError):
        document.add_page(Page(number=1))


def test_document_content_rejects_duplicate_page_numbers() -> None:
    source = DocumentSource(uri="/tmp/sample.pdf", source_type=SourceType.LOCAL_FILE)
    page = Page(number=1)
    content = DocumentContent.from_pages([page])
    document = Document(
        document_id=DocumentId("doc-dup"), source=source, content=content
    )

    with pytest.raises(ValueError):
        DocumentContent.from_pages([page, Page(number=1)])

    with pytest.raises(ValueError):
        document.add_page(Page(number=1))


def test_document_content_rejects_duplicate_block_ids() -> None:
    bbox = BoundingBox(0.0, 0.0, 1.0, 1.0)
    page = Page(
        number=1,
        blocks=[
            TextBlock(block_id="b-1", bbox=bbox, text="hello"),
            TextBlock(block_id="b-1", bbox=bbox, text="duplicate"),
        ],
    )

    with pytest.raises(ValueError):
        DocumentContent.from_pages([page])


def test_page_rejects_duplicate_block_ids() -> None:
    page = Page(number=1)
    bbox = BoundingBox(0.0, 0.0, 1.0, 1.0)

    page.add_block(TextBlock(block_id="b-1", bbox=bbox, text="hello"))

    with pytest.raises(ValueError):
        page.add_block(TextBlock(block_id="b-1", bbox=bbox, text="duplicate"))


def test_table_block_requires_cells() -> None:
    with pytest.raises(ValueError):
        TableBlock(block_id="t-1", bbox=BoundingBox(0.0, 0.0, 1.0, 1.0), cells=tuple())


def test_valid_task_lifecycle() -> None:
    source = DocumentSource(uri="/tmp/sample.pdf", source_type=SourceType.LOCAL_FILE)
    request = ParsingRequest(task_id=TaskId("task-1"), source=source)
    task = ParsingTask(request=request)

    task.start()

    document = Document(document_id=DocumentId("doc-1"), source=source)
    task.complete(document)

    assert task.document == document
    assert task.started_at is not None
    assert task.completed_at is not None


def test_invalid_task_transition_raises() -> None:
    source = DocumentSource(uri="/tmp/sample.pdf", source_type=SourceType.LOCAL_FILE)
    request = ParsingRequest(task_id=TaskId("task-2"), source=source)
    task = ParsingTask(request=request)

    with pytest.raises(ValueError):
        task.complete(Document(document_id=DocumentId("doc-1"), source=source))
