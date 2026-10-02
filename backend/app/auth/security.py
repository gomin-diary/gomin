"""Password hashes and opaque sessions; never persist the original token."""

import hashlib
import hmac
import secrets

N, R, P = 32768, 8, 3


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=N, r=R, p=P,
                            maxmem=64 * 1024 * 1024, dklen=32)
    return f"scrypt${N}${R}${P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt, expected = encoded.split("$")
        if algorithm != "scrypt" or (int(n), int(r), int(p)) != (N, R, P):
            return False
        salt_bytes, expected_bytes = bytes.fromhex(salt), bytes.fromhex(expected)
        if len(salt_bytes) != 16 or len(expected_bytes) != 32:
            return False
        digest = hashlib.scrypt(password.encode(), salt=salt_bytes, n=N, r=R, p=P,
                                maxmem=64 * 1024 * 1024, dklen=32)
        return hmac.compare_digest(digest, expected_bytes)
    except (ValueError, TypeError):
        return False


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def token_digest(token: str) -> str:
    # PostgREST bytea input format.
    return "\\x" + hashlib.sha256(token.encode()).hexdigest()


# Perform the same expensive verification for unknown email addresses.
DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))
