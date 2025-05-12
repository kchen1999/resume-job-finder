import pytest
from httpx import Response, Request, HTTPStatusError
from unittest.mock import AsyncMock, MagicMock, patch
from scraper.node_client import send_page_jobs_to_node

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
async def test_send_page_jobs_to_node_success(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.raise_for_status = MagicMock()

    await send_page_jobs_to_node([{"title": "test job"}])
    mock_post.assert_awaited_once()
    mock_post.return_value.raise_for_status.assert_called_once()

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
async def test_send_page_jobs_to_node_http_error(mock_post, caplog):
    request = Request("POST", "http://localhost:3000/api/jobs/page-batch")
    response = Response(400, request=request, content=b"Bad job data")

    mock_post.return_value = response
    with pytest.raises(HTTPStatusError):
        await send_page_jobs_to_node([{"title": "bad job"}])
    assert "Failed to insert jobs: 400 - Bad job data" in caplog.text
