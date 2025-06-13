import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from concurrency.job_runner import process_job_with_retries, process_job_with_semaphore
from utils.constants import SUCCESS, TERMINATE, SKIPPED

@pytest.mark.asyncio
@patch("concurrency.job_runner.enrich_job", new_callable=MagicMock)
@patch("concurrency.job_runner.extract_job_data", new_callable=AsyncMock)
@patch("concurrency.job_runner.pause_briefly", new_callable=AsyncMock)
@patch("concurrency.job_runner.backoff_if_high_cpu", new_callable=AsyncMock)
async def test_process_job_success(
    mock_backoff, mock_pause, mock_extract_job_data, mock_enrich_job
):
    job_url = "https://seek.com.au/job/123"
    count = 1
    crawler = AsyncMock()
    page_pool = AsyncMock()
    location_search = "Sydney"
    terminate_event = MagicMock()
    day_range_limit = 3

    mock_extract_job_data.return_value = {
        "status": SUCCESS,
        "job": {"title": "Software Engineer"},
        "job_metadata": {"logo_src": "https://logo.png", "posted_date": "05/05/2024", "company": "Google"}
    }

    enriched_job = {
        "title": "Software Engineer",
        "company": "Google",
        "job_url": job_url,
        "logo_src": "https://logo.png",
        "posted_date": "05/05/2024"
    }

    mock_enrich_job.return_value = enriched_job

    result = await process_job_with_retries(
        job_url, count, crawler, page_pool, location_search, terminate_event, day_range_limit
    )

    assert result["status"] == SUCCESS
    assert result["job"] == enriched_job

@pytest.mark.asyncio
@patch("concurrency.job_runner.extract_job_data", new_callable=AsyncMock)
@patch("concurrency.job_runner.pause_briefly", new_callable=AsyncMock)
@patch("concurrency.job_runner.backoff_if_high_cpu", new_callable=AsyncMock)
async def test_process_job_skipped(mock_backoff, mock_pause, mock_extract_job_data):
    mock_extract_job_data.return_value = {
        "status": SKIPPED, "job": None, "job_metadata": None
    }

    result = await process_job_with_retries(
        "url", 1, AsyncMock(), AsyncMock(), "Sydney", MagicMock(), 3
    )

    assert result["status"] == SKIPPED
    assert result["job"] is None

@pytest.mark.asyncio
@patch("concurrency.job_runner.extract_job_data", new_callable=AsyncMock)
@patch("concurrency.job_runner.pause_briefly", new_callable=AsyncMock)
@patch("concurrency.job_runner.backoff_if_high_cpu", new_callable=AsyncMock)
async def test_process_job_terminate(mock_backoff, mock_pause, mock_extract_job_data):
    mock_extract_job_data.return_value = {
        "status": TERMINATE, "job": None, "job_metadata": {"logo_src": "https://logo.png", "posted_date": "05/05/2024", "salary": "$100k"}
    }

    result = await process_job_with_retries(
        "url", 1, AsyncMock(), AsyncMock(), "Sydney", MagicMock(), 3
    )

    assert result["status"] == TERMINATE
    assert result["job"] is None

@pytest.mark.asyncio
@patch("concurrency.job_runner.process_job_with_retries", new_callable=AsyncMock)
@patch("concurrency.job_runner.pause_briefly", new_callable=AsyncMock)
@patch("concurrency.job_runner.backoff_if_high_cpu", new_callable=AsyncMock)
async def test_process_job_with_semaphore_early_terminate(mock_backoff, mock_pause, mock_process_job_with_retries):
    job_url = "https://seek.com.au/job/123"
    terminate_event = MagicMock()
    terminate_event.is_set.return_value = True

    result = await process_job_with_semaphore(
        job_url, 1, AsyncMock(), AsyncMock(), "Sydney", terminate_event, 3, AsyncMock()
    )

    assert result == {"status": TERMINATE, "job": None}
    mock_backoff.assert_not_called()
    mock_pause.assert_not_called()
    mock_process_job_with_retries.assert_not_called()

@pytest.mark.asyncio
@patch("concurrency.job_runner.process_job_with_retries", new_callable=AsyncMock)
@patch("concurrency.job_runner.pause_briefly", new_callable=AsyncMock)
@patch("concurrency.job_runner.backoff_if_high_cpu", new_callable=AsyncMock)
async def test_process_job_with_semaphore_success(mock_backoff, mock_pause, mock_process_job_with_retries):
    job_url = "https://seek.com.au/job/123"
    terminate_event = MagicMock()
    terminate_event.is_set.return_value = False

    mock_process_job_with_retries.return_value = {"status": SUCCESS, "job": {"title": "Dev"}}

    semaphore = AsyncMock()

    result = await process_job_with_semaphore(
        job_url, 1, AsyncMock(), AsyncMock(), "Sydney", terminate_event, 3, semaphore
    )

    assert result["status"] == SUCCESS
    assert result["job"]["title"] == "Dev"
    mock_backoff.assert_awaited_once()
    mock_pause.assert_awaited_once()
    mock_process_job_with_retries.assert_awaited_once()
