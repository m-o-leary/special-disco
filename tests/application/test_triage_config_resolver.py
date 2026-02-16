from __future__ import annotations

from typing import Any, Literal, cast

import pytest
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from doc_parsing.application.triage_config_resolver import TriageConfigResolver
from doc_parsing.infrastructure.triage import (
    TriagePolicyRegistration,
    TriagePolicyRegistry,
)


class FakePolicyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["fake"] = Field(default="fake")
    flag: bool = False


def _registry() -> TriagePolicyRegistry:
    registry = TriagePolicyRegistry()
    registry.register_adapter(
        TriagePolicyRegistration(
            name="fake",
            config_model=FakePolicyConfig,
            factory=lambda config: None,  # not used in resolver tests
        )
    )
    return registry


def test_dynamic_union_and_validation() -> None:
    resolver = TriageConfigResolver(_registry())
    raw = {
        "triage": {"policies": [{"kind": "fake", "flag": True}]},
        "inspection": {"kind": "pypdf"},
        "input_path": "/tmp/a.pdf",
    }

    config = resolver.parse(raw)
    policy = cast(Any, config).triage.policies[0]

    assert isinstance(policy, FakePolicyConfig)
    assert policy.flag is True


def test_unknown_policy_rejected() -> None:
    resolver = TriageConfigResolver(_registry())
    cli_model = resolver.build_cli_model()
    raw = {
        "triage": {"policies": [{"kind": "missing"}]},
        "inspection": {"kind": "pypdf"},
        "input_path": "/tmp/a.pdf",
    }

    with pytest.raises(ValidationError):
        TypeAdapter(cli_model).validate_python(raw)


def test_set_overrides_inspection_and_triage() -> None:
    resolver = TriageConfigResolver(_registry())
    raw = {
        "triage": {"policies": [{"kind": "fake"}]},
        "inspection": {"kind": "pypdf"},
        "input_path": "/tmp/a.pdf",
    }
    config = resolver.parse(raw)

    updated = resolver.apply_overrides(
        config,
        overrides=[
            "inspection.scanned_page_ratio_threshold=0.9",
            'triage.policies=[{"kind": "fake", "flag": true}]',
        ],
    )

    inspection = cast(Any, updated).inspection
    policy = cast(Any, updated).triage.policies[0]

    assert inspection.scanned_page_ratio_threshold == 0.9
    assert policy.flag is True
