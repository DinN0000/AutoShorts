"""Shared helpers for platform uploaders: secrets loading and retry logic."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

RETRY_DELAYS = [5, 10, 20]


def load_secrets(platform: str) -> dict[str, Any]:
    """Load platform secrets: env vars first, then config/secrets.yaml fallback.

    Environment variable names follow the pattern:
        {PLATFORM}_{KEY} e.g. YOUTUBE_CLIENT_ID, TIKTOK_ACCESS_TOKEN
    """
    env_prefix = platform.upper() + "_"
    env_secrets: dict[str, Any] = {}
    for key, value in os.environ.items():
        if key.startswith(env_prefix):
            field = key[len(env_prefix):].lower()
            env_secrets[field] = value
    if env_secrets:
        return env_secrets

    secrets_path = Path(__file__).resolve().parent.parent.parent.parent / "config" / "secrets.yaml"
    try:
        with open(secrets_path) as f:
            data = yaml.safe_load(f) or {}
        return data.get(platform, {})
    except (FileNotFoundError, yaml.YAMLError):
        return {}


async def retry_upload(coro_factory, platform: str) -> Any:
    """Retry an async upload with exponential backoff (5s, 10s, 20s).

    Args:
        coro_factory: Callable that returns a new coroutine for each attempt.
        platform: Platform name for logging.

    Returns:
        The result of the successful coroutine call.

    Raises:
        The last exception if all retries are exhausted.
    """
    last_exc: Optional[Exception] = None
    for attempt, delay in enumerate(RETRY_DELAYS, 1):
        try:
            return await coro_factory()
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "%s upload attempt %d/%d failed: %s. Retrying in %ds...",
                platform, attempt, len(RETRY_DELAYS), exc, delay,
            )
            await asyncio.sleep(delay)

    # Final attempt (no delay after)
    try:
        return await coro_factory()
    except Exception as exc:
        logger.error("%s upload failed after all retries: %s", platform, exc)
        raise exc from last_exc
