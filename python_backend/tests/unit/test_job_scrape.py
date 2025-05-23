import pytest
from unittest.mock import AsyncMock, Mock, patch, ANY
from job_scrape import scrape_job_listing, scrape_job_listing_page, process_all_jobs_concurrently, process_job_with_backoff, scrape_individual_job_url, scrape_job_metadata
from constants import MAX_RETRIES, POSTED_TIME_SELECTOR, SUCCESS, SKIPPED, TERMINATE, ERROR, DAY_RANGE_LIMIT

@pytest.mark.asyncio
@patch("job_scrape.scrape_job_listing_page", new_callable=AsyncMock)
@patch("job_scrape.scrape_page_markdown", new_callable=AsyncMock)
@patch("job_scrape.AsyncWebCrawler") 
async def test_scrape_job_listing_happy_path(
    mock_crawler_class, mock_scrape_first_page, mock_scrape_page
):
    mock_crawler_instance = AsyncMock()
    mock_crawler_class.return_value.__aenter__.return_value = mock_crawler_instance
    mock_scrape_first_page.return_value = ["# 22 jobs listed"]
    mock_scrape_page.return_value = {
        "job_count": 22,
        "all_errors": [],
        "terminated_early": False,
        "invalid_jobs": []
    }
    result = await scrape_job_listing("https://seek.com", location_search="sydney")
    assert result == {
        "message": "Scraped and inserted 22 jobs.",
        "errors": None,
        "invalid_jobs": [],
        "terminated_early": False
    }
    mock_scrape_first_page.assert_awaited_once()
    mock_scrape_page.assert_awaited_once()

@pytest.mark.asyncio
@patch("job_scrape.scrape_job_listing_page", new_callable=AsyncMock)
@patch("job_scrape.scrape_page_markdown", new_callable=AsyncMock)
@patch("job_scrape.AsyncWebCrawler") 
async def test_scrape_job_listing_empty_markdown(
    mock_crawler_class, mock_scrape_first_page, mock_scrape_page
):
    mock_crawler_instance = AsyncMock()
    mock_crawler_class.return_value.__aenter__.return_value = mock_crawler_instance
    mock_scrape_first_page.return_value = [] 

    result = await scrape_job_listing("https://seek.com", location_search="sydney")
    assert result == {
        "message": "No job search markdown found. Scraped 0 jobs.",
        "errors": None,
        "invalid_jobs": [],
        "terminated_early": False
    }
    mock_scrape_first_page.assert_awaited_once()
    mock_scrape_page.assert_not_awaited()

@pytest.mark.asyncio
@patch("job_scrape.scrape_job_listing_page", new_callable=AsyncMock)
@patch("job_scrape.scrape_page_markdown", new_callable=AsyncMock)
@patch("job_scrape.AsyncWebCrawler") 
async def test_scrape_job_listing_zero_jobs(
    mock_crawler_class, mock_scrape_first_page, mock_scrape_page
):
    mock_crawler_instance = AsyncMock()
    mock_crawler_class.return_value.__aenter__.return_value = mock_crawler_instance
    mock_scrape_first_page.return_value = ["# 0 jobs listed"]

    result = await scrape_job_listing("https://seek.com", location_search="sydney")
    assert result == {
        "message": "No jobs found. Scraped 0 jobs.",
        "errors": None,
        "invalid_jobs": [],
        "terminated_early": False
    }
    mock_scrape_first_page.assert_awaited_once()
    mock_scrape_page.assert_not_awaited()

@pytest.mark.asyncio
@patch("job_scrape.scrape_job_listing_page", new_callable=AsyncMock)
@patch("job_scrape.scrape_page_markdown", new_callable=AsyncMock)
@patch("job_scrape.AsyncWebCrawler")
async def test_scrape_job_listing_with_invalid_jobs(
    mock_crawler_class, mock_scrape_first_page, mock_scrape_page
):
    mock_crawler_instance = AsyncMock()
    mock_crawler_class.return_value.__aenter__.return_value = mock_crawler_instance
    mock_scrape_first_page.return_value = ["# 44 jobs listed"]

    mock_scrape_page.side_effect = [
        {"job_count": 22, "all_errors": [], "terminated_early": False, "invalid_jobs": ["job123", "job124"]},
        {"job_count": 44, "all_errors": [], "terminated_early": False, "invalid_jobs": ["job125"]},
    ]

    result = await scrape_job_listing("https://seek.com", location_search="sydney")
    
    assert result == {
        "message": "Scraped and inserted 44 jobs.",
        "errors": None,
        "invalid_jobs": ["job123", "job124", "job125"],
        "terminated_early": False
    }

    assert mock_scrape_page.await_count == 2

@pytest.mark.asyncio
@patch("job_scrape.scrape_job_listing_page", new_callable=AsyncMock)
@patch("job_scrape.scrape_page_markdown", new_callable=AsyncMock)
@patch("job_scrape.AsyncWebCrawler")
async def test_scrape_job_listing_with_errors(
    mock_crawler_class, mock_scrape_first_page, mock_scrape_page
):
    mock_crawler_instance = AsyncMock()
    mock_crawler_class.return_value.__aenter__.return_value = mock_crawler_instance
    mock_scrape_first_page.return_value = ["# 44 jobs listed"]

    mock_scrape_page.side_effect = [
        {"job_count": 22, "all_errors": ["no matching 'Posted X ago' text found"], "terminated_early": False, "invalid_jobs": []},
        {"job_count": 44, "all_errors": ["no matching 'Posted X ago' text found", "'posted_date' selector broke (most likely)"], "terminated_early": False, "invalid_jobs": []},
    ]

    result = await scrape_job_listing("https://seek.com", location_search="sydney")
    
    assert result == {
        "message": "Scraped and inserted 44 jobs.",
        "errors": ["no matching 'Posted X ago' text found", "'posted_date' selector broke (most likely)"],
        "invalid_jobs": [],
        "terminated_early": False,
    }
    assert mock_scrape_page.await_count == 2

@pytest.mark.asyncio
@patch("job_scrape.scrape_page_markdown", new_callable=AsyncMock)
async def test_scrape_job_listing_collects_errors(mock_scrape_page_markdown):
    async def mocked_scrape_page_markdown(base_url, crawler, page_num, all_errors):
        all_errors.append(f"[scrape_page_markdown] No markdown found on page {page_num}")
        return []
    
    mock_scrape_page_markdown.side_effect = mocked_scrape_page_markdown

    result = await scrape_job_listing(
        base_url="https://seek.com",
        location_search="sydney",
        max_pages=1,
        day_range_limit=3
    )

    assert result["message"] == "No job search markdown found. Scraped 0 jobs."

    assert result["errors"] is not None
    assert isinstance(result["errors"], list)
    assert any(
        err.startswith("[scrape_page_markdown]") for err in result["errors"]
    ), "Expected error messages to start with '[scrape_page_markdown]'"

    assert result["invalid_jobs"] == []
    assert result["terminated_early"] is False

@pytest.mark.asyncio
@patch("job_scrape.scrape_job_listing_page", new_callable=AsyncMock)
@patch("job_scrape.scrape_page_markdown", new_callable=AsyncMock)
@patch("job_scrape.AsyncWebCrawler") 
async def test_scrape_job_listing_multiple_pages_no_early_exit(
    mock_crawler_class, mock_scrape_first_page, mock_scrape_page
):
    mock_crawler_instance = AsyncMock()
    mock_crawler_class.return_value.__aenter__.return_value = mock_crawler_instance
    mock_scrape_first_page.return_value = ["## 66 jobs listed"] 
    mock_scrape_page.side_effect = [
        {"job_count": 22, "all_errors": [], "terminated_early": False, "invalid_jobs": []},
        {"job_count": 44, "all_errors": [], "terminated_early": False, "invalid_jobs": []},
        {"job_count": 66, "all_errors": [], "terminated_early": False, "invalid_jobs": []},
    ]
    result = await scrape_job_listing("https://seek.com", location_search="sydney")
    assert result == {
        "message": "Scraped and inserted 66 jobs.",
        "errors": None,
        "invalid_jobs": [],
        "terminated_early": False
    }
    assert mock_scrape_page.await_count == 3

@pytest.mark.asyncio
@patch("job_scrape.scrape_job_listing_page", new_callable=AsyncMock)
@patch("job_scrape.scrape_page_markdown", new_callable=AsyncMock)
@patch("job_scrape.AsyncWebCrawler") 
async def test_scrape_job_listing_multiple_pages_with_early_exit(
    mock_crawler_class, mock_scrape_first_page, mock_scrape_page
):
    mock_crawler_instance = AsyncMock()
    mock_crawler_class.return_value.__aenter__.return_value = mock_crawler_instance
    mock_scrape_first_page.return_value = ["## 66 jobs listed"] 
    mock_scrape_page.side_effect = [
        {"job_count": 22, "all_errors": [], "terminated_early": False, "invalid_jobs": []},
        {"job_count": 44, "all_errors": [], "terminated_early": False, "invalid_jobs": []},
        {"job_count": 57, "all_errors": [], "terminated_early": True, "invalid_jobs": []},
    ]
    result = await scrape_job_listing("https://seek.com", location_search="sydney")
    assert result == {
        "message": "Scraped and inserted 57 jobs. Early termination triggered on page 3 due to day range limit of 7 days.",
        "errors": None,
        "invalid_jobs": [],
        "terminated_early": True
    }
    assert mock_scrape_page.await_count == 3

@pytest.mark.asyncio
@patch("job_scrape.scrape_page_markdown", new_callable=AsyncMock)
async def test_scrape_job_listing_page_empty_markdown(mock_scrape_page_markdown):
    async def side_effect(base_url, crawler, page_num, all_errors):
        all_errors.append(f"[scrape_page_markdown] No markdown found on page {page_num}")
        return []
    
    mock_scrape_page_markdown.side_effect = side_effect
    errors = []

    result = await scrape_job_listing_page(
        base_url="https://seek.com",
        location_search="sydney",
        crawler=AsyncMock(),
        page_num=1,
        job_count=0,
        all_errors=errors,
        day_range_limit=DAY_RANGE_LIMIT,
    )
    assert result == {
        "job_count": 0,
        "all_errors": errors,
        "terminated_early": False,
        "invalid_jobs": []
    }
    assert f"[scrape_page_markdown] No markdown found on page 1" in errors

@pytest.mark.asyncio
@patch("job_scrape.scrape_page_markdown", new_callable=AsyncMock)
async def test_scrape_job_listing_page_no_links_in_markdown(mock_scrape_page_markdown):
    mock_scrape_page_markdown.return_value = ["Some header\nMore content\nBut no job links"]
    result = await scrape_job_listing_page(
        base_url="https://seek.com", 
        location_search="sydney",
        crawler=AsyncMock(),
        page_num=1,
        job_count=0,
        all_errors=[],
        day_range_limit=DAY_RANGE_LIMIT
    )
    assert result == {"job_count": 0, "all_errors": ["No job links found on page 1"], "terminated_early": False, "invalid_jobs": []}

@pytest.mark.asyncio
@patch("job_scrape.validate_and_insert_jobs", new_callable=AsyncMock)
@patch("job_scrape.process_all_jobs_concurrently", new_callable=AsyncMock)
@patch("job_scrape.scrape_page_markdown", new_callable=AsyncMock)
@patch("job_scrape.process_markdown_to_job_links", return_value=["https://seek.com/job1"])
async def test_scrape_job_listing_page_with_job_errors(
    mock_process_links, mock_scrape_page_markdown, mock_process_all_jobs, mock_validate_and_insert_jobs
):
    mock_scrape_page_markdown.return_value = ["# Link to job1"]
    mock_process_all_jobs.return_value = ([{"title": "Job 1"}], False, ["Error parsing job1"])
    mock_validate_and_insert_jobs.return_value = (1,[],[])

    result = await scrape_job_listing_page(
        base_url="https://seek.com",
        location_search="sydney",
        crawler=AsyncMock(),
        page_num=1,
        job_count=0,
        all_errors=[],
        day_range_limit=DAY_RANGE_LIMIT
    )

    assert result["job_count"] == 1
    assert result["all_errors"] == ["Error parsing job1"]

@pytest.mark.asyncio
@patch("job_scrape.scrape_job_listing_page", new_callable=AsyncMock)
@patch("job_scrape.scrape_page_markdown", new_callable=AsyncMock)
@patch("job_scrape.AsyncWebCrawler")
async def test_scrape_job_listing_respects_max_pages(
    mock_crawler_class, mock_scrape_first_page, mock_scrape_page
):
    mock_crawler_instance = AsyncMock()
    mock_crawler_class.return_value.__aenter__.return_value = mock_crawler_instance
    mock_scrape_first_page.return_value = ["# 100 jobs listed"]
    mock_scrape_page.return_value = {
        "job_count": 22,
        "all_errors": [],
        "terminated_early": False,
        "invalid_jobs": []
    }
    result = await scrape_job_listing("https://seek.com", location_search="sydney", max_pages=1)
    assert result == {
        "message": "Scraped and inserted 22 jobs.",
        "errors": None,
        "invalid_jobs": [],
        "terminated_early": False
    }
    mock_scrape_first_page.assert_awaited_once()
    mock_scrape_page.assert_awaited_once() 


@pytest.mark.asyncio
@patch("job_scrape.bounded_process_job", new_callable=AsyncMock)
async def test_process_all_jobs_concurrently(mock_bounded_process_job):
    job_urls = ["https://www.seek.com.au/job/123", "https://www.seek.com.au/job/456","https://www.seek.com.au/job/789", "https://www.seek.com.au/job/999"]
    crawler = AsyncMock()
    location_search = "Sydney"
    day_range_limit = DAY_RANGE_LIMIT
    mock_bounded_process_job.side_effect = [
        {"status": SUCCESS, "job": {"title": "Software Engineer"}},
        {"status": TERMINATE}, 
        {"status": SKIPPED, "job": None, "error": "No JSON extracted"},
        {"status": SUCCESS, "job": {"title": "Senior Software Engineer"}},  
    ]
    final_jobs, early_termination, job_errors = await process_all_jobs_concurrently(job_urls, crawler, location_search, day_range_limit)
    assert final_jobs == [{"title": "Software Engineer"}, {"title": "Senior Software Engineer"}]
    assert early_termination is True
    assert job_errors == ["No JSON extracted"]


@pytest.mark.asyncio
@patch("job_scrape.scrape_individual_job_url", new_callable=AsyncMock)
@patch("job_scrape.parse_job_data_from_markdown", new_callable=AsyncMock)
@patch("job_scrape.set_default_work_model")
@patch("job_scrape.extract_job_urls")
@patch("job_scrape.enrich_job_data")
@patch("job_scrape.is_job_within_date_range")
@patch("job_scrape.override_experience_level_with_title")
@patch("job_scrape.normalize_experience_level")
async def test_process_job_with_backoff_success(
    mock_normalize_experience,
    mock_override_experience,
    mock_is_recent,
    mock_enrich,
    mock_extract_urls,
    mock_set_work_model,
    mock_parse_json,
    mock_scrape
):
    mock_scrape.return_value = ("<html>", {"title": "Software Engineer"})
    mock_parse_json.return_value = {"title": "Software Engineer"}
    mock_set_work_model.return_value = {"title": "Software Engineer"}
    mock_extract_urls.return_value = ("https://www.seek.com.au/job/123", "https://www.seek.com.au/job/123/apply")
    mock_enrich.return_value = None
    mock_is_recent.return_value = True
    mock_override_experience.return_value = {"title": "Software Engineer"}
    mock_normalize_experience.return_value = {"title": "Software Engineer"}

    job_link = "https://www.seek.com.au/job/123"
    count = 1
    crawler = AsyncMock()
    location_search = "Sydney"
    terminate_event = Mock()
    day_range_limit = DAY_RANGE_LIMIT

    result = await process_job_with_backoff(job_link, count, crawler, location_search, terminate_event, day_range_limit)
    assert result["status"] == SUCCESS
    assert result["job"]["title"] == "Software Engineer"
    assert result["error"] is None

@pytest.mark.asyncio
@patch("job_scrape.scrape_individual_job_url", new_callable=AsyncMock)
@patch("job_scrape.parse_job_data_from_markdown", new_callable=AsyncMock)
async def test_process_job_with_backoff_missing_json(mock_parse_json, mock_scrape):
    mock_scrape.return_value = ("<html>", {"title": "Software Engineer"})
    mock_parse_json.return_value = None  
    job_link = "https://www.seek.com.au/job/456"
    count = 2
    crawler = AsyncMock()
    location_search = "Sydney"
    terminate_event = Mock()
    day_range_limit = DAY_RANGE_LIMIT

    result = await process_job_with_backoff(job_link, count, crawler, location_search, terminate_event, day_range_limit)
    assert result["status"] == SKIPPED
    assert result["job"] is None
    assert result["error"] == "No JSON extracted"
    assert mock_scrape.call_count == 1


@pytest.mark.asyncio
@patch("job_scrape.scrape_individual_job_url", new_callable=AsyncMock)
@patch("job_scrape.parse_job_data_from_markdown", new_callable=AsyncMock)
@patch("job_scrape.set_default_work_model")
@patch("job_scrape.extract_job_urls")
@patch("job_scrape.enrich_job_data")
@patch("job_scrape.is_job_within_date_range")
@patch("job_scrape.override_experience_level_with_title")
@patch("job_scrape.normalize_experience_level")
async def test_process_job_with_backoff_too_old(
    mock_normalize_experience,
    mock_override_experience,
    mock_is_recent,
    mock_enrich,
    mock_extract_urls,
    mock_set_work_model,
    mock_parse_json,
    mock_scrape
):
    mock_scrape.return_value = ("<html>", {"title": "Software Engineer"})
    mock_parse_json.return_value = {"title": "Software Engineer"}
    mock_set_work_model.return_value = {"title": "Software Engineer"}
    mock_extract_urls.return_value = ("https://www.seek.com.au/job/123", "https://www.seek.com.au/job/123/apply")
    mock_enrich.return_value = None
    mock_is_recent.return_value = False  
    mock_override_experience.return_value = {"title": "Software Engineer"}
    mock_normalize_experience.return_value = {"title": "Software Engineer"}

    job_link = "https://www.seek.com.au/job/123"
    count = 1
    crawler = AsyncMock()
    location_search = "Sydney"
    terminate_event = Mock()
    day_range_limit = DAY_RANGE_LIMIT

    result = await process_job_with_backoff(job_link, count, crawler, location_search, terminate_event, day_range_limit)
    assert result == {"status": TERMINATE, "job": None, "error": None}
    terminate_event.set.assert_called_once()

@pytest.mark.asyncio
@patch("job_scrape.scrape_individual_job_url", new_callable=AsyncMock)
@patch("job_scrape.parse_job_data_from_markdown", new_callable=AsyncMock)
@patch("job_scrape.set_default_work_model")
@patch("job_scrape.extract_job_urls")
@patch("job_scrape.enrich_job_data")
@patch("job_scrape.is_job_within_date_range")
@patch("job_scrape.override_experience_level_with_title")
@patch("job_scrape.normalize_experience_level")
async def test_process_job_with_backoff_retry_once_logic(
    mock_normalize_experience,
    mock_override_experience,
    mock_is_recent,
    mock_enrich,
    mock_extract_urls,
    mock_set_work_model,
    mock_parse_json,
    mock_scrape
):
    mock_scrape.side_effect = [Exception("Scraping failed"), ("<html>", {"title": "Software Engineer"})]
    mock_parse_json.return_value = {"title": "Software Engineer"}
    mock_set_work_model.return_value = {"title": "Software Engineer"}
    mock_extract_urls.return_value = ("https://www.seek.com.au/job/123", "https://www.seek.com.au/job/123/apply")
    mock_enrich.return_value = None
    mock_is_recent.return_value = True
    mock_override_experience.return_value = {"title": "Software Engineer"}
    mock_normalize_experience.return_value = {"title": "Software Engineer"}

    job_link = "https://www.seek.com.au/job/123"
    count = 1
    crawler = AsyncMock()
    location_search = "Sydney"
    terminate_event = Mock()
    day_range_limit = DAY_RANGE_LIMIT

    result = await process_job_with_backoff(job_link, count, crawler, location_search, terminate_event, day_range_limit)
    assert result["status"] == SUCCESS
    assert result["job"]["title"] == "Software Engineer"
    assert result["error"] is None
    assert mock_scrape.call_count == 2  


@pytest.mark.asyncio
@patch("job_scrape.scrape_individual_job_url", new_callable=AsyncMock)
async def test_process_job_with_backoff_max_retries_exhausted(mock_scrape):
    mock_scrape.side_effect = Exception("Simulated failure")
    job_link = "https://www.seek.com.au/job/123"
    count = 1
    crawler = AsyncMock()
    location_search = "Sydney"
    terminate_event = Mock()
    day_range_limit = DAY_RANGE_LIMIT

    result = await process_job_with_backoff(job_link, count, crawler, location_search, terminate_event, day_range_limit, max_retries=MAX_RETRIES)
    assert result["status"] == ERROR
    assert result["job"] is None
    assert f"{job_link} failed after {MAX_RETRIES} retries" in result["error"]
    assert mock_scrape.call_count == MAX_RETRIES

@pytest.mark.asyncio
@patch("job_scrape.scrape_individual_job_url", new_callable=AsyncMock)
async def test_process_job_with_backoff_markdown_error(mock_scrape):
    mock_scrape.return_value = (None, {"error": "No markdown extracted"})
    
    job_link = "https://www.seek.com.au/job/123"
    count = 3
    crawler = AsyncMock()
    location_search = "Sydney"
    terminate_event = Mock()
    day_range_limit = DAY_RANGE_LIMIT

    result = await process_job_with_backoff(job_link, count, crawler, location_search, terminate_event, day_range_limit)
    assert result["status"] == SKIPPED
    assert result["job"] is None
    assert result["error"] == "No markdown extracted"

@pytest.mark.asyncio
@patch("job_scrape.scrape_individual_job_url", new_callable=AsyncMock)
async def test_process_job_with_backoff_posted_time_no_elements_error(mock_scrape):
    mock_scrape.return_value = (None, {"posted_time_error": "__NO_ELEMENTS__"})
    
    job_link = "https://www.seek.com.au/job/123"
    count = 4
    crawler = AsyncMock()
    location_search = "Sydney"
    terminate_event = Mock()
    day_range_limit = DAY_RANGE_LIMIT

    result = await process_job_with_backoff(job_link, count, crawler, location_search, terminate_event, day_range_limit)
    assert result["status"] == SKIPPED
    assert result["job"] is None
    assert result["error"] == "Posted date selector issue: 'posted_date' selector broke (most likely)"

@pytest.mark.asyncio
@patch("job_scrape.scrape_individual_job_url", new_callable=AsyncMock)
async def test_process_job_with_backoff_posted_time_no_matching_text_error(mock_scrape):
    mock_scrape.return_value = (None, {"posted_time_error": "__NO_MATCHING_TEXT__"})
    
    job_link = "https://www.seek.com.au/job/123"
    count = 4
    crawler = AsyncMock()
    location_search = "Sydney"
    terminate_event = Mock()
    day_range_limit = DAY_RANGE_LIMIT

    result = await process_job_with_backoff(job_link, count, crawler, location_search, terminate_event, day_range_limit)
    assert result["status"] == SKIPPED
    assert result["job"] is None
    assert result["error"] == "Posted date selector issue: no matching 'Posted X ago' text found"

@pytest.mark.asyncio
@patch("job_scrape.scrape_job_metadata", new_callable=AsyncMock)
async def test_scrape_individual_job_url_success(mock_scrape_metadata):
    job_url = "https://www.seek.com.au/job/123"
    crawler = AsyncMock()  
    crawler.arun.return_value = AsyncMock(markdown=AsyncMock(fit_markdown="Some markdown content"))
    mock_scrape_metadata.return_value = {"location": "Sydney", "title": "Software Engineer", "company": "Company X"}
    
    result = await scrape_individual_job_url(job_url, crawler)
    assert len(result) == 2
    assert "Some markdown content" in result[0]
    assert result[1] == {"location": "Sydney", "title": "Software Engineer", "company": "Company X"}
    crawler.arun.assert_called_once_with(job_url, config=ANY)
    mock_scrape_metadata.assert_called_once_with(job_url, ANY)

@pytest.mark.asyncio
@patch("job_scrape.scrape_job_metadata", new_callable=AsyncMock)
async def test_scrape_individual_job_url_no_markdown(mock_scrape_metadata):
    job_url = "https://www.seek.com.au/job/123"
    crawler = AsyncMock()
    crawler.arun.return_value = AsyncMock(markdown=None)  
    mock_scrape_metadata.return_value = {"location": "Sydney", "title": "Data Analyst", "company": "Company X"}
    
    result = await scrape_individual_job_url(job_url, crawler)
    assert result == (None, {"error": "No markdown extracted"}) 
    crawler.arun.assert_called_once_with(job_url, config=ANY)

@pytest.mark.asyncio
@patch("job_scrape.create_browser_context", new_callable=AsyncMock)
@patch("job_scrape.extract_logo_src", new_callable=AsyncMock)
@patch("job_scrape.extract_job_metadata_fields", new_callable=AsyncMock)
@patch("job_scrape.extract_posted_date_by_class", new_callable=AsyncMock)
async def test_scrape_job_metadata_success(mock_extract_posted_time, mock_extract_metadata, mock_extract_logo, mock_create_browser_context):
    mock_browser = AsyncMock()
    mock_page = AsyncMock()
    mock_context = AsyncMock()

    mock_create_browser_context.return_value = (None, mock_browser, mock_context)
    mock_context.new_page.return_value = mock_page
    mock_extract_logo.return_value = "https://image-service-cdn.seek.com.au/1a2b3c4d5e6f"
    mock_extract_metadata.return_value = {
        "location": "Sydney NSW",
        "classification": "Testing & Quality Assurance (Information & Communication Technology)",
        "work_type": "Remote",
        "salary": "$100,000 - $120,000",
        "title": "Software Engineer",
        "company": "Company X"
    }
    mock_extract_posted_time.return_value = {"posted_time": "09/05/2025", "error": None}

    result = await scrape_job_metadata("https://www.seek.com.au/job/123", ["metadata_id_1", "metadata_id_2"])
    assert result == {
        "logo_src": "https://image-service-cdn.seek.com.au/1a2b3c4d5e6f",
        "posted_time": "09/05/2025",
        "posted_time_error": None,
        "title": "Software Engineer",
        "location": "Sydney NSW",
        "classification": "Testing & Quality Assurance (Information & Communication Technology)",
        "work_type": "Remote",
        "salary": "$100,000 - $120,000",
        "company": "Company X"
    }
    mock_page.goto.assert_called_once_with("https://www.seek.com.au/job/123")
    mock_extract_logo.assert_called_once_with(mock_page)
    mock_extract_metadata.assert_called_once_with(mock_page, ["metadata_id_1", "metadata_id_2"])
    mock_extract_posted_time.assert_called_once_with(mock_page, POSTED_TIME_SELECTOR)
    
@pytest.mark.asyncio
@patch("job_scrape.create_browser_context", new_callable=AsyncMock)
async def test_scrape_job_metadata_error_handling(mock_create_browser_context):
    mock_browser = AsyncMock()
    mock_page = AsyncMock()
    mock_context = AsyncMock()

    mock_create_browser_context.return_value = (None, mock_browser, mock_context)
    mock_context.new_page.return_value = mock_page
    mock_page.goto.side_effect = Exception("Page load failed")

    result = await scrape_job_metadata("https://www.seek.com.au/job/123", ["metadata_id_1"])

    assert "error" in result
    assert "Page load failed" in result["error"]

    mock_page.goto.assert_called_once_with("https://www.seek.com.au/job/123")

@pytest.mark.asyncio
@patch("job_scrape.create_browser_context", new_callable=AsyncMock)
@patch("job_scrape.extract_logo_src", new_callable=AsyncMock)
@patch("job_scrape.extract_job_metadata_fields", new_callable=AsyncMock)
@patch("job_scrape.extract_posted_date_by_class", new_callable=AsyncMock)
async def test_scrape_job_metadata_missing_elements(mock_extract_posted_time, mock_extract_metadata, mock_extract_logo, mock_create_browser_context):
    mock_browser = AsyncMock()
    mock_page = AsyncMock()
    mock_context = AsyncMock()

    mock_create_browser_context.return_value = (None, mock_browser, mock_context)
    mock_context.new_page.return_value = mock_page
    
    mock_extract_logo.return_value = ""  
    mock_extract_metadata.return_value = {"title": "Software Engineer", "company": ""}  
    mock_extract_posted_time.return_value = {"posted_time": "", "error": None} 

    result = await scrape_job_metadata("https://www.seek.com.au/job/123", ["metadata_id_1"])
    assert result == {
        "logo_src": "",
        "posted_time": "",
        "posted_time_error": None,
        "title": "Software Engineer",
        "company": ""
    }
    mock_page.goto.assert_called_once_with("https://www.seek.com.au/job/123")
    mock_extract_logo.assert_called_once_with(mock_page)
    mock_extract_metadata.assert_called_once_with(mock_page, ["metadata_id_1"])
    mock_extract_posted_time.assert_called_once_with(mock_page, POSTED_TIME_SELECTOR)

@pytest.mark.asyncio
@patch("job_scrape.create_browser_context", new_callable=AsyncMock)
async def test_scrape_job_metadata_cleanup_on_exception(mock_create_browser_context):
    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_page = AsyncMock()
    mock_playwright = AsyncMock()

    mock_create_browser_context.return_value = (mock_playwright, mock_browser, mock_context)
    mock_context.new_page.return_value = mock_page
    mock_page.goto.side_effect = Exception("Navigation error")

    result = await scrape_job_metadata("https://www.seek.com.au/job/123", ["metadata_id_1"])

    assert "error" in result
    assert "Navigation error" in result["error"]

    mock_browser.close.assert_awaited_once()
    mock_playwright.stop.assert_awaited_once()

@pytest.mark.asyncio
@patch("job_scrape.create_browser_context", new_callable=AsyncMock)
@patch("job_scrape.extract_logo_src", new_callable=AsyncMock)
@patch("job_scrape.extract_job_metadata_fields", new_callable=AsyncMock)
@patch("job_scrape.extract_posted_date_by_class", new_callable=AsyncMock)
async def test_scrape_job_metadata_posted_time_error(mock_extract_posted_time, mock_extract_metadata, mock_extract_logo, mock_create_browser_context):
    mock_browser = AsyncMock()
    mock_page = AsyncMock()
    mock_context = AsyncMock()

    mock_create_browser_context.return_value = (None, mock_browser, mock_context)
    mock_context.new_page.return_value = mock_page
    mock_extract_logo.return_value = "logo.png"
    mock_extract_metadata.return_value = {"title": "Software Engineer"}
    mock_extract_posted_time.return_value = {"posted_time": "", "error": "__NO_ELEMENTS__"}

    result = await scrape_job_metadata("https://www.seek.com.au/job/123", ["metadata_id_1"])
    assert result == {
        "logo_src": "logo.png",
        "posted_time": "",
        "posted_time_error": "__NO_ELEMENTS__",
        "title": "Software Engineer"
    }
