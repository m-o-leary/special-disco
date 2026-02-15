from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from .value_objects import (
    BoundingBox,
    DocumentId,
    DocumentSource,
    ParseOptions,
    TaskId,
)


class BlockType(StrEnum):
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"


class ParseStatus(StrEnum):
    RECEIVED = "received"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DocumentContentKind(StrEnum):
    BLOCKS = "blocks"
    MARKDOWN = "markdown"


ALLOWED_STATUS_TRANSITIONS: dict[ParseStatus, frozenset[ParseStatus]] = {
    ParseStatus.RECEIVED: frozenset({ParseStatus.RUNNING, ParseStatus.CANCELLED}),
    ParseStatus.RUNNING: frozenset(
        {ParseStatus.SUCCEEDED, ParseStatus.FAILED, ParseStatus.CANCELLED}
    ),
    ParseStatus.SUCCEEDED: frozenset(),
    ParseStatus.FAILED: frozenset(),
    ParseStatus.CANCELLED: frozenset(),
}


def _require_non_blank(value: str, *, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} cannot be empty")


def _ensure_unique[T](
    values: list[T], *, key: Callable[[T], object], field_name: str
) -> None:
    seen: set[object] = set()
    for value in values:
        marker = key(value)
        if marker in seen:
            raise ValueError(f"duplicate {field_name}: {marker}")
        seen.add(marker)


def _ensure_pages_valid(pages: list[Page]) -> None:
    _ensure_unique(pages, key=lambda page: page.number, field_name="page number")
    for page in pages:
        _ensure_unique(
            page.blocks, key=lambda block: block.block_id, field_name="block_id"
        )


@dataclass(slots=True)
class ContentBlock:
    block_id: str
    bbox: BoundingBox
    kind: BlockType

    def __post_init__(self) -> None:
        _require_non_blank(self.block_id, field_name="block_id")


@dataclass(slots=True)
class TextBlock(ContentBlock):
    kind: BlockType = field(default=BlockType.TEXT, init=False)
    text: str = ""
    confidence: float | None = None

    def __post_init__(self) -> None:
        ContentBlock.__post_init__(self)
        _require_non_blank(self.text, field_name="text block content")
        if self.confidence is not None and not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")


@dataclass(slots=True)
class TableBlock(ContentBlock):
    kind: BlockType = field(default=BlockType.TABLE, init=False)
    cells: tuple[tuple[str, ...], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        ContentBlock.__post_init__(self)
        if not self.cells:
            raise ValueError("table must have at least one row")
        if any(not row for row in self.cells):
            raise ValueError("table rows cannot be empty")


@dataclass(slots=True)
class ImageBlock(ContentBlock):
    kind: BlockType = field(default=BlockType.IMAGE, init=False)
    description: str | None = None

    def __post_init__(self) -> None:
        ContentBlock.__post_init__(self)
        if self.description is not None and not self.description.strip():
            raise ValueError("description cannot be blank")


@dataclass(slots=True)
class Page:
    number: int
    blocks: list[ContentBlock] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.number < 1:
            raise ValueError("page number must be >= 1")

    def add_block(self, block: ContentBlock) -> None:
        if any(existing.block_id == block.block_id for existing in self.blocks):
            raise ValueError(
                f"duplicate block_id on page {self.number}: {block.block_id}"
            )
        self.blocks.append(block)


@dataclass(slots=True)
class DocumentContent:
    kind: DocumentContentKind
    pages: list[Page] = field(default_factory=list)
    markdown: str | None = None

    @classmethod
    def from_pages(cls, pages: list[Page]) -> DocumentContent:
        pages_copy = list(pages)
        _ensure_pages_valid(pages_copy)
        pages_copy.sort(key=lambda page: page.number)
        return cls(kind=DocumentContentKind.BLOCKS, pages=pages_copy, markdown=None)

    @classmethod
    def from_markdown(cls, markdown: str) -> DocumentContent:
        return cls(kind=DocumentContentKind.MARKDOWN, pages=[], markdown=markdown)

    def __post_init__(self) -> None:
        if self.kind == DocumentContentKind.BLOCKS:
            if self.markdown is not None:
                raise ValueError("markdown must be None for block-based content")
            _ensure_pages_valid(self.pages)
        elif self.kind == DocumentContentKind.MARKDOWN:
            if self.pages:
                raise ValueError("pages must be empty for markdown content")
            if self.markdown is None:
                raise ValueError("markdown content cannot be None")
            _require_non_blank(self.markdown, field_name="markdown")


@dataclass(slots=True)
class Document:
    document_id: DocumentId
    source: DocumentSource
    content: DocumentContent = field(
        default_factory=lambda: DocumentContent.from_pages([])
    )
    metadata: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    @property
    def pages(self) -> list[Page]:
        return self.content.pages

    @property
    def markdown(self) -> str | None:
        return self.content.markdown

    def add_page(self, page: Page) -> None:
        if self.content.kind != DocumentContentKind.BLOCKS:
            raise ValueError("cannot add pages to a markdown-only document")
        if any(existing.number == page.number for existing in self.pages):
            raise ValueError(f"duplicate page number: {page.number}")
        self.pages.append(page)
        self.pages.sort(key=lambda p: p.number)

    def get_page(self, number: int) -> Page | None:
        for page in self.pages:
            if page.number == number:
                return page
        return None

    def all_blocks(self) -> list[ContentBlock]:
        return [block for page in self.pages for block in page.blocks]


@dataclass(frozen=True, slots=True)
class ParsingRequest:
    task_id: TaskId
    source: DocumentSource
    options: ParseOptions = field(default_factory=ParseOptions)
    requested_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


@dataclass(slots=True)
class ParsingTask:
    request: ParsingRequest
    status: ParseStatus = ParseStatus.RECEIVED
    document: Document | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None

    def start(self) -> None:
        self._ensure_transition_allowed(ParseStatus.RUNNING)
        self.status = ParseStatus.RUNNING
        self.started_at = datetime.now(tz=UTC)

    def complete(self, document: Document) -> None:
        self._ensure_transition_allowed(ParseStatus.SUCCEEDED)
        self.status = ParseStatus.SUCCEEDED
        self.document = document
        self._mark_completed()

    def fail(self, error_message: str) -> None:
        self._ensure_transition_allowed(ParseStatus.FAILED)
        _require_non_blank(error_message, field_name="error_message")
        self.status = ParseStatus.FAILED
        self.error_message = error_message
        self._mark_completed()

    def cancel(self) -> None:
        self._ensure_transition_allowed(ParseStatus.CANCELLED)
        self.status = ParseStatus.CANCELLED
        self._mark_completed()

    def _ensure_transition_allowed(self, target: ParseStatus) -> None:
        if target not in ALLOWED_STATUS_TRANSITIONS[self.status]:
            raise ValueError(
                f"invalid status transition from {self.status.value} to {target.value}"
            )

    def _mark_completed(self) -> None:
        self.completed_at = datetime.now(tz=UTC)
