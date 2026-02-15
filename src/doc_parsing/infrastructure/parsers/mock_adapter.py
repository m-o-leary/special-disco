from __future__ import annotations

from .mock import MockConfig, MockPdfParserFactory
from .registration import AdapterRegistration

adapter = AdapterRegistration(
    name="mock",
    config_model=MockConfig,
    factory=MockPdfParserFactory(),
)
