import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from concurrency.job_runner import process_job_with_retries, process_job_with_semaphore
from utils.constants import SKIPPED, SUCCESS, TERMINATE
from utils.context import ScrapeContext

EXPECTED_PAUSE_CALLS = 2

@pytest.mark.asyncio
@patch("concurrency.job_runner.enrich_job", new_callable=MagicMock)
@patch("concurrency.job_runner.extract_job_data", new_callable=AsyncMock)
@patch("concurrency.job_runner.pause_briefly", new_callable=AsyncMock)
@patch("concurrency.job_runner.backoff_if_high_cpu", new_callable=AsyncMock)
async def test_process_job_success(
    mock_backoff: AsyncMock,
    mock_pause: AsyncMock,
    mock_extract_job_data: AsyncMock,
    mock_enrich_job: MagicMock
) -> None:
    job_url = "https://seek.com.au/job/123"
    count = 1

    ctx = ScrapeContext(
        crawler=AsyncMock(),
        page_pool=AsyncMock(),
        location_search="Sydney",
        terminate_event=asyncio.Event(),
        semaphore=asyncio.Semaphore(1),
        day_range_limit=3,
    )

    mock_extract_job_data.return_value = {
        "status": SUCCESS,
        "job": {"title": "Software Engineer"},
        "job_metadata": {
            "logo_src": "https://logo.png",
            "posted_date": "05/05/2024",
            "company": "Google"
        }
    }

    enriched_job = {
        "title": "Software Engineer",
        "company": "Google",
        "job_url": job_url,
        "logo_src": "https://logo.png",
        "posted_date": "05/05/2024"
    }

    mock_enrich_job.return_value = enriched_job

    result = await process_job_with_retries(job_url, count, ctx)

    assert result["status"] == SUCCESS
    assert result["job"] == enriched_job

    assert mock_backoff.await_count == 1
    assert mock_pause.await_count == EXPECTED_PAUSE_CALLS

@pytest.mark.asyncio
@patch("concurrency.job_runner.extract_job_data", new_callable=AsyncMock)
@patch("concurrency.job_runner.pause_briefly", new_callable=AsyncMock)
@patch("concurrency.job_runner.backoff_if_high_cpu", new_callable=AsyncMock)
async def test_process_job_skipped(
    mock_backoff: AsyncMock,
    mock_pause: AsyncMock,
    mock_extract_job_data: AsyncMock
) -> None:
    job_url = "https://seek.com.au/job/123"
    count = 1

    ctx = ScrapeContext(
        crawler=AsyncMock(),
        page_pool=AsyncMock(),
        location_search="Sydney",
        terminate_event=asyncio.Event(),
        semaphore=asyncio.Semaphore(1),
        day_range_limit=3,
    )

    mock_extract_job_data.return_value = {
        "status": SKIPPED, "job": None, "job_metadata": None
    }

    result = await process_job_with_retries(job_url, count, ctx)

    assert result["status"] == SKIPPED
    assert result["job"] is None

    assert mock_backoff.await_count == 1
    assert mock_pause.await_count == 1

@pytest.mark.asyncio
@patch("concurrency.job_runner.extract_job_data", new_callable=AsyncMock)
@patch("concurrency.job_runner.pause_briefly", new_callable=AsyncMock)
@patch("concurrency.job_runner.backoff_if_high_cpu", new_callable=AsyncMock)
async def test_process_job_terminate(
    mock_backoff: AsyncMock,
    mock_pause: AsyncMock,
    mock_extract_job_data: AsyncMock
) -> None:
    job_url = "https://seek.com.au/job/123"
    count = 1

    ctx = ScrapeContext(
        crawler=AsyncMock(),
        page_pool=AsyncMock(),
        location_search="Sydney",
        terminate_event=asyncio.Event(),
        semaphore=asyncio.Semaphore(1),
        day_range_limit=3,
    )
    mock_extract_job_data.return_value = {
        "status": TERMINATE,
        "job": None,
        "job_metadata": {
            "logo_src": "https://logo.png",
            "posted_date": "05/05/2024",
            "salary": "$100k"
        }
    }

    result = await process_job_with_retries(job_url, count, ctx)

    assert result["status"] == TERMINATE
    assert result["job"] is None

    assert mock_backoff.await_count == 1
    assert mock_pause.await_count == 1

@pytest.mark.asyncio
@patch("concurrency.job_runner.process_job_with_retries", new_callable=AsyncMock)
@patch("concurrency.job_runner.pause_briefly", new_callable=AsyncMock)
@patch("concurrency.job_runner.backoff_if_high_cpu", new_callable=AsyncMock)
async def test_process_job_with_semaphore_early_terminate(
    mock_backoff: AsyncMock,
    mock_pause: AsyncMock,
    mock_process_job_with_retries: AsyncMock
) -> None:
    job_url = "https://seek.com.au/job/123"
    count = 1
    terminate_event = MagicMock()
    terminate_event.is_set.return_value = True

    ctx = ScrapeContext(
        crawler=AsyncMock(),
        page_pool=AsyncMock(),
        location_search="Sydney",
        terminate_event=terminate_event,
        semaphore=asyncio.Semaphore(1),
        day_range_limit=3,
    )

    result = await process_job_with_semaphore(job_url, count, ctx)

    assert result == {"status": TERMINATE, "job": None}
    mock_backoff.assert_not_called()
    mock_pause.assert_not_called()
    mock_process_job_with_retries.assert_not_called()

@pytest.mark.asyncio
@patch("concurrency.job_runner.process_job_with_retries", new_callable=AsyncMock)
@patch("concurrency.job_runner.pause_briefly", new_callable=AsyncMock)
@patch("concurrency.job_runner.backoff_if_high_cpu", new_callable=AsyncMock)
async def test_process_job_with_semaphore_success(
    mock_backoff: AsyncMock,
    mock_pause: AsyncMock,
    mock_process_job_with_retries: AsyncMock
) -> None:
    job_url = "https://seek.com.au/job/123"
    count = 1
    terminate_event = MagicMock()
    terminate_event.is_set.return_value = False

    mock_process_job_with_retries.return_value = {"status": SUCCESS, "job": {"title": "Dev"}}

    semaphore = AsyncMock()

    ctx = ScrapeContext(
        crawler=AsyncMock(),
        page_pool=AsyncMock(),
        location_search="Sydney",
        terminate_event=terminate_event,
        semaphore=semaphore,
        day_range_limit=3,
    )

    result = await process_job_with_semaphore(job_url, count, ctx)

    assert result["status"] == SUCCESS
    assert result["job"]["title"] == "Dev"
    mock_backoff.assert_awaited_once()
    mock_pause.assert_awaited_once()
    mock_process_job_with_retries.assert_awaited_once()
