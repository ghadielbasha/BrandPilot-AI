"""Safe bidirectional text formatting for BrandPilot's Streamlit UI."""

from __future__ import annotations

import html
import re

from validators.terminology_validator import normalize_global_terminology


ARABIC_FONT_STACK = '"Noto Sans Arabic", "Tajawal", "Arial", sans-serif'
_ARABIC_CHARACTER = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")
_LTR_TOKEN = re.compile(
    r"https?://[^\s<>]+|www\.[^\s<>]+|"
    r"\b[A-Za-z][A-Za-z0-9._-]*\b"
)


def correct_known_spelling(text: str) -> str:
    """Correct known display spelling errors without changing other wording."""
    return normalize_global_terminology(text)


def contains_arabic(text: str) -> bool:
    return bool(_ARABIC_CHARACTER.search(text))


def _escape_with_ltr_isolates(text: str) -> str:
    parts: list[str] = []
    position = 0
    for match in _LTR_TOKEN.finditer(text):
        parts.append(html.escape(text[position:match.start()]))
        parts.append(
            '<bdi dir="ltr">'
            f"{html.escape(match.group(0))}</bdi>"
        )
        position = match.end()
    parts.append(html.escape(text[position:]))
    return "".join(parts)


def format_text_html(text: object, *, direction: str | None = None) -> str:
    """Build an escaped RTL or LTR block suitable for Streamlit markdown."""
    value = correct_known_spelling(str(text or ""))
    resolved_direction = direction or ("rtl" if contains_arabic(value) else "ltr")
    if resolved_direction not in {"rtl", "ltr"}:
        raise ValueError("Text direction must be 'rtl' or 'ltr'.")

    alignment = "start"
    font = ARABIC_FONT_STACK if resolved_direction == "rtl" else '"Arial", sans-serif'
    body = (
        _escape_with_ltr_isolates(value)
        if resolved_direction == "rtl"
        else html.escape(value)
    )
    return (
        f'<div class="brandpilot-text brandpilot-{resolved_direction}" '
        f'lang="{"ar" if resolved_direction == "rtl" else "en"}" '
        f'dir="{resolved_direction}" style="direction: {resolved_direction}; '
        f'text-align: {alignment}; unicode-bidi: plaintext; '
        f'font-family: {font}; white-space: pre-wrap;">{body}</div>'
    )


def format_arabic_html(text: object) -> str:
    return format_text_html(text, direction="rtl")


def format_english_html(text: object) -> str:
    return format_text_html(text, direction="ltr")
