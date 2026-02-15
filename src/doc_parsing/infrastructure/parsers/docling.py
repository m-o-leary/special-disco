from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    smolvlm_picture_description,
)
from docling.document_converter import DocumentConverter, PdfFormatOption

from doc_parsing.domain import PdfParser, PdfParserConfig, PdfParserFactory

from .docling_config import DoclingConfig


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
