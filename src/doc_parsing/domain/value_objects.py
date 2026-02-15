from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True, slots=True)
class DocumentId:
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("DocumentId cannot be empty")


@dataclass(frozen=True, slots=True)
class TaskId:
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("TaskId cannot be empty")


class SourceType(StrEnum):
    LOCAL_FILE = "local_file"
    URL = "url"
    OBJECT_STORAGE = "object_storage"
    RAW_BYTES = "raw_bytes"


@dataclass(frozen=True, slots=True)
class DocumentSource:
    uri: str
    source_type: SourceType
    mime_type: str | None = None

    def __post_init__(self) -> None:
        if not self.uri.strip():
            raise ValueError("Document source URI cannot be empty")


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Represents a rectangular region on a page."""

    x0: float
    y0: float
    x1: float
    y1: float
    normalized: bool = True

    def __post_init__(self) -> None:
        if self.x0 >= self.x1:
            raise ValueError("x0 must be less than x1")
        if self.y0 >= self.y1:
            raise ValueError("y0 must be less than y1")

        if self.normalized:
            values = (self.x0, self.y0, self.x1, self.y1)
            if any(v < 0.0 or v > 1.0 for v in values):
                raise ValueError(
                    "Normalized bounding boxes must have coordinates in [0.0, 1.0]"
                )


@dataclass(frozen=True, slots=True)
class ParseOptions:
    extract_tables: bool = True
    extract_images: bool = True
    extract_text: bool = True
    language_hint: str | None = None

    def __post_init__(self) -> None:
        if self.language_hint is not None and not self.language_hint.strip():
            raise ValueError("language_hint cannot be blank")
