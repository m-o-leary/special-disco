from __future__ import annotations

from .docling_config import DoclingConfig
from .docling_lazy import LazyDoclingPdfParserFactory
from .registration import AdapterRegistration

adapter = AdapterRegistration(
    name="docling",
    config_model=DoclingConfig,
    factory=LazyDoclingPdfParserFactory(),
)
