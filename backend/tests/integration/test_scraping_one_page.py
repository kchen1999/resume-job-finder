import pytest
import asyncio
import json
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from scraper.app import app  
from scraper.job_scrape import scrape_job_listing
from scraper.constants import REQUIRED_FIELDS, NON_REQUIRED_FIELDS, LIST_FIELDS, TOTAL_JOBS_PER_PAGE, OPTIONAL_FIELDS, REQUIRED_JOB_METADATA_FIELDS, DAY_RANGE_LIMIT
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
    scrape_results = {}

    async def mock_send_page_jobs_to_node(job_data_list):
        jobs_received.extend(job_data_list)

    async def mock_scrape_job_listing(base_url, location_search, max_pages=None, day_range_limit=DAY_RANGE_LIMIT):
        result = await scrape_job_listing(base_url, location_search, max_pages=1, day_range_limit=DAY_RANGE_LIMIT)
        scrape_results.update(result)
        return result

    with patch("scraper.validate_and_insert_db.send_page_jobs_to_node", new=mock_send_page_jobs_to_node), \
         patch("scraper.app.scrape_job_listing", new=mock_scrape_job_listing):
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
    print(json.dumps(scrape_results, indent=2))

    if not jobs_received:
        print("No jobs were received. Skipping health checks.")
        return 

    for i, job in enumerate(jobs_received, start=1):
        print(f"\n--- Job {i} ---")
        print(json.dumps(job, indent=2))
    
    for job in jobs_received:
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

    for required_job_metadata_field in REQUIRED_JOB_METADATA_FIELDS:
        assert field_counter[required_job_metadata_field] > 0, f"All jobs missing {required_job_metadata_field} — possible selector change."

    for optional_field in OPTIONAL_FIELDS:
        assert field_counter[optional_field] > 0, f"All jobs missing {optional_field} — possible selector change."

    print("Job metadata selector health checks passed.")
    assert len(jobs_received) == TOTAL_JOBS_PER_PAGE


