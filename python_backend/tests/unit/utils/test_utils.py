from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from freezegun import freeze_time
from tzlocal import get_localzone
from utils.constants import TOTAL_JOBS_PER_PAGE
from utils.utils import (
    backoff_if_high_cpu,
    clean_string,
    extract_job_urls,
    flatten_field,
    get_job_urls,
    get_posted_date,
    get_total_job_count,
    get_total_pages,
    is_recent_job,
    normalize_keys,
    pause_briefly,
    try_fix_missing_closing_brace,
)


@pytest.mark.asyncio
@patch("utils.utils.psutil.cpu_percent", return_value=95)
@patch("utils.utils.pause_briefly", new_callable=AsyncMock)
async def test_backoff_if_high_cpu_hard(mock_pause: AsyncMock, mock_cpu_percent: int) -> None:  # noqa: ARG001
    await backoff_if_high_cpu()
    mock_pause.assert_awaited_once_with(1.0, 3.0)

@pytest.mark.asyncio
@patch("utils.utils.psutil.cpu_percent", return_value=75)
@patch("utils.utils.pause_briefly", new_callable=AsyncMock)
async def test_backoff_if_high_cpu_soft(mock_pause: AsyncMock, mock_cpu_percent: int) -> None:  # noqa: ARG001
    await backoff_if_high_cpu()
    mock_pause.assert_awaited_once_with(0.25, 0.75)

@pytest.mark.asyncio
@patch("utils.utils.psutil.cpu_percent", return_value=50)
@patch("utils.utils.pause_briefly", new_callable=AsyncMock)
async def test_backoff_if_high_cpu_normal(mock_pause: AsyncMock, mock_cpu_percent: int) -> None:  # noqa: ARG001
    await backoff_if_high_cpu()
    mock_pause.assert_not_awaited()

@pytest.mark.asyncio
@patch("utils.utils.sentry_sdk.capture_exception")
@patch("utils.utils.sentry_sdk.push_scope")
@patch("utils.utils.psutil.cpu_percent", side_effect=RuntimeError("test error"))
@patch("utils.utils.pause_briefly", new_callable=AsyncMock)
async def test_backoff_if_high_cpu_exception(
    mock_pause: AsyncMock,
    mock_cpu: MagicMock, # noqa: ARG001
    mock_push_scope: MagicMock,
    mock_capture_exception: MagicMock
    ) -> None:
    mock_scope = MagicMock()
    mock_push_scope.return_value.__enter__.return_value = mock_scope

    await backoff_if_high_cpu()

    mock_capture_exception.assert_called_once()
    mock_scope.set_tag.assert_any_call("component", "backoff_if_high_cpu")
    mock_scope.set_extra.assert_any_call("soft_limit", 70)
    mock_scope.set_extra.assert_any_call("hard_limit", 90)
    mock_pause.assert_not_awaited()

@pytest.mark.asyncio
@patch("utils.utils.asyncio.sleep", new_callable=AsyncMock)
@patch("utils.utils.random.uniform", return_value=0.3)
async def test_pause_briefly_default(mock_uniform: MagicMock, mock_sleep: AsyncMock) -> None:
    await pause_briefly()
    mock_uniform.assert_called_once_with(0.2, 0.6)
    mock_sleep.assert_awaited_once_with(0.3)

@pytest.mark.asyncio
@patch("utils.utils.asyncio.sleep", new_callable=AsyncMock)
@patch("utils.utils.random.uniform", return_value=1.5)
async def test_pause_briefly_with_range(mock_uniform: MagicMock, mock_sleep: AsyncMock) -> None:
    await pause_briefly(1, 2.5)
    mock_uniform.assert_called_once_with(1, 2.5)
    mock_sleep.assert_awaited_once_with(1.5)

@freeze_time("2024-05-08")
def test_get_posted_date() -> None:
    assert get_posted_date(0) == "08/05/2024"
    assert get_posted_date(1) == "07/05/2024"
    assert get_posted_date(7) == "01/05/2024"
    assert get_posted_date(30) == "08/04/2024"

@pytest.mark.parametrize(("markdown", "expected"), [
    ("# 23 jobs listed", 23),
    ("#1,234 jobs found", 1234),
    ("# 1 job available", 1),
    ("# 1 jobs available", 1),
    ("# 0 jobs", 0),
    ("# no jobs here", 0),
    ("#5job listings", 0),
    ("Totally unrelated text", 0),
])
def test_get_total_job_count(markdown: str, expected: int) -> None:
    assert get_total_job_count(markdown) == expected

def test_get_total_job_count_from_file() -> None:
    file_path = Path(__file__).parent.parent.parent / "data" / "sample_first_page_markdown.md"
    with file_path.open(encoding="utf-8") as f:
        markdown = f.read()
    expected = 758
    assert get_total_job_count(markdown) == expected

def test_extract_job_urls_from_file() -> None:
    file_path = Path(__file__).parent.parent.parent / "data" / "sample_first_page_markdown.md"
    with file_path.open(encoding="utf-8") as f:
        markdown = f.read()
    job_urls = extract_job_urls(markdown)
    assert isinstance(job_urls, list)
    assert all(job_url.startswith("https://www.seek.com.au/job/") for job_url in job_urls)
    assert all("origin=cardTitle" in job_url for job_url in job_urls)
    assert len(job_urls) == TOTAL_JOBS_PER_PAGE

def test_extract_job_urls_no_urls() -> None:
    sample_markdown = "This is just some random text."
    result = extract_job_urls(sample_markdown)
    assert result == []

def test_get_job_urls() -> None:
    job_link = "https://www.seek.com.au/job/12345678?type=standard&ref=search-standalone&origin=cardTitle"
    expected_job_url = "https://www.seek.com.au/job/12345678"
    expected_quick_apply_url = "https://www.seek.com.au/job/12345678/apply"
    result = get_job_urls(job_link)
    assert result == [expected_job_url, expected_quick_apply_url]

def test_clean_string_removes_backslashes_and_newlines() -> None:
    raw_string = """{\n\\"key\\": \\"value\\"\n}"""
    expected = """{"key": "value"}"""
    result = clean_string(raw_string)
    assert result == expected

@pytest.mark.parametrize(("total_jobs", "pagesize", "max_pages", "expected"), [
    (88, TOTAL_JOBS_PER_PAGE, None, 4),
    (89, TOTAL_JOBS_PER_PAGE, None, 5),
    (88, TOTAL_JOBS_PER_PAGE, 3, 3),
    (20, TOTAL_JOBS_PER_PAGE, None, 1),
    (0, 10, None, 0),
    (88, TOTAL_JOBS_PER_PAGE, 5, 4),
])
def test_get_total_pages(total_jobs: int, pagesize: int, max_pages: int | None, expected: int) -> None:
    assert get_total_pages(total_jobs, pagesize, max_pages) == expected

@pytest.mark.parametrize(
    ("days_ago", "within_days", "expected"),
    [(3, 7, True), (0, 7, True), (7, 7, True), (8, 7, False), (30, 7, False)]
)
def test_is_recent_job_valid_dates(days_ago: int, within_days: int, expected: bool) -> None:
    local_tz = get_localzone()
    posted_date = (datetime.now(local_tz) - timedelta(days=days_ago)).strftime("%d/%m/%Y")
    job_data = {"posted_date": posted_date}
    assert is_recent_job(job_data, within_days=within_days) is expected

@patch("utils.utils.sentry_sdk.capture_exception")
@patch("utils.utils.sentry_sdk.push_scope")
def test_is_recent_job_invalid_date_format(mock_push_scope: MagicMock, mock_capture_exception: MagicMock) -> None:
    mock_scope = MagicMock()
    mock_push_scope.return_value.__enter__.return_value = mock_scope

    job_data = {"posted_date": "invalid-date-format"}
    result = is_recent_job(job_data, within_days=7)

    assert result is False
    mock_capture_exception.assert_called_once()
    mock_scope.set_tag.assert_called_with("component", "is_recent_job")
    mock_scope.set_extra.assert_any_call("posted_date_str", "invalid-date-format")
    mock_scope.set_extra.assert_any_call("job_metadata", job_data)

def test_flatten_field_with_list() -> None:
    mock_field = [
        "Work with suppliers to manage production timelines.",
        "Support product development from concept to launch.",
        "Ensure quality control standards are met."
    ]

    expected_output = (
        "Work with suppliers to manage production timelines. "
        "Support product development from concept to launch. "
        "Ensure quality control standards are met."
    )
    assert isinstance(mock_field, list)
    result = flatten_field(mock_field)
    assert result == expected_output
    assert isinstance(result, str)

def test_flatten_field_with_string() -> None:
    mock_field = "Strong communication and relationship-building skills."
    expected_output = "Strong communication and relationship-building skills."
    result = flatten_field(mock_field)
    assert result == expected_output

def test_flatten_field_with_empty() -> None:
    mock_field = []
    expected_output = ""
    result = flatten_field(mock_field)
    assert result == expected_output


@pytest.mark.parametrize(("input_dict", "expected_output"), [
    (
        {"Title": "Engineer", "Company Name": "Acme Corp"},
        {"title": "Engineer", "company_name": "Acme Corp"}
    ),
    (
        {"Experience-Level": "Mid", "Location ": "Sydney"},
        {"experience_level": "Mid", "location": "Sydney"}
    ),
    (
        {"   Work Type": "Full-time"},
        {"work_type": "Full-time"}
    ),
])
def test_normalize_keys(input_dict: dict, expected_output: dict) -> None:
    result = normalize_keys(input_dict)
    assert result == expected_output

@pytest.mark.parametrize(("input_str", "expected_output"), [
    (
        '{"key": "value"',
        '{"key": "value"}'
    ),
    (
        '{"key": "value"}',
        '{"key": "value"}'
    ),
])
def test_try_fix_missing_closing_brace(input_str: str, expected_output: str) -> None:
    assert try_fix_missing_closing_brace(input_str) == expected_output


