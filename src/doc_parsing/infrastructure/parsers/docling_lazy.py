from __future__ import annotations

from doc_parsing.domain import PdfParser, PdfParserConfig, PdfParserFactory

from .docling_config import DoclingConfig


class LazyDoclingPdfParserFactory(PdfParserFactory):
    config_model = DoclingConfig

    def create(self, config: PdfParserConfig) -> PdfParser:
        from .docling import DoclingPdfParserFactory

        return DoclingPdfParserFactory().create(config)
