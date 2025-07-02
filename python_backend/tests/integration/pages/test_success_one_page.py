import asyncio
import json
import logging
from collections import Counter
from unittest.mock import patch

import pytest
import sentry_sdk
from app.app import app
from httpx import ASGITransport, AsyncClient
from utils.constants import (
    HTTP_STATUS_ACCEPTED,
    LIST_FIELDS,
    NON_REQUIRED_FIELDS,
    OPTIONAL_FIELDS,
    REQUIRED_FIELDS,
    REQUIRED_JOB_METADATA_FIELDS,
    TOTAL_JOBS_PER_PAGE,
)

logger = logging.getLogger(__name__)

def assert_valid_job(job: dict) -> None:
    unknown_keys = set(job) - set(REQUIRED_FIELDS + NON_REQUIRED_FIELDS + LIST_FIELDS)
    assert not unknown_keys, f"Unexpected fields found: {unknown_keys}"

    for field in REQUIRED_FIELDS:
        value = job.get(field)
        assert value is not None, f"{field} is missing"
        assert isinstance(value, str), f"{field} is not a string"

    for field in NON_REQUIRED_FIELDS:
        val = job.get(field)
        if val is not None:
            assert isinstance(val, str), f"{field} should be a string if present"

    for field in LIST_FIELDS:
        val = job.get(field)
        assert isinstance(val, list), f"{field} should be a list"
        assert all(isinstance(item, str) for item in val), f"All items in {field} should be strings"

def run_job_health_checks(jobs_received: list) -> None:
    if not jobs_received:
        sentry_sdk.capture_message(
            "[SCRAPER HEALTHCHECK] No jobs were received — scraper may be broken or no listings matched.",
            level="warning"
        )
        logger.warning("No jobs were received. Skipping health checks.")
        return

    field_counter = Counter()
    for job in jobs_received:
        for field in REQUIRED_JOB_METADATA_FIELDS + OPTIONAL_FIELDS:
            val = job.get(field)
            if isinstance(val, str) and val.strip():
                field_counter[field] += 1

    for required_field in REQUIRED_JOB_METADATA_FIELDS:
        if field_counter[required_field] == 0:
            sentry_sdk.capture_message(
                f"[SCRAPER HEALTHCHECK] All jobs missing `{required_field}` — likely selector change.",
                level="error"
            )
        assert field_counter[required_field] > 0

    logger.info("Job metadata selector health checks passed.")


@pytest.mark.asyncio
async def test_scrape_and_send_jobs() -> None:
    jobs_received = []
    summary_reported = {}

    async def mock_validate_jobs(page_job_data: list):
        return page_job_data

    async def mock_insert_jobs_into_database(cleaned_jobs: dict, _page_num: int, job_count: int):
        jobs_received.extend(cleaned_jobs)
        return job_count + len(cleaned_jobs)

    async def mock_send_scrape_summary_to_node(summary: dict):
        summary_reported.update(summary)

    with patch("pages.listing_handler.validate_jobs", new=mock_validate_jobs), \
        patch("pages.listing_handler.insert_jobs_into_database", new=mock_insert_jobs_into_database), \
        patch("app.main.send_scrape_summary_to_node", new=mock_send_scrape_summary_to_node):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/start-scraping",
                json={"job_title": "software engineer", "location": "sydney", "max_pages": 1}
            )
    assert response.status_code == HTTP_STATUS_ACCEPTED
    await asyncio.sleep(90)

    logger.info("Received %s jobs", len(jobs_received))
    logger.info("Scrape Summary:\n%s", json.dumps(summary_reported, indent=2))

    for i, job in enumerate(jobs_received, start=1):
        logger.debug("--- Job %d ---\n%s", i, json.dumps(job, indent=2))
        assert_valid_job(job)

    run_job_health_checks(jobs_received)
    assert len(jobs_received) == TOTAL_JOBS_PER_PAGE


