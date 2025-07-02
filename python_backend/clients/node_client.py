import logging
import os
from pathlib import Path

import httpx
import sentry_sdk
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

if os.environ.get("FLY_REGION") is None:
    file_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(file_path)

def get_node_backend_url() -> str:
    return os.getenv("NODE_BACKEND_URL", "http://localhost:3000/api")

async def send_page_jobs_to_node(jobs: dict) -> None:
    url = get_node_backend_url()
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
            response = await client.post(
                f"{url}/jobs/page-batch",
                json={"jobs": jobs}
            )
            response.raise_for_status()
            logger.info("Successfully sent jobs to Node backend")
    except httpx.HTTPStatusError as exc:
        error_msg = f"Failed to insert jobs: {exc.response.status_code} - {exc.response.text}"
        logger.exception(error_msg)
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "send_page_jobs_to_node")
            scope.set_extra("status_code", exc.response.status_code)
            scope.set_extra("response_text", exc.response.text)
            scope.set_extra("job_count", len(jobs))
            sentry_sdk.capture_exception(exc)
        raise RuntimeError(error_msg) from exc
    except Exception as exc:
        logger.exception("Unexpected error while sending jobs")
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "send_page_jobs_to_node")
            scope.set_extra("job_count", len(jobs))
            sentry_sdk.capture_exception(exc)
        raise

# Note: This is a best-effort reporting step. Failure to send the summary does not interrupt scraping.
async def send_scrape_summary_to_node(summary: dict) -> None:
    url = get_node_backend_url()
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
            response = await client.post(
                f"{url}/jobs/scrape-summary",
                json=summary
            )
            response.raise_for_status()
            logger.info("Successfully sent scrape summary to Node backend")
    except httpx.HTTPStatusError as exc:
        error_msg = f"Failed to send scrape summary: {exc.response.status_code} - {exc.response.text}"
        logger.exception(error_msg)
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "send_scrape_summary_to_node")
            scope.set_extra("status_code", exc.response.status_code)
            scope.set_extra("response_text", exc.response.text)
            scope.set_extra("summary_keys", list(summary.keys()))
            sentry_sdk.capture_exception(exc)
    except Exception as exc:
        logger.exception("Unexpected error while sending scrape summary")
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "send_scrape_summary_to_node")
            scope.set_extra("summary_keys", list(summary.keys()))
            sentry_sdk.capture_exception(exc)
