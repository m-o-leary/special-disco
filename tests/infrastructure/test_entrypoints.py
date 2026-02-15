from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import BaseModel, ConfigDict

from doc_parsing.domain import PdfParserFactory
from doc_parsing.infrastructure.parsers.entrypoints import load_entrypoints
from doc_parsing.infrastructure.parsers.registry import AdapterRegistration


class FakeEP:
    def __init__(self, name: str, obj):
        self.name = name
        self._obj = obj

    def load(self):
        return self._obj


class FakeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FakeFactory(PdfParserFactory):
    config_model = FakeConfig

    def create(self, config):  # pragma: no cover - not used
        raise NotImplementedError


def test_entrypoints_load(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = AdapterRegistration(
        name="fake",
        config_model=FakeConfig,
        factory=FakeFactory(),
    )

    eps = SimpleNamespace(select=lambda group: [FakeEP("fake", adapter)])
    monkeypatch.setattr(
        "doc_parsing.infrastructure.parsers.entrypoints.entry_points", lambda: eps
    )

    loaded = load_entrypoints("doc_parsing.adapters")

    assert loaded == [adapter]


def test_entrypoints_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    eps = SimpleNamespace(select=lambda group: [FakeEP("fake", object())])
    monkeypatch.setattr(
        "doc_parsing.infrastructure.parsers.entrypoints.entry_points", lambda: eps
    )

    with pytest.raises(ValueError):
        load_entrypoints("doc_parsing.adapters")
