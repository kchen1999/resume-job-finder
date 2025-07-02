
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.main import scrape_job_listing


@pytest.mark.asyncio
@patch("sentry_sdk.capture_exception")
@patch("sentry_sdk.capture_message")
@patch("app.main.send_scrape_summary_to_node", new_callable=AsyncMock)
@patch("app.main.scrape_pages", new_callable=AsyncMock)
@patch("app.main.fetch_page_markdown", new_callable=AsyncMock)
@patch("app.main.AsyncWebCrawler")
@patch("app.main.setup_scraping_context", new_callable=AsyncMock)
@patch("app.main.teardown_scraping_context", new_callable=AsyncMock)
async def test_scrape_job_listing_happy_path(
    mock_teardown: AsyncMock,
    mock_setup: AsyncMock,
    mock_crawler_class: MagicMock,
    mock_fetch_markdown: AsyncMock,
    mock_scrape_pages: AsyncMock,
    mock_send_summary: AsyncMock,
    mock_capture_message: MagicMock, # noqa: ARG001
    mock_capture_exception: MagicMock, # noqa: ARG001
) -> None:
    mock_setup.return_value = ("playwright", "browser", "page_pool")
    mock_crawler_instance = AsyncMock()
    mock_crawler_class.return_value.__aenter__.return_value = mock_crawler_instance
    mock_fetch_markdown.return_value = "# 22 jobs listed"
    mock_scrape_pages.return_value = {
        "message": "Scraped and inserted 22 jobs.",
        "terminated_early": False,
    }
    result = await scrape_job_listing("https://seek.com.au", location_search="sydney")

    assert result == {
        "message": "Scraped and inserted 22 jobs.",
        "terminated_early": False,
    }
    mock_send_summary.assert_awaited_once()
    mock_teardown.assert_awaited_once()

@pytest.mark.asyncio
@patch("sentry_sdk.capture_exception")
@patch("sentry_sdk.capture_message")
@patch("app.main.send_scrape_summary_to_node", new_callable=AsyncMock)
@patch("app.main.fetch_page_markdown", new_callable=AsyncMock)
@patch("app.main.AsyncWebCrawler")
@patch("app.main.setup_scraping_context", new_callable=AsyncMock)
@patch("app.main.teardown_scraping_context", new_callable=AsyncMock)
async def test_scrape_job_listing_empty_markdown(
    mock_teardown: AsyncMock,
    mock_setup: AsyncMock,
    mock_crawler_class: MagicMock,
    mock_fetch_markdown: AsyncMock,
    mock_send_summary: AsyncMock,
    mock_capture_message: MagicMock, # noqa: ARG001
    mock_capture_exception: MagicMock, # noqa: ARG001
) -> None:
    mock_setup.return_value = ("playwright", "browser", "page_pool")
    mock_crawler_instance = AsyncMock()
    mock_crawler_class.return_value.__aenter__.return_value = mock_crawler_instance
    mock_fetch_markdown.return_value = None

    result = await scrape_job_listing("https://seek.com.au", location_search="sydney")

    assert result == {
        "message": "No job search markdown found. Scraped 0 jobs.",
        "terminated_early": False,
    }
    mock_fetch_markdown.assert_awaited_once()
    mock_send_summary.assert_awaited_once_with(result)
    mock_teardown.assert_awaited_once()

@pytest.mark.asyncio
@patch("sentry_sdk.capture_exception")
@patch("sentry_sdk.capture_message")
@patch("app.main.send_scrape_summary_to_node", new_callable=AsyncMock)
@patch("app.main.fetch_page_markdown", new_callable=AsyncMock)
@patch("app.main.AsyncWebCrawler")
@patch("app.main.setup_scraping_context", new_callable=AsyncMock)
@patch("app.main.teardown_scraping_context", new_callable=AsyncMock)
async def test_scrape_job_listing_zero_jobs(
    mock_teardown: AsyncMock,
    mock_setup: AsyncMock,
    mock_crawler_class: MagicMock,
    mock_fetch_markdown: AsyncMock,
    mock_send_summary: AsyncMock,
    mock_capture_message: MagicMock,
    mock_capture_exception: MagicMock,
) -> None:
    mock_setup.return_value = ("playwright", "browser", "page_pool")
    mock_crawler_instance = AsyncMock()
    mock_crawler_class.return_value.__aenter__.return_value = mock_crawler_instance
    mock_fetch_markdown.return_value = "# 0 jobs listed"

    result = await scrape_job_listing("https://seek.com.au", location_search="sydney")

    assert result == {
        "message": "No jobs found. Scraped 0 jobs.",
        "terminated_early": False,
    }
    mock_fetch_markdown.assert_awaited_once()
    mock_send_summary.assert_awaited_once_with(result)
    mock_capture_message.assert_not_called()
    mock_capture_exception.assert_not_called()
    mock_teardown.assert_awaited_once()


@pytest.mark.asyncio
@patch("sentry_sdk.capture_exception")
@patch("sentry_sdk.capture_message")
@patch("app.main.send_scrape_summary_to_node", new_callable=AsyncMock)
@patch("app.main.AsyncWebCrawler")
async def test_scrape_job_listing_crawler_init_fails(
    mock_crawler_class: MagicMock,
    mock_send_summary: AsyncMock,
    mock_capture_message: AsyncMock,
    mock_capture_exception: AsyncMock
) -> None:
    mock_crawler_class.return_value.__aenter__.side_effect = RuntimeError("crawler init failed")

    result = await scrape_job_listing("https://seek.com.au", location_search="sydney")

    assert "Fatal error during job scrape" in result["message"]
    mock_capture_exception.assert_called()
    mock_capture_message.assert_called_with("Failed initializing AsyncWebCrawler")
    mock_send_summary.assert_awaited_once_with(result)

@pytest.mark.asyncio
@patch("app.main.send_scrape_summary_to_node", new_callable=AsyncMock)
@patch("app.main.scrape_pages", new_callable=AsyncMock)
@patch("app.main.fetch_page_markdown", new_callable=AsyncMock)
@patch("app.main.AsyncWebCrawler")
@patch("app.main.setup_scraping_context", new_callable=AsyncMock)
@patch("app.main.teardown_scraping_context", new_callable=AsyncMock)
async def test_scrape_job_listing_multiple_pages_no_early_exit(
    mock_teardown: AsyncMock,
    mock_setup: AsyncMock,
    mock_crawler_class: MagicMock,
    mock_fetch_markdown: AsyncMock,
    mock_scrape_pages: AsyncMock,
    mock_send_summary: AsyncMock,
) -> None:
    mock_crawler_instance = AsyncMock()
    mock_crawler_class.return_value.__aenter__.return_value = mock_crawler_instance
    mock_setup.return_value = ("playwright", "browser", "page_pool")
    mock_fetch_markdown.return_value = "## 66 jobs listed"
    mock_scrape_pages.return_value = {
        "message": "Scraped and inserted 66 jobs.",
        "terminated_early": False
    }
    result = await scrape_job_listing("https://seek.com.au", location_search="sydney")

    assert result == {
        "message": "Scraped and inserted 66 jobs.",
        "terminated_early": False
    }
    assert mock_scrape_pages.await_count == 1
    mock_send_summary.assert_awaited_once_with(result)
    mock_teardown.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.main.send_scrape_summary_to_node", new_callable=AsyncMock)
@patch("app.main.scrape_pages", new_callable=AsyncMock)
@patch("app.main.fetch_page_markdown", new_callable=AsyncMock)
@patch("app.main.AsyncWebCrawler")
@patch("app.main.setup_scraping_context", new_callable=AsyncMock)
@patch("app.main.teardown_scraping_context", new_callable=AsyncMock)
async def test_scrape_job_listing_multiple_pages_with_early_exit(
    mock_teardown: AsyncMock,
    mock_setup: AsyncMock,
    mock_crawler_class: MagicMock,
    mock_fetch_markdown: AsyncMock,
    mock_scrape_pages: AsyncMock,
    mock_send_summary: AsyncMock,
) -> None:
    mock_crawler_instance = AsyncMock()
    mock_crawler_class.return_value.__aenter__.return_value = mock_crawler_instance
    mock_setup.return_value = ("playwright", "browser", "page_pool")
    mock_fetch_markdown.return_value = "## 66 jobs listed"
    mock_scrape_pages.return_value = {
         "message": (
            "Scraped and inserted 57 jobs. Early termination triggered on page 3 "
            "due to day range limit of 7 days."
        ),
        "terminated_early": True
    }

    result = await scrape_job_listing("https://seek.com.au", location_search="sydney")

    assert result == {
        "message": (
            "Scraped and inserted 57 jobs. Early termination triggered on page 3 due to "
            "day range limit of 7 days."
        ),
        "terminated_early": True
    }
    assert mock_scrape_pages.await_count == 1
    mock_send_summary.assert_awaited_once_with(result)
    mock_teardown.assert_awaited_once()


