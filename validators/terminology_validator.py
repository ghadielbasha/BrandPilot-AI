import re
from typing import Any

from knowledge_loader import (
    KnowledgeError,
    load_brand_knowledge,
)


# --------------------------------------------------
# Custom Validation Error
# --------------------------------------------------

class TerminologyValidationError(Exception):
    """Raised when generated content violates approved terminology."""
    pass


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def _contains_variant(
    text: str,
    variant: str
) -> bool:
    """
    Case-insensitive matching for Latin text.

    Python casefold keeps Arabic text usable while
    normalizing Latin capitalization.
    """

    return (
        variant.casefold()
        in text.casefold()
    )


def _get_terminology_record(
    brand: str
) -> dict:
    """
    Load the approved terminology dictionary
    for a specific brand.
    """

    knowledge = load_brand_knowledge(
        brand
    )

    terminology = (
        knowledge
        .get("records", {})
        .get("terminology.json")
    )

    if not terminology:
        raise TerminologyValidationError(
            f"No approved terminology dictionary "
            f"was loaded for brand '{brand}'."
        )

    terms = terminology.get(
        "terms"
    )

    if not isinstance(
        terms,
        list
    ):
        raise TerminologyValidationError(
            f"Invalid terminology dictionary "
            f"for brand '{brand}'."
        )

    return terminology


# --------------------------------------------------
# Safe Deterministic Normalization
# --------------------------------------------------

def normalize_terminology(
    text: str,
    brand: str
) -> dict[str, Any]:
    """
    Replace explicitly forbidden terminology variants
    with their approved preferred equivalent.

    Only replacements explicitly defined in the approved
    terminology dictionary are performed.

    The LLM does not decide these replacements.
    """

    if not isinstance(
        text,
        str
    ):
        raise TerminologyValidationError(
            "Text must be a string."
        )

    brand = brand.strip().lower()

    if not brand:
        raise TerminologyValidationError(
            "Brand cannot be empty."
        )

    terminology = _get_terminology_record(
        brand
    )

    normalized_text = text

    changes = []

    for term in terminology[
        "terms"
    ]:

        concept = term.get(
            "concept",
            "unknown"
        )

        preferred = term.get(
            "preferred",
            {}
        )

        forbidden_variants = term.get(
            "forbidden_variants",
            {}
        )

        if not isinstance(
            forbidden_variants,
            dict
        ):
            continue

        for language, variants in (
            forbidden_variants.items()
        ):

            if not isinstance(
                variants,
                list
            ):
                continue

            preferred_value = preferred.get(
                language
            )

            if not isinstance(
                preferred_value,
                str
            ):
                continue

            if not preferred_value:
                continue

            for variant in variants:

                if not isinstance(
                    variant,
                    str
                ):
                    continue

                if not variant:
                    continue

                pattern = re.escape(
                    variant
                )

                if re.search(
                    pattern,
                    normalized_text,
                    flags=re.IGNORECASE
                ):

                    normalized_text = re.sub(
                        pattern,
                        preferred_value,
                        normalized_text,
                        flags=re.IGNORECASE
                    )

                    changes.append(
                        {
                            "concept": concept,
                            "language": language,
                            "from": variant,
                            "to": preferred_value
                        }
                    )

    return {
        "brand": brand,
        "text": normalized_text,
        "changed": len(changes) > 0,
        "changes": changes
    }


# --------------------------------------------------
# Main Validator
# --------------------------------------------------

def validate_terminology(
    text: str,
    brand: str
) -> dict[str, Any]:
    """
    Validate generated text against the approved
    terminology dictionary for a brand.

    This validator does not modify content.

    It reports violations so generation can
    be blocked when required.
    """

    if not isinstance(
        text,
        str
    ):
        raise TerminologyValidationError(
            "Text must be a string."
        )

    brand = brand.strip().lower()

    if not brand:
        raise TerminologyValidationError(
            "Brand cannot be empty."
        )

    terminology = _get_terminology_record(
        brand
    )

    terms = terminology[
        "terms"
    ]

    issues = []

    checked_forbidden_variants = 0

    for term in terms:

        concept = term.get(
            "concept",
            "unknown"
        )

        preferred = term.get(
            "preferred",
            {}
        )

        forbidden_variants = term.get(
            "forbidden_variants",
            {}
        )

        if not isinstance(
            forbidden_variants,
            dict
        ):
            continue

        for language, variants in (
            forbidden_variants.items()
        ):

            if not isinstance(
                variants,
                list
            ):
                continue

            for variant in variants:

                if not isinstance(
                    variant,
                    str
                ):
                    continue

                if not variant:
                    continue

                checked_forbidden_variants += 1

                if _contains_variant(
                    text,
                    variant
                ):

                    preferred_value = (
                        preferred.get(
                            language
                        )
                    )

                    issues.append(
                        {
                            "type": "forbidden_terminology",
                            "concept": concept,
                            "language": language,
                            "found": variant,
                            "preferred": preferred_value,
                            "message": (
                                f"Forbidden terminology "
                                f"'{variant}' detected."
                            )
                        }
                    )

    return {
        "brand": brand,
        "valid": len(issues) == 0,
        "status": (
            "PASS"
            if len(issues) == 0
            else "BLOCK"
        ),
        "issues": issues,
        "checked_terms": len(
            terms
        ),
        "checked_forbidden_variants": (
            checked_forbidden_variants
        )
    }


# --------------------------------------------------
# Enforcement Helper
# --------------------------------------------------

def enforce_terminology(
    text: str,
    brand: str
) -> dict[str, Any]:
    """
    Validate terminology and raise an exception
    when a forbidden variant still exists.

    This function does NOT automatically normalize.
    Normalization must happen explicitly first.
    """

    result = validate_terminology(
        text=text,
        brand=brand
    )

    if not result[
        "valid"
    ]:

        messages = [
            issue["message"]
            for issue in result[
                "issues"
            ]
        ]

        raise TerminologyValidationError(
            "Terminology validation failed: "
            + "; ".join(messages)
        )

    return result


# --------------------------------------------------
# Manual Test
# --------------------------------------------------

if __name__ == "__main__":

    samples = [
        "اكتشف الخدمات عبر منصة «دولتي».",
        "اكتشف الخدمات عبر داولاتي.",
        "اكتشف الخدمات عبر دوالتي.",
        "اكتشف الخدمات عبر داولتي.",
        "اكتشف الخدمات عبر دَولتي.",
    ]

    for sample in samples:

        print(
            "\nORIGINAL:",
            sample
        )

        try:

            normalized = normalize_terminology(
                text=sample,
                brand="dawlati"
            )

            print(
                "NORMALIZED:",
                normalized["text"]
            )

            if normalized[
                "changed"
            ]:

                print(
                    "CHANGES:",
                    normalized["changes"]
                )

            result = validate_terminology(
                text=normalized["text"],
                brand="dawlati"
            )

            print(
                "STATUS:",
                result["status"]
            )

        except (
            KnowledgeError,
            TerminologyValidationError
        ) as error:

            print(
                "ERROR:",
                error
            )
            