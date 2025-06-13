import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from concurrency.batch_runner import process_jobs_concurrently, aggregate_job_results
from utils.constants import SUCCESS, TERMINATE, SKIPPED, ERROR

def test_aggregate_job_results_all_success():
    job_results = [
        {"status": SUCCESS, "job": {"title": "Job 1"}},
        {"status": SUCCESS, "job": {"title": "Job 2"}},
    ]
    final_jobs, early_termination, n_skipped, n_terminated = aggregate_job_results(job_results)
    
    assert final_jobs == [{"title": "Job 1"}, {"title": "Job 2"}]
    assert early_termination is False
    assert n_skipped == 0
    assert n_terminated == 0

def test_aggregate_job_results_mixed_statuses():
    job_results = [
        {"status": SUCCESS, "job": {"title": "Software Engineer"}},
        {"status": SKIPPED},
        {"status": TERMINATE},
        {"status": SUCCESS, "job": {"title": "Intern Engineer"}},
    ]
    final_jobs, early_termination, n_skipped, n_terminated = aggregate_job_results(job_results)

    assert final_jobs == [{"title": "Software Engineer"}, {"title": "Intern Engineer"}]
    assert early_termination is True
    assert n_skipped == 1
    assert n_terminated == 1


@pytest.mark.asyncio
@patch("concurrency.batch_runner.process_job_with_semaphore", new_callable=AsyncMock)
@patch("sentry_sdk.capture_message")
@patch("sentry_sdk.push_scope")
@patch("concurrency.batch_runner.pause_briefly", new_callable=AsyncMock)
@patch("concurrency.batch_runner.backoff_if_high_cpu", new_callable=AsyncMock)
async def test_process_jobs_concurrently_mixed_results(
    mock_backoff,
    mock_pause,
    mock_push_scope,
    mock_capture_message,
    mock_process_job
):
    # Arrange
    job_urls = [
        "https://seek.com.au/job/123", 
        "https://seek.com.au/job/456", 
        "https://seek.com.au/job/789", 
        "https://seek.com.au/job/999"
    ]
    crawler = AsyncMock()
    page_pool = AsyncMock()
    page_num = 3
    location_search = "Sydney"
    day_range_limit = 7

    mock_process_job.side_effect = [
        {"status": SUCCESS, "job": {"title": "Dev 1"}},
        {"status": SUCCESS, "job": {"title": "Dev 2"}},
        {"status": TERMINATE, "job": None, "job_metadata": {"posted_date": "01/01/2024"}},
        {"status": SKIPPED, "job": None, "job_metadata": {"posted_date": "01/01/2024"}},
    ]

    mock_scope = MagicMock()
    mock_push_scope.return_value.__enter__.return_value = mock_scope

    final_jobs, early_termination = await process_jobs_concurrently(
        job_urls, crawler, page_pool, page_num, location_search, day_range_limit
    )

    # Assert results
    assert final_jobs == [{"title": "Dev 1"}, {"title": "Dev 2"}]
    assert early_termination is True

    # Assert processing
    assert mock_process_job.await_count == 4

    # Assert Sentry scope tagging
    mock_scope.set_tag.assert_any_call("component", "process_jobs_concurrently")
    mock_scope.set_tag.assert_any_call("page_num", page_num)
    mock_scope.set_extra.assert_any_call("total_jobs_attempted", 4)
    mock_scope.set_extra.assert_any_call("jobs_successful", 2)
    mock_scope.set_extra.assert_any_call("jobs_skipped", 1)
    mock_scope.set_extra.assert_any_call("jobs_terminated_early", 1)
    mock_scope.set_extra.assert_any_call("early_termination", True)

    # Ensure capture message was sent
    mock_capture_message.assert_called_once_with("Scraping job batch completed", level="info")
