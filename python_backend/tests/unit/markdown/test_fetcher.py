import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from markdown.fetcher import fetch_page_markdown, fetch_job_markdown

@pytest.mark.asyncio
@patch("markdown.fetcher.pause_briefly", new_callable=AsyncMock)
@patch("markdown.fetcher.backoff_if_high_cpu", new_callable=AsyncMock)
async def test_fetch_page_markdown_success(mock_backoff, mock_pause):
    mock_crawler = MagicMock()
    mock_crawler.arun = AsyncMock(return_value=MagicMock(
        success=True,
        markdown="## Job Listings",
        status_code=200
    ))

    result = await fetch_page_markdown("https://seek.com.au", mock_crawler, page_num=1)
    assert result == "## Job Listings"
    mock_crawler.arun.assert_awaited_once()
    mock_pause.assert_awaited_once()
    mock_backoff.assert_awaited_once()

@pytest.mark.asyncio
@patch("markdown.fetcher.pause_briefly", new_callable=AsyncMock)
@patch("sentry_sdk.capture_exception")
@patch("sentry_sdk.push_scope")
async def test_fetch_page_markdown_arun_exception(mock_push_scope, mock_capture_exception, mock_pause):
    mock_crawler = MagicMock()
    mock_crawler.arun = AsyncMock(side_effect=Exception("Network error"))

    scope = MagicMock()
    mock_push_scope.return_value.__enter__.return_value = scope

    result = await fetch_page_markdown("https://seek.com.au", mock_crawler, page_num=2)
    assert result is None

    mock_capture_exception.assert_called_once()
    assert scope.set_tag.call_args_list[0][0][0] == "component"
    assert scope.set_extra.call_args_list[0][0][0] == "page_url"

@pytest.mark.asyncio
@patch("markdown.fetcher.pause_briefly", new_callable=AsyncMock)
@patch("markdown.fetcher.backoff_if_high_cpu", new_callable=AsyncMock)
@patch("sentry_sdk.capture_message")
@patch("sentry_sdk.push_scope")
async def test_fetch_page_markdown_failed_result(mock_push_scope, mock_capture_message, mock_backoff, mock_pause):
    mock_crawler = MagicMock()
    mock_crawler.arun = AsyncMock(return_value=MagicMock(
        success=False,
        markdown="",
        status_code=500,
        error_message="Internal error"
    ))

    scope = MagicMock()
    mock_push_scope.return_value.__enter__.return_value = scope

    result = await fetch_page_markdown("https://seek.com.au", mock_crawler, page_num=3)
    assert result is None
    mock_capture_message.assert_called_once()
    assert "Crawl failed" in mock_capture_message.call_args[0][0]

@pytest.mark.asyncio
@patch("markdown.fetcher.pause_briefly", new_callable=AsyncMock)
@patch("markdown.fetcher.backoff_if_high_cpu", new_callable=AsyncMock)
@patch("sentry_sdk.capture_message")
@patch("sentry_sdk.push_scope")
async def test_fetch_page_markdown_no_markdown(mock_push_scope, mock_capture_message, mock_backoff, mock_pause):
    mock_crawler = MagicMock()
    mock_crawler.arun = AsyncMock(return_value=MagicMock(
        success=True,
        markdown=None,
        status_code=200
    ))

    scope = MagicMock()
    mock_push_scope.return_value.__enter__.return_value = scope

    result = await fetch_page_markdown("https://seek.com.au", mock_crawler, page_num=4)
    assert result is None
    mock_capture_message.assert_called_once()
    assert "No markdown found" in mock_capture_message.call_args[0][0]

@pytest.mark.asyncio
@patch("markdown.fetcher.retry_with_backoff", new_callable=AsyncMock)
async def test_fetch_job_markdown_success(mock_retry_with_backoff):
    mock_markdown = "## This is a job posting"
    mock_retry_with_backoff.return_value = mock_markdown

    crawler = MagicMock()
    result = await fetch_job_markdown("https://seek.com/job/123", crawler)

    assert result == mock_markdown
    mock_retry_with_backoff.assert_awaited_once()

@pytest.mark.asyncio
@patch("markdown.fetcher.pause_briefly", new_callable=AsyncMock)
@patch("markdown.fetcher.backoff_if_high_cpu", new_callable=AsyncMock)
@patch("sentry_sdk.capture_message")
@patch("sentry_sdk.push_scope")
@patch("markdown.fetcher.retry_with_backoff")
async def test_fetch_job_markdown_arun_failure(
    mock_retry_with_backoff,
    mock_push_scope,
    mock_capture_message,
    mock_backoff,
    mock_pause,
):
    # Mock `retry_with_backoff` to execute `crawl` and simulate failure
    async def mock_retry(crawl, **kwargs):
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error_message = "Timeout"
        crawler = MagicMock()
        crawler.arun = AsyncMock(return_value=mock_result)
        return await crawl()

    mock_retry_with_backoff.side_effect = mock_retry

    scope = MagicMock()
    mock_push_scope.return_value.__enter__.return_value = scope

    mock_crawler = MagicMock()
    mock_crawler.arun = AsyncMock(return_value=MagicMock(success=False, error_message="Timeout"))

    result = await fetch_job_markdown("https://seek.com/job/456", mock_crawler)
    assert result is None

    mock_capture_message.assert_called_once()
    assert "Crawler failed" in mock_capture_message.call_args[0][0]

@pytest.mark.asyncio
@patch("markdown.fetcher.retry_with_backoff", new_callable=AsyncMock)
async def test_fetch_job_markdown_retries_exhausted(mock_retry_with_backoff):
    mock_retry_with_backoff.return_value = None

    crawler = MagicMock()
    result = await fetch_job_markdown("https://seek.com/job/789", crawler)

    assert result is None
    mock_retry_with_backoff.assert_awaited_once()
