import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.app import app
from httpx import ASGITransport, AsyncClient
from tzlocal import get_localzone
from utils.constants import HTTP_STATUS_ACCEPTED
from utils.context import ScrapeContext
from utils.utils import is_recent_job

local_tz = get_localzone()

metadata_global = {
    "http://seek.com.au/job1": (datetime.now(local_tz) - timedelta(days=1)).strftime("%d/%m/%Y"),
    "http://seek.com.au/job2": (datetime.now(local_tz) - timedelta(days=5)).strftime("%d/%m/%Y"),
    "http://seek.com.au/job3": (datetime.now(local_tz) - timedelta(days=2)).strftime("%d/%m/%Y"),
}

@pytest.mark.asyncio
@patch("app.main.scrape_pages", new_callable=AsyncMock)
@patch("app.main.get_total_pages", return_value=1)
@patch("app.main.get_total_job_count", return_value=10)
@patch("app.main.fetch_page_markdown", new_callable=AsyncMock)
@patch("app.main.AsyncWebCrawler.__aenter__", new_callable=AsyncMock)
async def test_start_scraping_early_termination(
    mock_aenter: AsyncMock,
    mock_fetch_markdown: AsyncMock,
    mock_get_total_job_count: MagicMock, # noqa: ARG001
    mock_get_total_pages: MagicMock, # noqa: ARG001
    mock_scrape_pages: AsyncMock
) -> None:
    jobs_received = []

    mock_aenter.return_value = MagicMock()
    mock_fetch_markdown.return_value = "mock markdown"

    async def mock_scrape_pages_func(_base_url: str, ctx: ScrapeContext, _total_pages: int) -> dict:
        job_urls = list(metadata_global.items())
        page_jobs = []
        terminate = False

        for idx, (_job_url, date_str) in enumerate(job_urls):
            job_data = {"title": f"Job {idx + 1}", "posted_date": date_str}
            if not is_recent_job(job_data, ctx.day_range_limit):
                terminate = True
                continue
            page_jobs.append(job_data)
            jobs_received.append(job_data)

        return {
            "job_count": len(jobs_received),
            "terminated_early": terminate,
        }

    mock_scrape_pages.side_effect = mock_scrape_pages_func

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/start-scraping",
            json={"job_title": "software engineer", "location": "sydney", "max_pages": 1, "day_range_limit": 3}
        )

        assert response.status_code == HTTP_STATUS_ACCEPTED
        await asyncio.sleep(1)

    titles = {job["title"] for job in jobs_received}
    assert titles == {"Job 1", "Job 3"}

