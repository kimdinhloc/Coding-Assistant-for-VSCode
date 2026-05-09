from __future__ import annotations

import base64
import hmac
import json
import os
from hashlib import sha256

API_KEYS = set(filter(None, os.getenv("API_KEYS", "dev-key").split(",")))
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")


def validate_api_key(key: str | None) -> bool:
    return bool(key and key in API_KEYS)


def decode_jwt(token: str | None) -> dict | None:
    if not token or token.count(".") != 2:
        return None
    header_b64, payload_b64, sig_b64 = token.split(".")
    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected = hmac.new(JWT_SECRET.encode(), signing_input, sha256).digest()
    try:
        got = base64.urlsafe_b64decode(sig_b64 + "==")
        if not hmac.compare_digest(expected, got):
            return None
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "==").decode())
    except Exception:
        return None
    return payload
