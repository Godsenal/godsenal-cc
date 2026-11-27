import os
import secrets

from src.config.settings import API_KEY_ENV


def auth_header():
    return {"Authorization": f"Bearer {os.environ.get(API_KEY_ENV, 'test')}"}


def signed_headers():
    """Headers for a write request: auth plus a fresh request key."""
    return {**auth_header(), "Idempotency-Key": secrets.token_hex(16)}
