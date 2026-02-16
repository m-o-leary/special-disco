from __future__ import annotations

from doc_parsing.domain import TriageMetadata, TriageRoute
from doc_parsing.infrastructure.triage.rules_policy import (
    RuleAction,
    RuleConfig,
    RulesPolicy,
    RulesPolicyConfig,
    RuleWhen,
)


def test_rules_policy_matches_rule() -> None:
    config = RulesPolicyConfig(
        name="policy-1",
        rules=[
            RuleConfig(
                name="small-en",
                when=RuleWhen(min_pages=1, max_pages=10, languages=["en"]),
                action=RuleAction(
                    route="parse",
                    hint="default",
                ),
            )
        ],
    )
    policy = RulesPolicy(config)

    metadata = TriageMetadata(
        page_count=5,
        language="en",
        scanned=False,
        image_only_pages=0,
        image_only_page_ratio=0.0,
    )

    decision = policy.decide(metadata)

    assert decision is not None
    assert decision.route == TriageRoute.PARSE
    assert decision.policy == "policy-1"
    assert decision.rule == "small-en"


def test_rules_policy_default_used_when_no_match() -> None:
    config = RulesPolicyConfig(
        name="policy-2",
        rules=[
            RuleConfig(
                name="english",
                when=RuleWhen(languages=["en"]),
                action=RuleAction(
                    route="parse",
                    hint="default",
                ),
            )
        ],
        default=RuleAction(route="dlq", reason="no_match"),
    )
    policy = RulesPolicy(config)

    metadata = TriageMetadata(
        page_count=1,
        language="fr",
        scanned=False,
        image_only_pages=0,
        image_only_page_ratio=0.0,
    )

    decision = policy.decide(metadata)

    assert decision is not None
    assert decision.route == TriageRoute.DLQ
    assert decision.reason == "no_match"
    assert decision.rule is None


def test_rules_policy_returns_none_without_default() -> None:
    config = RulesPolicyConfig(
        name="policy-3",
        rules=[
            RuleConfig(
                name="scanned-only",
                when=RuleWhen(scanned=True),
                action=RuleAction(
                    route="dlq",
                    reason="scanned_pdf",
                ),
            )
        ],
    )
    policy = RulesPolicy(config)

    metadata = TriageMetadata(
        page_count=2,
        language=None,
        scanned=False,
        image_only_pages=0,
        image_only_page_ratio=0.0,
    )

    assert policy.decide(metadata) is None
