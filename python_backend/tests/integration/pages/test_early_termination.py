import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from app.app import app
from utils.utils import is_recent_job
from datetime import datetime, timedelta

# Global metadata simulation
metadata_global = {
    "http://seek.com.au/job1": (datetime.today() - timedelta(days=1)).strftime("%d/%m/%Y"),
    "http://seek.com.au/job2": (datetime.today() - timedelta(days=5)).strftime("%d/%m/%Y"),
    "http://seek.com.au/job3": (datetime.today() - timedelta(days=2)).strftime("%d/%m/%Y"),
}

@pytest.mark.asyncio
@patch("app.main.get_total_job_count", return_value=3)
@patch("app.main.fetch_page_markdown", new_callable=AsyncMock)
@patch("app.main.get_total_pages", return_value=1)
@patch("pages.listing_handler.process_job_listing_page", new_callable=AsyncMock)
@patch("app.main.send_scrape_summary_to_node", new_callable=AsyncMock)
@patch("app.main.AsyncWebCrawler.__aenter__", new_callable=AsyncMock)
@patch("app.main.AsyncWebCrawler.__aexit__", new_callable=AsyncMock)
async def test_start_scraping_early_termination(
    mock_aexit,
    mock_aenter,
    mock_send_summary,
    mock_process_page,
    mock_get_pages,
    mock_fetch_markdown,
    mock_get_total,
):
    jobs_received = []

    # Setup mocks
    mock_aenter.return_value = MagicMock()

    mock_fetch_markdown.return_value = "mock markdown"

    # Simulate early termination on page 1
    async def mock_process_job_listing_page(base_url, location_search, crawler, page_pool, page_num, job_count, day_range_limit):
        job_urls = list(metadata_global.items())
        page_jobs = []
        terminate = False

        for idx, (job_url, date_str) in enumerate(job_urls):
            job_data = {"title": f"Job {idx + 1}", "posted_date": date_str}
            if not is_recent_job(job_data, day_range_limit):
                terminate = True
                continue
            page_jobs.append(job_data)
            jobs_received.append(job_data)

        return {
            "job_count": len(jobs_received),
            "terminated_early": terminate,
        }

    mock_process_page.side_effect = mock_process_job_listing_page

    # Call endpoint
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/start-scraping",
            json={"job_title": "software engineer", "location": "sydney", "max_pages": 1, "day_range_limit": 3}
        )

        assert response.status_code == 202
        await asyncio.sleep(1) 

    # Assertions
    assert len(jobs_received) == 2  # job2 is outside range, triggers termination
    titles = {job["title"] for job in jobs_received}
    assert titles == {"Job 1", "Job 3"}

    print("Test passed: Early termination logic triggered correctly. Sent only recent jobs.")
