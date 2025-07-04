from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from clients.node_client import delete_all_jobs_from_node, send_page_jobs_to_node
from httpx import HTTPStatusError, Request, Response


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
async def test_send_page_jobs_to_node_success(mock_post: AsyncMock) -> None:
    mock_post.return_value.status_code = 200
    mock_post.return_value.raise_for_status = MagicMock()

    await send_page_jobs_to_node([{"title": "test job"}])
    mock_post.assert_awaited_once()
    mock_post.return_value.raise_for_status.assert_called_once()

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
async def test_send_page_jobs_to_node_http_error(mock_post: AsyncMock) -> None:
    request = Request("POST", "http://localhost:3000/api/jobs/page-batch")
    response = Response(400, request=request, content=b"Bad job data")
    response.raise_for_status = lambda: (_ for _ in ()).throw(
        HTTPStatusError("Bad Request", request=request, response=response)
    )
    mock_post.return_value = response

    with pytest.raises(RuntimeError) as exc_info:
        await send_page_jobs_to_node([{"title": "bad job"}])

    assert "Failed to insert jobs: 400 - Bad job data" in str(exc_info.value)

@pytest.mark.asyncio
@patch("httpx.AsyncClient.delete", new_callable=AsyncMock)
@patch("sentry_sdk.capture_message")
async def test_delete_all_jobs_from_node_success(mock_capture_message: MagicMock, mock_delete: AsyncMock) -> None:
    mock_delete.return_value.status_code = 200
    mock_delete.return_value.json = MagicMock(return_value={"deleted": 42})
    mock_delete.return_value.raise_for_status = MagicMock()

    await delete_all_jobs_from_node()

    mock_delete.assert_awaited_once()
    mock_delete.return_value.raise_for_status.assert_called_once()
    mock_capture_message.assert_called_once_with(
        "Successfully deleted jobs from Node backend", level="info"
    )

@pytest.mark.asyncio
@patch("httpx.AsyncClient.delete", new_callable=AsyncMock)
async def test_delete_all_jobs_from_node_http_error(mock_delete: AsyncMock) -> None:
    url = "http://localhost:3000/api/jobs"
    request = Request("DELETE", url)
    response = Response(404, request=request, content=b"Not Found")
    response.raise_for_status = lambda: (_ for _ in ()).throw(
        HTTPStatusError("Not Found", request=request, response=response)
    )
    mock_delete.return_value = response

    with pytest.raises(RuntimeError) as exc_info:
        await delete_all_jobs_from_node()

    assert "Failed to delete jobs: 404 - Not Found" in str(exc_info.value)

