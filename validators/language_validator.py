import re
from typing import Any


class LanguageValidationError(Exception):
    """Raised when generated content fails language-quality checks."""
    pass


# --------------------------------------------------
# Character Patterns
# --------------------------------------------------

ARABIC_CHARACTER_PATTERN = re.compile(
    r"[\u0600-\u06FF]"
)

LATIN_CHARACTER_PATTERN = re.compile(
    r"[A-Za-z]"
)

ARABIC_DIACRITICS_PATTERN = re.compile(
    r"[\u0610-\u061A"
    r"\u064B-\u065F"
    r"\u0670"
    r"\u06D6-\u06ED]"
)


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def _strip_arabic_diacritics(
    text: str
) -> str:

    return ARABIC_DIACRITICS_PATTERN.sub(
        "",
        text
    )


def _count_arabic_characters(
    text: str
) -> int:

    return len(
        ARABIC_CHARACTER_PATTERN.findall(
            text
        )
    )


def _count_latin_characters(
    text: str
) -> int:

    return len(
        LATIN_CHARACTER_PATTERN.findall(
            text
        )
    )


def detect_dominant_language(
    text: str
) -> str | None:
    """
    Detect the dominant language of generated text.

    Returns:
        "Arabic"
        "English"
        None
    """

    arabic_count = _count_arabic_characters(
        text
    )

    latin_count = _count_latin_characters(
        text
    )


    if (
        arabic_count < 5
        and latin_count < 5
    ):
        return None


    if arabic_count >= latin_count:
        return "Arabic"


    return "English"


# --------------------------------------------------
# Known Malformed Arabic Structures
# --------------------------------------------------

ARABIC_QUALITY_PATTERNS = [
    {
        "id": "dawlati_described_as_services",

        "pattern": (
            r"(?:منصة\s+)?"
            r"[«\"]?دولتي[»\"]?"
            r"\s+"
            r"(?:تعد|تعتبر)"
            r"\s+"
            r"(?:الآن\s+)?"
            r"(?:\d+|[٠-٩]+)"
            r"\s+"
            r"(?:خدمة|خدمات)"
        ),

        "message": (
            "Malformed Arabic structure detected: "
            "Dawlati is incorrectly described as being "
            "the services themselves."
        )
    },

    {
        "id": "dawlati_is_services",

        "pattern": (
            r"(?:منصة\s+)?"
            r"[«\"]?دولتي[»\"]?"
            r"\s+"
            r"(?:هي|عبارة\s+عن)"
            r"\s+"
            r"(?:\d+|[٠-٩]+)"
            r"\s+"
            r"(?:خدمة|خدمات)"
        ),

        "message": (
            "Malformed Arabic meaning detected: "
            "Dawlati cannot be described as a number "
            "of government services."
        )
    },

    {
        "id": "nonsensical_triangular_option",

        "pattern": (
            r"خيار\S*"
            r"\s+"
            r"مثلث\S*"
        ),

        "message": (
            "Nonsensical Arabic phrase detected around "
            "the expression 'خيار مثلث'."
        )
    },
]


# --------------------------------------------------
# Known Malformed English Structures
# --------------------------------------------------

ENGLISH_QUALITY_PATTERNS = [
    {
        "id": "dawlati_is_services",

        "pattern": (
            r"\bDawlati\s+"
            r"(?:is|are)\s+"
            r"\d+\s+services\b"
        ),

        "message": (
            "Malformed English meaning detected: "
            "Dawlati cannot be described as being "
            "the services themselves."
        )
    },
]


# --------------------------------------------------
# Arabic Validation
# --------------------------------------------------

def _validate_arabic(
    text: str
) -> list[dict]:

    issues = []

    arabic_count = _count_arabic_characters(
        text
    )

    latin_count = _count_latin_characters(
        text
    )


    # Arabic field must actually contain Arabic.

    if arabic_count < 5:

        issues.append(
            {
                "type": "language_mismatch",
                "language": "Arabic",

                "message": (
                    "Arabic content does not contain "
                    "enough Arabic text."
                )
            }
        )


    # Prevent English-dominant content
    # inside an Arabic field.

    if (
        latin_count > 20
        and latin_count > arabic_count
    ):

        issues.append(
            {
                "type": "language_mismatch",
                "language": "Arabic",

                "message": (
                    "Arabic content appears to be "
                    "dominated by English text."
                )
            }
        )


    normalized = _strip_arabic_diacritics(
        text
    )


    # Known malformed structures.

    for rule in ARABIC_QUALITY_PATTERNS:

        if re.search(
            rule["pattern"],
            normalized,
            flags=re.IGNORECASE
        ):

            issues.append(
                {
                    "type": "malformed_language",
                    "language": "Arabic",
                    "rule": rule["id"],
                    "message": rule["message"],
                }
            )


    # Excessive repeated words.

    repeated_word = re.search(
        r"\b([\u0600-\u06FF]{2,})"
        r"(?:\s+\1){2,}\b",
        normalized
    )


    if repeated_word:

        issues.append(
            {
                "type": "repeated_language",
                "language": "Arabic",
                "found": repeated_word.group(0),

                "message": (
                    "Arabic content contains excessive "
                    "repetition of the same word."
                )
            }
        )


    return issues


# --------------------------------------------------
# English Validation
# --------------------------------------------------

def _validate_english(
    text: str
) -> list[dict]:

    issues = []

    latin_count = _count_latin_characters(
        text
    )

    arabic_count = _count_arabic_characters(
        text
    )


    # English field must actually contain English.

    if latin_count < 5:

        issues.append(
            {
                "type": "language_mismatch",
                "language": "English",

                "message": (
                    "English content does not contain "
                    "enough English text."
                )
            }
        )


    # Prevent Arabic-dominant content
    # inside an English field.

    if (
        arabic_count > 20
        and arabic_count > latin_count
    ):

        issues.append(
            {
                "type": "language_mismatch",
                "language": "English",

                "message": (
                    "English content appears to be "
                    "dominated by Arabic text."
                )
            }
        )


    # Known malformed English structures.

    for rule in ENGLISH_QUALITY_PATTERNS:

        if re.search(
            rule["pattern"],
            text,
            flags=re.IGNORECASE
        ):

            issues.append(
                {
                    "type": "malformed_language",
                    "language": "English",
                    "rule": rule["id"],
                    "message": rule["message"],
                }
            )


    # Excessive repeated words.

    repeated_word = re.search(
        r"\b([A-Za-z]{2,})"
        r"(?:\s+\1){2,}\b",
        text,
        flags=re.IGNORECASE
    )


    if repeated_word:

        issues.append(
            {
                "type": "repeated_language",
                "language": "English",
                "found": repeated_word.group(0),

                "message": (
                    "English content contains excessive "
                    "repetition of the same word."
                )
            }
        )


    return issues


# --------------------------------------------------
# Single Text Validation
# --------------------------------------------------

def validate_language_quality(
    text: str,
    language: str
) -> dict[str, Any]:

    if not isinstance(
        text,
        str
    ):

        raise LanguageValidationError(
            "Text must be a string."
        )


    if not text.strip():

        raise LanguageValidationError(
            "Text cannot be empty."
        )


    language = (
        language
        .strip()
        .casefold()
    )


    if language == "arabic":

        issues = _validate_arabic(
            text
        )


    elif language == "english":

        issues = _validate_english(
            text
        )


    else:

        raise LanguageValidationError(
            f"Unsupported language: {language}"
        )


    return {
        "language": language,

        "valid": (
            len(
                issues
            ) == 0
        ),

        "status": (
            "PASS"
            if len(issues) == 0
            else "BLOCK"
        ),

        "issues": issues,
    }


# --------------------------------------------------
# Automatic Language Validation
# --------------------------------------------------

def validate_language_quality_auto(
    text: str
) -> dict[str, Any]:

    if not isinstance(
        text,
        str
    ):

        raise LanguageValidationError(
            "Text must be a string."
        )


    if not text.strip():

        raise LanguageValidationError(
            "Text cannot be empty."
        )


    detected_language = detect_dominant_language(
        text
    )


    if detected_language is None:

        return {
            "language": "unknown",
            "valid": True,
            "status": "PASS",
            "issues": [],
        }


    return validate_language_quality(
        text=text,
        language=detected_language
    )


# --------------------------------------------------
# Full Campaign Validation
# --------------------------------------------------

def validate_campaign_language_quality(
    content: dict,
    requested_languages
) -> dict[str, Any]:

    if not isinstance(
        content,
        dict
    ):

        raise LanguageValidationError(
            "Campaign content must be a dictionary."
        )


    requested_languages = set(
        requested_languages
    )

    field_results = []
    issues = []


    # --------------------------------------------------
    # Local Field Validator
    # --------------------------------------------------

    def validate_field(
        field_name: str,
        text: str,
        language: str | None = None
    ):

        if not isinstance(
            text,
            str
        ):
            return


        if not text.strip():
            return


        if language:

            result = validate_language_quality(
                text=text,
                language=language
            )

        else:

            result = validate_language_quality_auto(
                text=text
            )


        field_results.append(
            {
                "field": field_name,
                "result": result,
            }
        )


        if not result[
            "valid"
        ]:

            for issue in result[
                "issues"
            ]:

                issue_copy = dict(
                    issue
                )

                issue_copy[
                    "field"
                ] = field_name

                issues.append(
                    issue_copy
                )


    # --------------------------------------------------
    # Captions
    # --------------------------------------------------

    if "Arabic" in requested_languages:

        validate_field(
            "caption_ar",
            content.get(
                "caption_ar",
                ""
            ),
            "Arabic"
        )


    if "English" in requested_languages:

        validate_field(
            "caption_en",
            content.get(
                "caption_en",
                ""
            ),
            "English"
        )


    # --------------------------------------------------
    # Content Structure
    # --------------------------------------------------

    content_structure = content.get(
        "content_structure",
        []
    )


    if isinstance(
        content_structure,
        list
    ):

        for index, item in enumerate(
            content_structure,
            start=1
        ):

            if not isinstance(
                item,
                dict
            ):
                continue


            validate_field(
                (
                    f"content_structure"
                    f"[{index}].headline"
                ),
                item.get(
                    "headline",
                    ""
                )
            )


            validate_field(
                (
                    f"content_structure"
                    f"[{index}].body"
                ),
                item.get(
                    "body",
                    ""
                )
            )


    # --------------------------------------------------
    # CTA
    # --------------------------------------------------

    validate_field(
        "cta",
        content.get(
            "cta",
            ""
        )
    )


    # --------------------------------------------------
    # Visual Concept
    # --------------------------------------------------

    validate_field(
        "visual_concept",
        content.get(
            "visual_concept",
            ""
        )
    )


    # --------------------------------------------------
    # Visual Generation Prompt
    # --------------------------------------------------

    validate_field(
        "visual_generation_prompt",
        content.get(
            "visual_generation_prompt",
            ""
        )
    )


    # --------------------------------------------------
    # Result
    # --------------------------------------------------

    return {
        "valid": (
            len(
                issues
            ) == 0
        ),

        "status": (
            "PASS"
            if len(issues) == 0
            else "BLOCK"
        ),

        "issues": issues,

        "fields": field_results,
    }


# --------------------------------------------------
# Single Text Enforcement
# --------------------------------------------------

def enforce_language_quality(
    text: str,
    language: str
) -> dict[str, Any]:

    result = validate_language_quality(
        text=text,
        language=language
    )


    if not result[
        "valid"
    ]:

        messages = [
            issue[
                "message"
            ]

            for issue
            in result[
                "issues"
            ]
        ]


        raise LanguageValidationError(
            "Language-quality validation failed: "
            + "; ".join(
                messages
            )
        )


    return result


# --------------------------------------------------
# Full Campaign Enforcement
# --------------------------------------------------

def enforce_campaign_language_quality(
    content: dict,
    requested_languages
) -> dict[str, Any]:

    result = validate_campaign_language_quality(
        content=content,
        requested_languages=requested_languages
    )


    if not result[
        "valid"
    ]:

        messages = []


        for issue in result[
            "issues"
        ]:

            field = issue.get(
                "field",
                "unknown"
            )

            message = issue.get(
                "message",
                "Language-quality issue detected."
            )


            messages.append(
                f"{field}: {message}"
            )


        raise LanguageValidationError(
            "Campaign language-quality validation failed: "
            + "; ".join(
                messages
            )
        )


    return result


# --------------------------------------------------
# Manual Tests
# --------------------------------------------------

if __name__ == "__main__":

    samples = [

        (
            "SAFE ARABIC",
            "Arabic",
            (
                "أصبحت 7 خدمات تابعة لوزارة الزراعة "
                "متاحة الآن إلكترونياً عبر منصة «دولتي»."
            )
        ),

        (
            "BAD DAWLATI STRUCTURE",
            "Arabic",
            (
                "منصة «دولتي» تُعَدُّ الآن "
                "7 خدمات حكومية لقطاع الزراعة."
            )
        ),

        (
            "BAD ARABIC PHRASE",
            "Arabic",
            (
                "منصة «دولتي» هي خيارًا "
                "مُثَلَّثًا للخدمات الحكومية."
            )
        ),

        (
            "SAFE ENGLISH",
            "English",
            (
                "Seven Ministry of Agriculture services "
                "are now available online through Dawlati."
            )
        ),
    ]


    for label, language, text in samples:

        result = validate_language_quality(
            text=text,
            language=language
        )


        print(
            "\nTEST:",
            label
        )


        print(
            "STATUS:",
            result[
                "status"
            ]
        )


        for issue in result[
            "issues"
        ]:

            print(
                "ISSUE:",
                issue[
                    "message"
                ]
            )
            