"""Pure UI policy helpers; server-side authorization remains authoritative."""

from auth import Role


def can_save_draft(role: str) -> bool:
    return role in {Role.ADMIN.value, Role.EDITOR.value}


def content_is_compliant(content: dict | None) -> bool:
    if not isinstance(content, dict):
        return False
    return all(
        (content.get(key) or {}).get("status") == "PASS"
        for key in (
            "security_validation",
            "terminology_validation",
            "factual_validation",
            "language_validation",
        )
    )
