from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from langdetect import DetectorFactory, LangDetectException, detect
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pypdf import PdfReader

from doc_parsing.domain import PdfInspector, TriageMetadata

DetectorFactory.seed = 0


class PypdfInspectorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["pypdf"] = Field(default="pypdf")
    scanned_page_ratio_threshold: float = 0.7
    min_text_chars: int = 20
    language_sample_pages: int = 5
    language_min_chars: int = 200

    @model_validator(mode="after")
    def _validate_values(self) -> PypdfInspectorConfig:
        if not (0.0 <= self.scanned_page_ratio_threshold <= 1.0):
            raise ValueError("scanned_page_ratio_threshold must be between 0.0 and 1.0")
        if self.min_text_chars < 0:
            raise ValueError("min_text_chars must be >= 0")
        if self.language_sample_pages < 1:
            raise ValueError("language_sample_pages must be >= 1")
        if self.language_min_chars < 0:
            raise ValueError("language_min_chars must be >= 0")
        return self


class PypdfInspector(PdfInspector):
    def __init__(self, config: PypdfInspectorConfig) -> None:
        self._config = config

    def inspect(self, file_path: Path) -> TriageMetadata:
        reader = PdfReader(str(file_path))
        page_count = len(reader.pages)
        image_only_pages = 0
        language_parts: list[str] = []

        for index, page in enumerate(reader.pages):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            has_text = len(text.strip()) >= self._config.min_text_chars
            try:
                has_image = _page_has_image(page)
            except Exception:
                has_image = False

            if not has_text and has_image:
                image_only_pages += 1

            if index < self._config.language_sample_pages:
                language_parts.append(text)

        ratio = image_only_pages / page_count if page_count else 0.0
        scanned = ratio >= self._config.scanned_page_ratio_threshold
        language = _detect_language(
            " ".join(language_parts), self._config.language_min_chars
        )

        return TriageMetadata(
            page_count=page_count,
            language=language,
            scanned=scanned,
            image_only_pages=image_only_pages,
            image_only_page_ratio=ratio,
        )


def _detect_language(text: str, min_chars: int) -> str | None:
    sample = text.strip()
    if len(sample) < min_chars:
        return None
    try:
        return detect(sample)
    except LangDetectException:
        return None


def _page_has_image(page: Any) -> bool:
    resources = _get_attr(page, "/Resources")
    if not resources:
        return False
    xobject = _get_attr(resources, "/XObject")
    if not xobject:
        return False
    xobject = _deref(xobject)
    for obj in getattr(xobject, "values", lambda: [])():
        candidate = _deref(obj)
        subtype = _get_attr(candidate, "/Subtype")
        if subtype is None:
            continue
        if str(subtype) == "/Image":
            return True
    return False


def _get_attr(obj: Any, key: str) -> Any:
    if hasattr(obj, "get"):
        return obj.get(key)
    return None


def _deref(obj: Any) -> Any:
    if hasattr(obj, "get_object"):
        try:
            return obj.get_object()
        except Exception:
            return obj
    return obj
