from __future__ import annotations

import hashlib
import secrets
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from apps.api.app.core.config import settings
from apps.api.app.core.exceptions import ValidationError

_hasher = PasswordHasher(
    time_cost=settings.ARGON2_TIME_COST,
    memory_cost=settings.ARGON2_MEMORY_COST,
    parallelism=settings.ARGON2_PARALLELISM,
    hash_len=settings.ARGON2_HASH_LENGTH,
    salt_len=settings.ARGON2_SALT_LENGTH,
)


class PasswordValidationResult:
    def __init__(self, passes: bool, errors: list[str] | None = None) -> None:
        self.passes = passes
        self.errors = errors or []


_COMMON_PASSWORDS: set[str] | None = None


def _load_common_passwords() -> set[str]:
    global _COMMON_PASSWORDS
    if _COMMON_PASSWORDS is not None:
        return _COMMON_PASSWORDS
    _COMMON_PASSWORDS = {
        "password", "123456", "12345678", "qwerty", "abc123", "monkey",
        "123456789", "letmein", "111111", "1234", "1234567890", "dragon",
        "baseball", "iloveyou", "trustno1", "sunshine", "master", "welcome",
        "shadow", "ashley", "football", "jesus", "michael", "ninja",
        "mustang", "password1", "admin", "administrator", "passw0rd",
    }
    return _COMMON_PASSWORDS


def validate_password_policy(password: str) -> PasswordValidationResult:
    errors: list[str] = []

    if len(password) < settings.PASSWORD_MIN_LENGTH:
        errors.append(f"at least {settings.PASSWORD_MIN_LENGTH} characters")
    if len(password) > settings.PASSWORD_MAX_LENGTH:
        errors.append(f"at most {settings.PASSWORD_MAX_LENGTH} characters")

    char_classes = 0
    if any(c.isupper() for c in password):
        char_classes += 1
    if any(c.islower() for c in password):
        char_classes += 1
    if any(c.isdigit() for c in password):
        char_classes += 1
    special_chars = set("!@#$%^&*()_+-=[]{}|;':\",./<>?~")
    if any(c in special_chars for c in password):
        char_classes += 1
    if char_classes < 3:
        errors.append("at least 3 of 4 character classes")

    common = _load_common_passwords()
    if password.lower() in common:
        errors.append("password is too common")

    return PasswordValidationResult(passes=len(errors) == 0, errors=errors)


async def check_hibp(password: str) -> bool:
    if not settings.HIBP_ENABLED:
        return True
    try:
        sha1 = hashlib.sha1(password.encode()).hexdigest().upper()
        prefix = sha1[:5]
        suffix = sha1[5:]

        import httpx
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(
                f"{settings.PASSWORD_HIBP_API}{prefix}",
                headers={"hibp-api-key": settings.HIBP_API_KEY} if settings.HIBP_API_KEY else {},
            )
            if resp.status_code == 200:
                for line in resp.text.splitlines():
                    if line.startswith(suffix):
                        return False
        return True
    except Exception:
        return True


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        result = _hasher.verify(stored_hash, password)
        if _hasher.check_needs_rehash(stored_hash):
            return result
        return result
    except VerifyMismatchError:
        return False
    except (InvalidHashError, VerificationError):
        return False


async def validate_and_hash(password: str, user_id: str | None = None) -> str:
    result = validate_password_policy(password)
    if not result.passes:
        raise ValidationError("Password policy violation", {"errors": result.errors})
    pwned = await check_hibp(password)
    if not pwned:
        raise ValidationError("Password has been compromised in a data breach")
    return hash_password(password)