import pytest
import os
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
from freezegun import freeze_time
from utils.utils import get_job_urls, get_total_pages, backoff_if_high_cpu, clean_string, get_posted_date, get_total_job_count, extract_job_urls, is_recent_job, flatten_field, pause_briefly

@pytest.mark.asyncio
@patch("utils.utils.psutil.cpu_percent", return_value=95)
@patch("utils.utils.pause_briefly", new_callable=AsyncMock)
async def test_backoff_if_high_cpu_hard(mock_pause, mock_cpu):
    await backoff_if_high_cpu()
    mock_pause.assert_awaited_once_with(1.0, 3.0)

@pytest.mark.asyncio
@patch("utils.utils.psutil.cpu_percent", return_value=75)
@patch("utils.utils.pause_briefly", new_callable=AsyncMock)
async def test_backoff_if_high_cpu_soft(mock_pause, mock_cpu):
    await backoff_if_high_cpu()
    mock_pause.assert_awaited_once_with(0.25, 0.75)

@pytest.mark.asyncio
@patch("utils.utils.psutil.cpu_percent", return_value=50)
@patch("utils.utils.pause_briefly", new_callable=AsyncMock)
async def test_backoff_if_high_cpu_normal(mock_pause, mock_cpu):
    await backoff_if_high_cpu()
    mock_pause.assert_not_awaited()

@pytest.mark.asyncio
@patch("utils.utils.sentry_sdk.capture_exception")
@patch("utils.utils.sentry_sdk.push_scope")
@patch("utils.utils.psutil.cpu_percent", side_effect=RuntimeError("test error"))
@patch("utils.utils.pause_briefly", new_callable=AsyncMock)
async def test_backoff_if_high_cpu_exception(mock_pause, mock_cpu, mock_push_scope, mock_capture_exception):
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
async def test_pause_briefly_default(mock_uniform, mock_sleep):
    await pause_briefly() 
    mock_uniform.assert_called_once_with(0.2, 0.6)
    mock_sleep.assert_awaited_once_with(0.3)

@pytest.mark.asyncio
@patch("utils.utils.asyncio.sleep", new_callable=AsyncMock)
@patch("utils.utils.random.uniform", return_value=1.5)
async def test_pause_briefly_with_range(mock_uniform, mock_sleep):
    await pause_briefly(1, 2.5) 
    mock_uniform.assert_called_once_with(1, 2.5)
    mock_sleep.assert_awaited_once_with(1.5)

@freeze_time("2024-05-08")
def test_get_posted_date():
    assert get_posted_date(0) == "08/05/2024"
    assert get_posted_date(1) == "07/05/2024"
    assert get_posted_date(7) == "01/05/2024"
    assert get_posted_date(30) == "08/04/2024"

@pytest.mark.parametrize("markdown, expected", [ 
    ("# 23 jobs listed", 23),
    ("#1,234 jobs found", 1234),
    ("# 1 job available", 1),
    ("# 1 jobs available", 1),
    ("# 0 jobs", 0),
    ("# no jobs here", 0),  
    ("#5job listings", 0),
    ("Totally unrelated text", 0),  
])
def test_get_total_job_count(markdown, expected):
    assert get_total_job_count(markdown) == expected

def test_get_total_job_count_from_file():
    file_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sample_first_page_markdown.md")
    with open(file_path, "r", encoding="utf-8") as f:
        markdown = f.read()
    expected = 758
    assert get_total_job_count(markdown) == expected

def test_extract_job_urls_from_file():
    file_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sample_first_page_markdown.md")
    with open(file_path, "r", encoding="utf-8") as f:
        markdown = f.read()
    job_urls = extract_job_urls(markdown)
    assert isinstance(job_urls, list)
    assert all(job_url.startswith("https://www.seek.com.au/job/") for job_url in job_urls)
    assert all("origin=cardTitle" in job_url for job_url in job_urls)
    assert len(job_urls) == 22  

def test_extract_job_urls_no_urls():
    sample_markdown = "This is just some random text."
    result = extract_job_urls(sample_markdown)
    assert result == []

def test_get_job_urls():
    job_link = "https://www.seek.com.au/job/12345678?type=standard&ref=search-standalone&origin=cardTitle"
    expected_job_url = "https://www.seek.com.au/job/12345678"
    expected_quick_apply_url = "https://www.seek.com.au/job/12345678/apply"
    result = get_job_urls(job_link)
    assert result == [expected_job_url, expected_quick_apply_url]

def test_clean_string_removes_backslashes_and_newlines():
    raw_string = """{\n\\"key\\": \\"value\\"\n}"""
    expected = """{"key": "value"}""" 
    result = clean_string(raw_string)
    assert result == expected

@pytest.mark.parametrize("total_jobs, pagesize, max_pages, expected", [
    (88, 22, None, 4),        
    (89, 22, None, 5),           
    (88, 22, 3, 3),                
    (20, 22, None, 1),            
    (0, 10, None, 0),              
    (88, 22, 5, 4),                
])
def test_get_total_pages(total_jobs, pagesize, max_pages, expected):
    assert get_total_pages(total_jobs, pagesize, max_pages) == expected

@pytest.mark.parametrize(
    "days_ago, within_days, expected",
    [(3, 7, True), (0, 7, True), (7, 7, True), (8, 7, False), (30, 7, False)]
)
def test_is_recent_job_valid_dates(days_ago, within_days, expected):
    posted_date = (datetime.today() - timedelta(days=days_ago)).strftime("%d/%m/%Y")
    job_data = {"posted_date": posted_date}
    assert is_recent_job(job_data, within_days=within_days) is expected

@patch("utils.utils.sentry_sdk.capture_exception")
@patch("utils.utils.sentry_sdk.push_scope")
def test_is_recent_job_invalid_date_format(mock_push_scope, mock_capture_exception):
    mock_scope = MagicMock()
    mock_push_scope.return_value.__enter__.return_value = mock_scope

    job_data = {"posted_date": "invalid-date-format"}
    result = is_recent_job(job_data, within_days=7)

    assert result is False
    mock_capture_exception.assert_called_once()
    mock_scope.set_tag.assert_called_with("component", "is_recent_job")
    mock_scope.set_extra.assert_any_call("posted_date_str", "invalid-date-format")
    mock_scope.set_extra.assert_any_call("job_metadata", job_data)

def test_flatten_field_with_list():
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

def test_flatten_field_with_string():
    mock_field = "Strong communication and relationship-building skills."
    expected_output = "Strong communication and relationship-building skills."
    result = flatten_field(mock_field)
    assert result == expected_output

def test_flatten_field_with_empty():
    mock_field = []
    expected_output = ""
    result = flatten_field(mock_field)
    assert result == expected_output


