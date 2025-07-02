import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

import sentry_sdk

logger = logging.getLogger(__name__)

T = TypeVar("T")

async def retry_with_backoff(
    func: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    base_delay: float = 1.0,
    label: str = "operation"
) -> T | None:
    attempt = 0
    last_exception = None

    while attempt < max_retries:
        try:
            return await func()
        except (KeyboardInterrupt, asyncio.CancelledError, SystemExit):
            raise
        except Exception as e:
            last_exception = e
            attempt += 1
            logger.warning("[Attempt %s] %s failed: %s", attempt, label, e)

            if attempt < max_retries:
                await asyncio.sleep(base_delay * (2 ** (attempt - 1)))

    with sentry_sdk.push_scope() as scope:
        scope.set_tag("component", "retry_with_backoff")
        scope.set_extra("operation_label", label)
        scope.set_extra("last_exception", str(last_exception))
        sentry_sdk.capture_exception(last_exception)

    return None
