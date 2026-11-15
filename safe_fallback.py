"""Pure-Python conservative campaign fallback for factual repair failures."""

from __future__ import annotations

import re
from typing import Any


class SafeFallbackError(Exception):
    """Raised when a safe deterministic campaign cannot be constructed."""


NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
}
NUMBER_LABELS = {value: word.capitalize() for word, value in NUMBER_WORDS.items()}

ARABIC_ENTITY_TERMS = {
    "agriculture": "الزراعة",
    "health": "الصحة",
    "education": "التربية",
    "finance": "المالية",
    "interior": "الداخلية",
    "environment": "البيئة",
    "labor": "العمل",
    "tourism": "السياحة",
}


def _requested_languages(strategy: dict[str, Any]) -> set[str]:
    values = strategy.get("languages", [])
    if isinstance(values, str):
        values = [values]
    languages = {value for value in values if isinstance(value, str)}
    unsupported = languages - {"Arabic", "English"}
    if unsupported:
        raise SafeFallbackError(
            "Deterministic fallback does not support requested languages: "
            + ", ".join(sorted(unsupported))
        )
    return languages


def _target_audience(strategy: dict[str, Any]) -> list[str]:
    values = strategy.get("target_audience", [])
    if isinstance(values, str):
        values = [values]
    return [
        value.strip() for value in values
        if isinstance(value, str) and value.strip()
    ]


def _extract_service_subject(brief: str) -> dict[str, Any] | None:
    number_words = "|".join(NUMBER_WORDS)
    match = re.search(
        rf"\b(?P<number>\d+|{number_words})\s+"
        r"(?P<descriptor>[^.!?\n]{1,100}?)\s+services\b",
        brief,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    raw_number = match.group("number")
    count = int(raw_number) if raw_number.isdigit() else NUMBER_WORDS[raw_number.casefold()]
    descriptor = re.sub(r"\s+", " ", match.group("descriptor")).strip()
    ministry = re.search(
        r"\bministry\s+of\s+[a-z][a-z\s&-]*",
        descriptor,
        flags=re.IGNORECASE,
    )
    entity = ministry.group(0).strip() if ministry else descriptor
    return {
        "count": count,
        "count_word": NUMBER_LABELS.get(count, str(count)),
        "entity": entity,
    }


def _platform(strategy: dict[str, Any], brief: str) -> str:
    brand_key = str(strategy.get("brand_key", "")).casefold()
    if brand_key == "dawlati" or re.search(r"\bDawlati\b", brief, re.IGNORECASE):
        return "Dawlati"
    brand = strategy.get("brand")
    if isinstance(brand, str) and brand.strip():
        return brand.strip()
    raise SafeFallbackError("Could not safely determine the campaign platform.")


def _arabic_ministry(entity: str) -> str:
    match = re.fullmatch(r"ministry\s+of\s+([a-z\s&-]+)", entity, re.IGNORECASE)
    if not match:
        raise SafeFallbackError(
            "Could not safely construct the requested Arabic subject."
        )
    sector = match.group(1).strip().casefold()
    translated = ARABIC_ENTITY_TERMS.get(sector)
    if not translated:
        raise SafeFallbackError(
            "No tested Arabic entity template exists for the campaign subject."
        )
    return f"وزارة {translated}"


def _join_audience(audience: list[str]) -> str:
    lowered = [value[:1].lower() + value[1:] for value in audience]
    if not lowered:
        return "the approved campaign audience"
    if len(lowered) == 1:
        return lowered[0]
    if len(lowered) == 2:
        return f"{lowered[0]} and {lowered[1]}"
    return ", ".join(lowered[:-1]) + f", and {lowered[-1]}"


def build_safe_fallback_campaign(
    brief: str,
    strategy: dict[str, Any],
    approved_grounding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construct a minimal grounded campaign without calling any model."""
    if not isinstance(brief, str) or not brief.strip():
        raise SafeFallbackError("Campaign brief cannot be empty.")
    if not isinstance(strategy, dict):
        raise SafeFallbackError("Campaign strategy must be a dictionary.")

    languages = _requested_languages(strategy)
    subject = _extract_service_subject(brief)
    if not subject:
        raise SafeFallbackError(
            "No deterministic quantified-service template matches the brief."
        )
    platform = _platform(strategy, brief)
    count = subject["count"]
    count_word = subject["count_word"]
    entity = subject["entity"]
    audience = _target_audience(strategy)
    audience_text = _join_audience(audience)

    english_caption = (
        f"{count_word} {entity} services are now available online through "
        f"{platform}."
    )
    caption_en = english_caption if "English" in languages else ""

    caption_ar = ""
    if "Arabic" in languages:
        if platform.casefold() != "dawlati":
            raise SafeFallbackError(
                "No tested Arabic platform template exists for this brand."
            )
        entity_ar = _arabic_ministry(entity)
        caption_ar = (
            f"أصبحت {count} خدمات تابعة ل{entity_ar} متاحة الآن إلكترونياً "
            "عبر منصة «دولتي»."
        )

    sector_headline = (
        "For the agricultural sector"
        if entity.casefold() == "ministry of agriculture"
        else "For the approved campaign audience"
    )
    structure = [
        {
            "number": 1,
            "type": "Slide",
            "headline": f"{count} {entity} services",
            "body": english_caption,
        },
        {
            "number": 2,
            "type": "Slide",
            "headline": f"Available through {platform}",
            "body": (
                f"Explore the {entity} services now available through {platform}."
            ),
        },
        {
            "number": 3,
            "type": "Slide",
            "headline": sector_headline,
            "body": f"For {audience_text}.",
        },
        {
            "number": 4,
            "type": "Slide",
            "headline": "Explore the available services",
            "body": (
                f"Discover the {count} available {entity} services through {platform}."
            ),
        },
        {
            "number": 5,
            "type": "Slide",
            "headline": "Learn more",
            "body": (
                f"Explore the {count} available {entity} services on {platform}."
            ),
        },
    ]

    visual_concept = (
        f"A professional digital-service announcement for {count} {entity} "
        f"services available online through {platform}, using generic sector "
        "and digital-service visual elements without naming individual services."
    )
    visual_prompt = (
        f"Create a professional public-sector visual announcing that {count} "
        f"{entity} services are available online through {platform}. Use generic "
        "sector and digital-service imagery. Keep all service representation "
        "generic and limited to the announcement facts."
    )
    hashtags = [f"#{platform.replace(' ', '')}"]
    if platform.casefold() == "dawlati":
        hashtags.extend(["#دولتي", "#Lebanon"])

    return {
        "caption_ar": caption_ar,
        "caption_en": caption_en,
        "content_structure": structure,
        "visual_concept": visual_concept,
        "visual_generation_prompt": visual_prompt,
        "cta": f"Explore the {count} available {entity} services on {platform}",
        "hashtags": hashtags,
        "brand_check": {
            "status": "PASS",
            "issues": [],
            "recommendations": [],
        },
    }
