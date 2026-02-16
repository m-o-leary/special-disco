from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from doc_parsing.domain import TriageDecision, TriageMetadata, TriagePolicy, TriageRoute

from .registration import TriagePolicyRegistration


class RuleWhen(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_pages: int | None = None
    max_pages: int | None = None
    languages: list[str] | None = None
    scanned: bool | None = None

    @model_validator(mode="after")
    def _validate_bounds(self) -> RuleWhen:
        if self.min_pages is not None and self.min_pages < 0:
            raise ValueError("min_pages must be >= 0")
        if self.max_pages is not None and self.max_pages < 0:
            raise ValueError("max_pages must be >= 0")
        if (
            self.min_pages is not None
            and self.max_pages is not None
            and self.min_pages > self.max_pages
        ):
            raise ValueError("min_pages cannot be greater than max_pages")
        if self.languages is not None and not self.languages:
            raise ValueError("languages cannot be empty")
        if self.languages is not None:
            if any(not lang.strip() for lang in self.languages):
                raise ValueError("languages cannot contain blank entries")
        return self


class RuleAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route: Literal["parse", "dlq"]
    parser: dict[str, object] | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def _validate_route(self) -> RuleAction:
        if self.route == "parse":
            if not self.parser:
                raise ValueError("parser is required when route=parse")
            if "kind" not in self.parser:
                raise ValueError("parser must include kind")
        if self.route == "dlq":
            if self.reason is None or not self.reason.strip():
                raise ValueError("reason is required when route=dlq")
        return self


class RuleConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    when: RuleWhen
    action: RuleAction

    @model_validator(mode="after")
    def _validate_name(self) -> RuleConfig:
        if not self.name.strip():
            raise ValueError("rule name cannot be empty")
        return self


class RulesPolicyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["rules"] = Field(default="rules")
    name: str
    rules: list[RuleConfig]
    default: RuleAction | None = None

    @model_validator(mode="after")
    def _validate_config(self) -> RulesPolicyConfig:
        if not self.name.strip():
            raise ValueError("policy name cannot be empty")
        if not self.rules:
            raise ValueError("rules policy requires at least one rule")
        return self


class RulesPolicy(TriagePolicy):
    def __init__(self, config: RulesPolicyConfig) -> None:
        self._config = config

    def decide(self, metadata: TriageMetadata) -> TriageDecision | None:
        for rule in self._config.rules:
            if _matches(rule.when, metadata):
                return _decision_from_action(
                    rule.action,
                    policy=self._config.name,
                    rule=rule.name,
                )

        if self._config.default is not None:
            return _decision_from_action(
                self._config.default,
                policy=self._config.name,
                rule=None,
            )
        return None


def _matches(when: RuleWhen, metadata: TriageMetadata) -> bool:
    if when.min_pages is not None and metadata.page_count < when.min_pages:
        return False
    if when.max_pages is not None and metadata.page_count > when.max_pages:
        return False
    if when.scanned is not None and metadata.scanned is not when.scanned:
        return False
    if when.languages is not None:
        if metadata.language is None:
            return False
        accepted = {lang.lower() for lang in when.languages}
        if metadata.language.lower() not in accepted:
            return False
    return True


def _decision_from_action(
    action: RuleAction, *, policy: str, rule: str | None
) -> TriageDecision:
    route = TriageRoute.PARSE if action.route == "parse" else TriageRoute.DLQ
    return TriageDecision(
        route=route,
        parser=action.parser,
        reason=action.reason,
        policy=policy,
        rule=rule,
    )


def _build_policy(config: BaseModel) -> TriagePolicy:
    if not isinstance(config, RulesPolicyConfig):
        raise TypeError("RulesPolicyConfig is required")
    return RulesPolicy(config)


policy = TriagePolicyRegistration(
    name="rules",
    config_model=RulesPolicyConfig,
    factory=_build_policy,
)
