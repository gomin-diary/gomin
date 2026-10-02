"""Secrets are never persisted in plaintext or included in diagnostics."""
import hashlib
import hmac
from uuid import UUID


def code_digest(key: str, request_id: UUID, email: str, code: str) -> str:
    message = f"signup\0{request_id}\0{email}\0{code}".encode()
    return "\\x" + hmac.new(key.encode(), message, hashlib.sha256).hexdigest()
