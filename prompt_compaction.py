"""Lossless prompt projections that omit duplicated internal metadata."""

from __future__ import annotations

from typing import Any


STRATEGY_PROMPT_KEYS = (
    "brand_key",
    "brand",
    "objective",
    "target_audience",
    "platform",
    "languages",
    "tone",
    "recommended_format",
    "campaign_angle",
    "cta",
)


def compact_strategy_for_prompt(strategy: dict[str, Any]) -> dict[str, Any]:
    """Keep campaign decisions; omit provenance and validator bookkeeping."""
    return {
        key: strategy[key]
        for key in STRATEGY_PROMPT_KEYS
        if key in strategy
    }


VALIDATION_ISSUE_KEYS = (
    "type",
    "capability",
    "field",
    "matched_phrase",
    "generated_audience",
    "approved_audience",
    "campaign_subject",
    "generated_substitution",
    "message",
)


def compact_validation_context(context: dict[str, Any] | None) -> dict[str, Any]:
    """Keep actionable repair feedback without redundant field PASS results."""
    if not context:
        return {}
    issues = context.get("issues", [])
    compact_issues = []
    if isinstance(issues, list):
        for issue in issues:
            if isinstance(issue, dict):
                compact_issues.append({
                    key: issue[key]
                    for key in VALIDATION_ISSUE_KEYS
                    if key in issue
                })
    result = {"issues": compact_issues}
    if "validation_stage" in context:
        result["validation_stage"] = context["validation_stage"]
    return result
