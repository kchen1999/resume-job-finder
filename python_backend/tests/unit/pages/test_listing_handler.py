import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pages.listing_handler import extract_job_urls_from_markdown, process_job_listing_page, scrape_pages

@patch("pages.listing_handler.extract_job_urls")
@patch("pages.listing_handler.logging")
def test_extract_job_urls_success(mock_logging, mock_extract_job_urls):
    markdown = "some markdown with links"
    job_urls = ["https://seek.com.au/job/123", "https://seek.com.au/job/456"]
    mock_extract_job_urls.return_value = job_urls

    result = extract_job_urls_from_markdown(markdown)

    assert result == job_urls

@patch("pages.listing_handler.extract_job_urls")
@patch("pages.listing_handler.logging")
def test_extract_job_urls_empty(mock_logging, mock_extract_job_urls):
    markdown = "markdown with no job links"
    mock_extract_job_urls.return_value = []

    result = extract_job_urls_from_markdown(markdown)

    assert result is None


@pytest.mark.asyncio
@patch("pages.listing_handler.backoff_if_high_cpu", new_callable=AsyncMock)
@patch("pages.listing_handler.pause_briefly", new_callable=AsyncMock)
@patch("pages.listing_handler.insert_jobs_into_database", new_callable=AsyncMock)
@patch("pages.listing_handler.validate_jobs", new_callable=AsyncMock)
@patch("pages.listing_handler.process_jobs_concurrently", new_callable=AsyncMock)
@patch("pages.listing_handler.extract_job_urls_from_markdown")
@patch("pages.listing_handler.fetch_page_markdown", new_callable=AsyncMock)
async def test_process_job_listing_page_success(
    mock_fetch_markdown,
    mock_extract_urls,
    mock_process_jobs,
    mock_validate_jobs,
    mock_insert_jobs,
    mock_pause,
    mock_backoff
):
    mock_fetch_markdown.return_value = "## Job Markdown"
    mock_extract_urls.return_value = ["https://seek.com.au/job/123"]
    mock_process_jobs.return_value = ([{"title": "Software Engineer"}], False)
    mock_validate_jobs.return_value = [{"title": "Software Engineer"}]
    mock_insert_jobs.return_value = 11  # updated job_count

    result = await process_job_listing_page(
        base_url="https://seek.com.au/jobs",
        location_search="Sydney",
        crawler=AsyncMock(),
        page_pool=AsyncMock(),
        page_num=1,
        job_count=10,
        day_range_limit=3
    )

    assert result == {'job_count': 11, 'terminated_early': False}
    mock_fetch_markdown.assert_awaited_once()
    mock_extract_urls.assert_called_once()
    mock_process_jobs.assert_awaited_once()
    mock_validate_jobs.assert_awaited_once()
    mock_insert_jobs.assert_awaited_once()

@pytest.mark.asyncio
@patch("pages.listing_handler.fetch_page_markdown", new_callable=AsyncMock)
async def test_process_job_listing_page_empty_markdown(mock_fetch_markdown):
    mock_fetch_markdown.return_value = ""

    result = await process_job_listing_page(
        base_url="https://seek.com.au/jobs",
        location_search="Sydney",
        crawler=AsyncMock(),
        page_pool=AsyncMock(),
        page_num=1,
        job_count=5,
        day_range_limit=3
    )

    assert result == {'job_count': 5, 'terminated_early': False}

@pytest.mark.asyncio
@patch("pages.listing_handler.sentry_sdk.capture_message")
@patch("pages.listing_handler.sentry_sdk.push_scope")
@patch("pages.listing_handler.extract_job_urls_from_markdown")
@patch("pages.listing_handler.fetch_page_markdown", new_callable=AsyncMock)
async def test_process_job_listing_page_no_urls_found(
    mock_fetch_markdown,
    mock_extract_urls,
    mock_push_scope,
    mock_capture_message
):
    mock_fetch_markdown.return_value = "some markdown but no urls"
    mock_extract_urls.return_value = []

    scope = MagicMock()
    mock_push_scope.return_value.__enter__.return_value = scope

    result = await process_job_listing_page(
        base_url="https://seek.com.au/jobs",
        location_search="Sydney",
        crawler=AsyncMock(),
        page_pool=AsyncMock(),
        page_num=2,
        job_count=7,
        day_range_limit=2
    )

    assert result == {'job_count': 7, 'terminated_early': False}
    mock_capture_message.assert_called_once_with(
        "No job urls found in markdown on page 2", level="warning"
    )
    scope.set_tag.assert_any_call("component", "process_job_listing_page")
    scope.set_tag.assert_any_call("page_num", 2)

@pytest.mark.asyncio
@patch("pages.listing_handler.backoff_if_high_cpu", new_callable=AsyncMock)
@patch("pages.listing_handler.pause_briefly", new_callable=AsyncMock)
@patch("pages.listing_handler.process_jobs_concurrently", new_callable=AsyncMock)
@patch("pages.listing_handler.extract_job_urls_from_markdown")
@patch("pages.listing_handler.fetch_page_markdown", new_callable=AsyncMock)
async def test_process_job_listing_page_terminated_early(
    mock_fetch_markdown,
    mock_extract_urls,
    mock_process_jobs,
    mock_pause,
    mock_backoff
):
    mock_fetch_markdown.return_value = "## markdown content"
    mock_extract_urls.return_value = ["https://seek.com.au/job/456"]
    mock_process_jobs.return_value = (None, True)  

    result = await process_job_listing_page(
        base_url="https://seek.com.au/jobs",
        location_search="Sydney",
        crawler=AsyncMock(),
        page_pool=AsyncMock(),
        page_num=3,
        job_count=4,
        day_range_limit=3
    )

    assert result == {'job_count': 4, 'terminated_early': True}
    mock_fetch_markdown.assert_awaited_once()
    mock_extract_urls.assert_called_once()
    mock_process_jobs.assert_awaited_once()

@pytest.mark.asyncio
@patch("pages.listing_handler.process_job_listing_page", new_callable=AsyncMock)
async def test_scrape_pages_normal_completion(mock_process_page):
    mock_process_page.side_effect = [
        {'job_count': 3, 'terminated_early': False},
        {'job_count': 6, 'terminated_early': False},
    ]

    result = await scrape_pages(
        base_url="https://seek.com.au/jobs",
        location_search="Sydney",
        crawler=AsyncMock(),
        page_pool=AsyncMock(),
        total_pages=2,
        day_range_limit=3
    )

    assert result == {
        'message': 'Scraped and inserted 6 jobs.',
        'terminated_early': False
    }

    assert mock_process_page.await_count == 2

@pytest.mark.asyncio
@patch("pages.listing_handler.process_job_listing_page", new_callable=AsyncMock)
async def test_scrape_pages_early_termination(mock_process_page):
    mock_process_page.side_effect = [
        {'job_count': 2, 'terminated_early': False},
        {'job_count': 2, 'terminated_early': True},
    ]

    result = await scrape_pages(
        base_url="https://seek.com.au/jobs",
        location_search="Brisbane",
        crawler=AsyncMock(),
        page_pool=AsyncMock(),
        total_pages=5,
        day_range_limit=5
    )

    assert result == {
        'message': 'Scraped and inserted 2 jobs. Early termination triggered on page 2 due to day range limit of 5 days.',
        'terminated_early': True
    }

    assert mock_process_page.await_count == 2



