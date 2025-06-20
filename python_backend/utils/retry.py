import asyncio
import logging

logger = logging.getLogger(__name__)

from collections.abc import Callable
from typing import Any

import sentry_sdk


async def retry_with_backoff(
    func: Callable[[], Any],
    max_retries: int = 3,
    base_delay: float = 1.0,
    label: str = "operation"
):
    attempt = 0
    last_exception = None

    while attempt < max_retries:
        try:
            return await func()
        except Exception as e:
            last_exception = e
            attempt += 1
            logger.warning(f"[Attempt {attempt}] {label} failed: {e}")

            if attempt < max_retries:
                await asyncio.sleep(base_delay * (2 ** (attempt - 1)))

    with sentry_sdk.push_scope() as scope:
        scope.set_tag("component", "retry_with_backoff")
        scope.set_extra("operation_label", label)
        scope.set_extra("last_exception", str(last_exception))
        sentry_sdk.capture_exception(last_exception)

    return None
