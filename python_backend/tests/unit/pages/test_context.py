import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pages.pool import PagePool
from pages.context import setup_scraping_context, teardown_scraping_context
from utils.constants import CONCURRENT_JOBS_NUM

@pytest.mark.asyncio
@patch("pages.context.create_browser_context", new_callable=AsyncMock)
@patch("pages.context.PagePool")
@patch("pages.context.retry_with_backoff", new_callable=AsyncMock)
async def test_setup_scraping_context_success(mock_retry_with_backoff, mock_page_pool_cls, mock_create_browser_context):
    mock_playwright = MagicMock()
    mock_browser = MagicMock()
    mock_context = MagicMock()
    mock_create_browser_context.return_value = (mock_playwright, mock_browser, mock_context)

    mock_page_pool = AsyncMock()
    mock_page_pool_cls.return_value = mock_page_pool

    async def fake_retry_with_backoff(func, *args, **kwargs):
        return await func()
    mock_retry_with_backoff.side_effect = fake_retry_with_backoff

    result = await setup_scraping_context()

    mock_retry_with_backoff.assert_awaited()
    mock_page_pool_cls.assert_called_once_with(mock_context, max_pages=CONCURRENT_JOBS_NUM)
    mock_page_pool.init_pages.assert_awaited_once()

    assert result == (mock_playwright, mock_browser, mock_page_pool)


@pytest.mark.asyncio
@patch("pages.context.retry_with_backoff", new_callable=AsyncMock)
@patch("pages.context.logging")
async def test_setup_scraping_context_failure(mock_logging, mock_retry_with_backoff):
    mock_retry_with_backoff.return_value = None

    result = await setup_scraping_context()

    mock_retry_with_backoff.assert_awaited()
    mock_logging.error.assert_called_once_with("Failed to create scraping context after retries.")
    assert result == (None, None, None)

@pytest.mark.asyncio
@patch("pages.context.sentry_sdk.capture_exception")
@patch("pages.context.sentry_sdk.push_scope")
async def test_teardown_scraping_context_success(mock_push_scope, mock_capture_exception):
    playwright = AsyncMock()
    browser = AsyncMock()
    page_pool = AsyncMock()

    await teardown_scraping_context(playwright, browser, page_pool)

    page_pool.close_all.assert_awaited_once()
    browser.close.assert_awaited_once()
    playwright.stop.assert_awaited_once()
    mock_capture_exception.assert_not_called()

@pytest.mark.asyncio
@patch("pages.context.sentry_sdk.capture_exception")
@patch("pages.context.sentry_sdk.push_scope")
async def test_teardown_scraping_context_page_pool_error(mock_push_scope, mock_capture_exception):
    playwright = AsyncMock()
    browser = AsyncMock()
    page_pool = AsyncMock()
    page_pool.close_all.side_effect = Exception("Page pool error")

    await teardown_scraping_context(playwright, browser, page_pool)

    mock_capture_exception.assert_called_once()
    args, _ = mock_capture_exception.call_args
    assert "Page pool error" in str(args[0])

@pytest.mark.asyncio
@patch("pages.context.sentry_sdk.capture_exception")
@patch("pages.context.sentry_sdk.push_scope")
async def test_teardown_scraping_context_browser_error(mock_push_scope, mock_capture_exception):
    playwright = AsyncMock()
    browser = AsyncMock()
    page_pool = AsyncMock()
    browser.close.side_effect = Exception("Browser close error")

    await teardown_scraping_context(playwright, browser, page_pool)

    mock_capture_exception.assert_called_once()
    args, _ = mock_capture_exception.call_args
    assert "Browser close error" in str(args[0])

@pytest.mark.asyncio
@patch("pages.context.sentry_sdk.capture_exception")
@patch("pages.context.sentry_sdk.push_scope")
async def test_teardown_scraping_context_playwright_error(mock_push_scope, mock_capture_exception):
    playwright = AsyncMock()
    browser = AsyncMock()
    page_pool = AsyncMock()
    playwright.stop.side_effect = Exception("Playwright stop error")

    await teardown_scraping_context(playwright, browser, page_pool)

    mock_capture_exception.assert_called_once()
    args, _ = mock_capture_exception.call_args
    assert "Playwright stop error" in str(args[0])
