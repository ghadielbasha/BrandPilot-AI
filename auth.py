"""Local password authentication and role definitions."""

from __future__ import annotations

import re
from enum import StrEnum

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError


class Role(StrEnum):
    ADMIN = "ADMIN"
    EDITOR = "EDITOR"
    REVIEWER = "REVIEWER"


_HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


def validate_password_strength(password: str) -> None:
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters.")
    if not re.search(r"[A-Z]", password) or not re.search(r"[a-z]", password):
        raise ValueError("Password must contain upper- and lowercase letters.")
    if not re.search(r"\d", password) or not re.search(r"[^\w\s]", password):
        raise ValueError("Password must contain a number and a symbol.")


def hash_password(password: str) -> str:
    validate_password_strength(password)
    return _HASHER.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _HASHER.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError, TypeError):
        return False

