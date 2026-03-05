from __future__ import annotations

import hmac


def is_valid_api_key(candidate: str, allowed_keys: tuple[str, ...]) -> bool:
    """Validate API keys with constant-time comparisons."""
    return any(hmac.compare_digest(candidate, key) for key in allowed_keys)
