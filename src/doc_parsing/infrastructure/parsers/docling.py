from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    smolvlm_picture_description,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from pydantic import BaseModel, ConfigDict, Field, model_validator

from doc_parsing.domain import PdfParser, PdfParserConfig, PdfParserFactory


class DoclingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["docling"] = Field(default="docling")
    picture_description: bool = False
    picture_prompt: str | None = None
    images_scale: float | None = None
    generate_picture_images: bool = False

    @model_validator(mode="after")
    def _validate_picture_prompt(self) -> DoclingConfig:
        if self.picture_prompt is not None and not self.picture_description:
            raise ValueError("picture_prompt requires picture_description=true")
        return self


@dataclass(slots=True)
class DoclingPdfParser(PdfParser):
    config: DoclingConfig

    def parse(self, file_path: Path) -> str:
        pipeline_options = PdfPipelineOptions()

        if self.config.picture_description:
            pipeline_options.do_picture_description = True
            pipeline_options.picture_description_options = smolvlm_picture_description
            if self.config.picture_prompt is not None:
                pipeline_options.picture_description_options.prompt = (
                    self.config.picture_prompt
                )

        if self.config.images_scale is not None:
            pipeline_options.images_scale = self.config.images_scale

        if self.config.generate_picture_images:
            pipeline_options.generate_picture_images = True

        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        document = converter.convert(file_path).document
        return _document_to_markdown(document)


class DoclingPdfParserFactory(PdfParserFactory):
    config_model = DoclingConfig

    def create(self, config: PdfParserConfig) -> PdfParser:
        options = _coerce_options(config.options)
        options.setdefault("kind", "docling")
        model = DoclingConfig.model_validate(options)
        return DoclingPdfParser(config=model)


def _coerce_options(options: Any) -> dict[str, Any]:
    if options is None:
        return {}
    if isinstance(options, dict):
        return dict(options)
    raise ValueError("options must be a mapping")


def _document_to_markdown(document: Any) -> str:
    for attr in ("export_to_markdown", "to_markdown"):
        method = getattr(document, attr, None)
        if callable(method):
            result = method()
            if isinstance(result, str):
                return result
    raise ValueError("Docling document does not expose a markdown export method")
