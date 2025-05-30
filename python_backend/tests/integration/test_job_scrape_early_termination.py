import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from app import app  
from constants import SUCCESS, TERMINATE
from utils import is_job_within_date_range
from datetime import datetime, timedelta

# Global metadata simulation
metadata_global = {
    "http://seek.com.au/job1": (datetime.today() - timedelta(days=1)).strftime("%d/%m/%Y"),
    "http://seek.com.au/job2": (datetime.today() - timedelta(days=5)).strftime("%d/%m/%Y"),
    "http://seek.com.au/job3": (datetime.today() - timedelta(days=2)).strftime("%d/%m/%Y"),
}

@pytest.mark.asyncio
@patch("job_scrape.extract_total_job_count", return_value=3)
@patch("job_validate_and_db_insert.send_page_jobs_to_node", new_callable=AsyncMock)
@patch("job_scrape.process_job_with_backoff", new_callable=AsyncMock)
@patch("job_scrape.scrape_page_markdown", new_callable=AsyncMock)
@patch("job_scrape.process_markdown_to_job_links")
async def test_start_scraping_early_termination(
    mock_process_links,
    mock_scrape_page_markdown,
    mock_process_job_with_backoff,
    mock_send_page_jobs_to_node,
    mock_extract_total_job_count,
):
    jobs_received = []

    async def mock_send_page_jobs(job_data_list):
        jobs_received.extend(job_data_list)

    async def mock_process_job(job_link, count, crawler, location_search, terminate_event, day_range_limit, max_retries=3):
        posted_date = metadata_global.get(job_link)
        job_data = {
            "title": f"Job {count + 1}",
            "posted_date": posted_date,
        }
        if not is_job_within_date_range(job_data, day_range_limit):
            terminate_event.set()
            return {"status": TERMINATE, "job": None, "error": None}
        return {"status": SUCCESS, "job": job_data, "error": None}

    mock_send_page_jobs_to_node.side_effect = mock_send_page_jobs
    mock_scrape_page_markdown.return_value = ["dummy markdown content"]
    mock_process_links.return_value = [
        "http://seek.com.au/job1",
        "http://seek.com.au/job2",
        "http://seek.com.au/job3",
    ]
    mock_process_job_with_backoff.side_effect = mock_process_job

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/start-scraping",
            json={"job_title": "software engineer", "location": "sydney", "max_pages": 1, "day_range_limit": 3}
        )
        assert response.status_code == 202
        await asyncio.sleep(2)

    assert len(jobs_received) == 2
    titles = {job["title"] for job in jobs_received}
    assert titles == {"Job 1", "Job 3"}

    print(f"Test passed: Sent jobs within day range only.")
