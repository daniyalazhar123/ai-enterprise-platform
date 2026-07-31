import time


def test_password_hashing_speed() -> None:
    from apps.api.app.auth.service.password import hash_password, verify_password

    password = "TestPassword123!"
    start = time.perf_counter()
    hashed = hash_password(password)
    duration = time.perf_counter() - start
    assert duration > 0.1

    start = time.perf_counter()
    result = verify_password(password, hashed)
    duration = time.perf_counter() - start
    assert result is True


def test_password_hashing_verification_fail() -> None:
    from apps.api.app.auth.service.password import hash_password, verify_password

    hashed = hash_password("CorrectPass123!")
    result = verify_password("WrongPass123!", hashed)
    assert result is False