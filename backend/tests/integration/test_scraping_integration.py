import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from scraper.app import app  
from scraper.job_scrape import scrape_job_listing
import asyncio
import json

def assert_valid_job(job):
    for field in ['title', 'company', 'classification', 'posted_date', 'posted_within', 'work_type', 'work_model']:
        assert isinstance(job.get(field), str) and job[field], f"{field} is missing or not a string"

    for field in ['description', 'logo_link', 'location', 'location_search', 'experience_level', 'salary', 'quick_apply_url', 'job_url']:
        val = job.get(field)
        assert val is None or isinstance(val, str), f"{field} should be a string or None"

    for field in ['responsibilities', 'requirements', 'other']:
        val = job.get(field)
        assert val is None or (isinstance(val, list) and all(isinstance(item, str) for item in val)), f"{field} should be a list of strings or None"


@pytest.mark.asyncio
async def test_scrape_and_send_jobs():
    jobs_received = []
    scrape_results = {}

    async def mock_send_page_jobs_to_node(job_data_list):
        jobs_received.extend(job_data_list)

    async def mock_scrape_job_listing(base_url, location_search, max_pages=None):
        result = await scrape_job_listing(base_url, location_search, max_pages=1)
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
            await asyncio.sleep(120) 

    assert jobs_received, "No jobs were sent to Node backend"
    print(f"Received {len(jobs_received)} jobs")

    for i, job in enumerate(jobs_received, start=1):
        print(f"\n--- Job {i} ---")
        print(json.dumps(job, indent=2))
    
    assert len(jobs_received) == 22 
    for job in jobs_received:
        assert_valid_job(job)

    print("\nScrape Summary:")
    print(json.dumps(scrape_results, indent=2))
    assert "message" in scrape_results
