"""Password hashing and opaque bearer-session authentication."""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from database import delete_auth_session, save_auth_session, user_for_session


SESSION_DAYS = 7


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt_hex, digest_hex = encoded.split("$", 2)
        if algorithm != "scrypt":
            return False
        actual = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1
        )
        return hmac.compare_digest(actual, bytes.fromhex(digest_hex))
    except (ValueError, TypeError):
        return False


def issue_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)).isoformat()
    save_auth_session(_token_hash(token), user_id, expires_at)
    return token


def authenticate_token(token: str) -> dict | None:
    return user_for_session(_token_hash(token))


def revoke_token(token: str) -> None:
    delete_auth_session(_token_hash(token))


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
