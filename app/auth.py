from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

PASSWORD_SCHEME = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 390_000
SALT_BYTES = 16
PASSWORD_BYTES = 12


def generate_password() -> str:
    return secrets.token_urlsafe(PASSWORD_BYTES)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    encoded_salt = base64.urlsafe_b64encode(salt).decode("ascii")
    encoded_digest = base64.urlsafe_b64encode(digest).decode("ascii")
    return f"{PASSWORD_SCHEME}${PASSWORD_ITERATIONS}${encoded_salt}${encoded_digest}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, iterations_text, encoded_salt, encoded_digest = password_hash.split("$", 3)
        iterations = int(iterations_text)
        salt = base64.urlsafe_b64decode(encoded_salt.encode("ascii"))
        expected_digest = base64.urlsafe_b64decode(encoded_digest.encode("ascii"))
    except (ValueError, TypeError):
        return False

    if scheme != PASSWORD_SCHEME:
        return False

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual_digest, expected_digest)

