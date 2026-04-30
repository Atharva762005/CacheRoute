"""
PropIQ Security — API Key Authentication + Rate Limiting
Simple but production-looking security layer for the demo.
"""

import os
import time
from collections import defaultdict
from fastapi import HTTPException, Security, Request
from fastapi.security.api_key import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=True)

# Load allowed API keys from environment (comma-separated)
env_keys = os.environ.get("PROPIQ_API_KEYS", "propiq-demo-2026")
VALID_API_KEYS = {k.strip() for k in env_keys.split(",") if k.strip()}

# In-memory rate limiting (per API key, per minute)
_rate_store: dict = defaultdict(list)
RATE_WINDOW_SECONDS = 60


def check_rate_limit(api_key: str, limit: int = 100):
    now = time.time()
    window_start = now - RATE_WINDOW_SECONDS
    # Clean old entries
    _rate_store[api_key] = [t for t in _rate_store[api_key] if t > window_start]
    if len(_rate_store[api_key]) >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {limit} requests/minute. Try again shortly."
        )
    _rate_store[api_key].append(now)


async def get_api_key(api_key_header: str = Security(API_KEY_HEADER)):
    """
    Strict API key validation using environment variables.
    No anonymous fallback allowed in enterprise mode.
    """
    if api_key_header not in VALID_API_KEYS:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key."
        )

    check_rate_limit(api_key_header, limit=200)
    return {"name": "Authenticated User", "tier": "enterprise"}