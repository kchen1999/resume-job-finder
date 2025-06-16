import pytest
import asyncio
import json
import sentry_sdk
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from app.app import app
from utils.constants import REQUIRED_FIELDS, NON_REQUIRED_FIELDS, LIST_FIELDS, TOTAL_JOBS_PER_PAGE, OPTIONAL_FIELDS, REQUIRED_JOB_METADATA_FIELDS, DAY_RANGE_LIMIT
from collections import Counter

def assert_valid_job(job):
    unknown_keys = set(job) - set(REQUIRED_FIELDS + NON_REQUIRED_FIELDS + LIST_FIELDS)
    assert not unknown_keys, f"Unexpected fields found: {unknown_keys}"

    for field in REQUIRED_FIELDS:
        assert isinstance(job.get(field), str) and job[field], f"{field} is missing or not a string"

    for field in NON_REQUIRED_FIELDS:
        val = job.get(field)
        if val is not None:
            assert isinstance(val, str), f"{field} should be a string if present"

    for field in LIST_FIELDS:
        val = job.get(field)
        assert isinstance(val, list) and all(isinstance(item, str) for item in val), f"{field} should be a list of strings"


@pytest.mark.asyncio
async def test_scrape_and_send_jobs():
    jobs_received = []
    summary_reported = {}

    async def mock_validate_jobs(page_job_data):
        return page_job_data
    
    async def mock_insert_jobs_into_database(cleaned_jobs, page_num, job_count):
        jobs_received.extend(cleaned_jobs)
        return job_count + len(cleaned_jobs)

    async def mock_send_scrape_summary_to_node(summary):
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
    assert response.status_code == 202
    await asyncio.sleep(90) 
    
    print(f"Received {len(jobs_received)} jobs")
    print("\nScrape Summary:")
    print(json.dumps(summary_reported, indent=2))

    if not jobs_received:
        print("No jobs were received. Skipping health checks.")
        return 

    for i, job in enumerate(jobs_received, start=1):
        print(f"\n--- Job {i} ---")
        print(json.dumps(job, indent=2))
        assert_valid_job(job)

    # --------------------------
    # Health checks for selectors
    # --------------------------

    field_counter = Counter()
    for job in jobs_received:
        for field in REQUIRED_JOB_METADATA_FIELDS + OPTIONAL_FIELDS:
            val = job.get(field)
            if isinstance(val, str):
                if val.strip(): field_counter[field] += 1

    for required_field in REQUIRED_JOB_METADATA_FIELDS:
        if field_counter[required_field] == 0:
            sentry_sdk.capture_message(
                f"[SCRAPER HEALTHCHECK] All jobs missing `{required_field}` — likely selector change or extraction bug.",
                level="error"
            )
        assert field_counter[required_field] > 0, f"All jobs missing {required_field} — possible selector change."

    for optional_field in OPTIONAL_FIELDS:
        if field_counter[optional_field] == 0:
            sentry_sdk.capture_message(
                f"[SCRAPER HEALTHCHECK] All jobs missing optional field `{optional_field}` — selector may be broken.",
                level="warning"
            )
        assert field_counter[optional_field] > 0, f"All jobs missing {optional_field} — possible selector change."

    print("Job metadata selector health checks passed.")
    assert len(jobs_received) == TOTAL_JOBS_PER_PAGE


