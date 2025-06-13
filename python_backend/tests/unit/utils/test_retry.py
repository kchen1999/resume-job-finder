import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pages.context import retry_with_backoff  


@pytest.mark.asyncio
async def test_retry_with_backoff_success_first_try():
    mock_func = AsyncMock(return_value="success")

    result = await retry_with_backoff(mock_func, max_retries=3, base_delay=0.01, label="test_op")

    assert result == "success"
    mock_func.assert_awaited_once()


@pytest.mark.asyncio
async def test_retry_with_backoff_succeeds_after_retries():
    mock_func = AsyncMock(side_effect=[Exception("fail 1"), Exception("fail 2"), "success"])

    with patch("asyncio.sleep", new_callable=AsyncMock): 
        result = await retry_with_backoff(mock_func, max_retries=5, base_delay=0.01, label="retry_test")

    assert result == "success"
    assert mock_func.await_count == 3


@pytest.mark.asyncio
@patch("sentry_sdk.capture_exception")
@patch("sentry_sdk.push_scope")
async def test_retry_with_backoff_fails_all_attempts(mock_push_scope, mock_capture_exception):
    mock_func = AsyncMock(side_effect=Exception("final failure"))

    mock_scope = MagicMock()
    mock_push_scope.return_value.__enter__.return_value = mock_scope

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await retry_with_backoff(mock_func, max_retries=3, base_delay=0.01, label="failure_test")

    assert result is None
    assert mock_func.await_count == 3
    mock_capture_exception.assert_called_once()
    assert mock_scope.set_tag.call_args[0] == ("component", "retry_with_backoff")
    assert mock_scope.set_extra.call_args_list[0][0][0] == "operation_label"
