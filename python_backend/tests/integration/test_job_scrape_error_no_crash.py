import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from app import app  

@pytest.mark.asyncio
@patch("job_scrape.AsyncWebCrawler.arun", new_callable=AsyncMock)
async def test_start_scraping_crawler_arun_crash(mock_arun):
    """
    Integration test to verify that if AsyncWebCrawler.arun raises an exception during scraping,
    the /start-scraping endpoint still responds successfully without crashing.
    This ensures robust error handling regardless of where errors occur in the scraping pipeline.
    """
    mock_arun.side_effect = RuntimeError("Simulated crawler arun crash")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/start-scraping",
            json={"job_title": "software engineer", "location": "sydney", "max_pages": 1, "day_range_limit": 3}
        )

    assert response.status_code == 202
    assert response.json()["status"] == "Scraping started"

    await asyncio.sleep(1)
    print("Test passed: the /start-scraping endpoint handles internal errors gracefully without failing.")
