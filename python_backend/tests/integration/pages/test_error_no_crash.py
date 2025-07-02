import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from app.app import app
from httpx import ASGITransport, AsyncClient
from utils.constants import HTTP_STATUS_ACCEPTED


@pytest.mark.asyncio
@patch("app.main.AsyncWebCrawler.__aenter__", new_callable=AsyncMock)
async def test_start_scraping_crawler_arun_crash(mock_aenter: AsyncMock) -> None:
    """Integration test that ensures AsyncWebCrawler.arun errors do not crash the scraping endpoint.

    The /start-scraping endpoint should still respond successfully even if an exception is raised.
    This ensures robust error handling regardless of where errors occur in the scraping pipeline.
    """
    mock_aenter.side_effect = RuntimeError("Simulated crawler arun crash")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/start-scraping",
            json={"job_title": "software engineer", "location": "sydney", "max_pages": 1, "day_range_limit": 3}
        )

    assert response.status_code == HTTP_STATUS_ACCEPTED
    assert response.json()["status"] == "Manual scraping started"

    await asyncio.sleep(1)
