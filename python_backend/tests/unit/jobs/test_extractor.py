import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jobs.extractor import (
    extract_job_data,
    extract_job_metadata,
    extract_job_metadata_fields,
    extract_logo_src,
    extract_metadata_from_page,
    extract_posted_date_by_class,
    safe_extract_job_metadata_fields,
    safe_extract_logo_src,
    safe_extract_posted_date_by_class,
    scrape_job_details,
)
from utils.constants import (
    JOB_METADATA_FIELDS,
    LOGO_SELECTOR,
    NO_ELEMENTS,
    NO_MATCHING_TEXT,
    POSTED_DATE_SELECTOR,
    SKIPPED,
    SUCCESS,
    TERMINATE,
)
from utils.context import ScrapeContext


@pytest.mark.asyncio
async def test_extract_logo_src_found() -> None:
    mock_logo_element = MagicMock()
    mock_logo_element.get_attribute = AsyncMock(return_value="https://image-service-cdn.seek.com.au/1a2b3c4d5e6f")
    mock_page = MagicMock()
    mock_page.query_selector = AsyncMock(return_value=mock_logo_element)

    result = await extract_logo_src(mock_page)

    assert result == "https://image-service-cdn.seek.com.au/1a2b3c4d5e6f"
    mock_page.query_selector.assert_awaited_once_with(LOGO_SELECTOR)
    mock_logo_element.get_attribute.assert_awaited_once_with("src")

@pytest.mark.asyncio
async def test_extract_logo_src_not_found() -> None:
    mock_page = MagicMock()
    mock_page.query_selector = AsyncMock(return_value=None)
    result = await extract_logo_src(mock_page)

    assert result == ""
    mock_page.query_selector.assert_awaited_once_with(LOGO_SELECTOR)


@pytest.mark.asyncio
async def test_extract_job_metadata_fields_success() -> None:
    mock_page = MagicMock()

    mock_elem_1 = MagicMock()
    mock_elem_1.inner_text = AsyncMock(return_value=" Software Engineer ")
    mock_elem_2 = MagicMock()
    mock_elem_2.inner_text = AsyncMock(return_value=" Google ")

    mock_page.query_selector = AsyncMock(side_effect=[mock_elem_1, mock_elem_2])

    job_metadata_fields = {
        "job_title": ["job-detail-title"],
        "company": ["advertiser-name"]
    }

    results, field_errors = await extract_job_metadata_fields(mock_page, job_metadata_fields)

    assert results == {
        "job_title": "Software Engineer",
        "company": "Google"
    }
    assert field_errors == {}

@pytest.mark.asyncio
async def test_extract_job_metadata_fields_element_missing() -> None:
    mock_page = MagicMock()
    mock_page.query_selector = AsyncMock(return_value=None)

    job_metadata_fields = {"location": ["job-detail-location"]}

    results, field_errors = await extract_job_metadata_fields(mock_page, job_metadata_fields)

    assert results == {"location": ""}
    assert field_errors == {"location": "Element not found"}

@pytest.mark.asyncio
async def test_extract_job_metadata_fields_with_exception() -> None:
    mock_page = MagicMock()
    mock_page.query_selector = AsyncMock(side_effect=Exception("TimeoutError"))

    job_metadata_fields = {"location": ["job-detail-location"]}

    results, field_errors = await extract_job_metadata_fields(mock_page, job_metadata_fields)

    assert results == {"location": ""}
    assert "TimeoutError" in field_errors["location"]

@pytest.mark.asyncio
async def test_extract_job_metadata_fields_fallback_to_second_selector() -> None:
    mock_page = MagicMock()

    mock_elem = MagicMock()
    mock_elem.inner_text = AsyncMock(return_value="Add expected salary to your profile for insights")
    mock_page.query_selector = AsyncMock(side_effect=[None, mock_elem])

    job_metadata_fields = {"salary": ["job-detail-salary", "job-detail-add-expected-salary"]}

    results, field_errors = await extract_job_metadata_fields(mock_page, job_metadata_fields)

    assert results == {"salary": "Add expected salary to your profile for insights"}
    assert field_errors == {}

@pytest.mark.asyncio
@patch("jobs.extractor.get_posted_date", return_value="05/05/2024")
async def test_extract_posted_date_by_class_with_days(mock_get_posted_date: MagicMock) -> None:
    mock_elem = AsyncMock()
    mock_elem.inner_text = AsyncMock(return_value="Posted 3d ago")
    page = MagicMock()
    page.query_selector_all = AsyncMock(return_value=[mock_elem])

    result = await extract_posted_date_by_class(page, "posted_date")
    assert result == {"posted_date": "05/05/2024", "error" : None}
    mock_get_posted_date.assert_called_once_with(3)

@pytest.mark.asyncio
@patch("jobs.extractor.get_posted_date", return_value="04/04/2024")
async def test_extract_posted_date_by_class_with_hours(mock_get_posted_date: MagicMock) -> None:
    mock_elem = AsyncMock()
    mock_elem.inner_text = AsyncMock(return_value="Posted 5h ago")
    page = MagicMock()
    page.query_selector_all = AsyncMock(return_value=[mock_elem])

    result = await extract_posted_date_by_class(page, "posted_date")
    assert result == {"posted_date": "04/04/2024", "error" : None}
    mock_get_posted_date.assert_called_once_with(0)

@pytest.mark.asyncio
@patch("jobs.extractor.get_posted_date", return_value="03/03/2024")
async def test_extract_posted_date_by_class_with_minutes(mock_get_posted_date: MagicMock) -> None:
    mock_elem = AsyncMock()
    mock_elem.inner_text = AsyncMock(return_value="Posted 42m ago")
    page = MagicMock()
    page.query_selector_all = AsyncMock(return_value=[mock_elem])

    result = await extract_posted_date_by_class(page, "posted_date")
    assert result == {"posted_date": "03/03/2024", "error" : None}
    mock_get_posted_date.assert_called_once_with(0)

@pytest.mark.asyncio
async def test_extract_posted_date_by_class_no_elements_found() -> None:
    page = MagicMock()
    page.query_selector_all = AsyncMock(return_value=[])

    result = await extract_posted_date_by_class(page, "posted_date")
    assert result == {"posted_date": None, "error": NO_ELEMENTS}

@pytest.mark.asyncio
async def test_extract_posted_date_by_class_no_matching_text() -> None:
    mock_elem = AsyncMock()
    mock_elem.inner_text = AsyncMock(return_value="Updated yesterday")
    page = MagicMock()
    page.query_selector_all = AsyncMock(return_value=[mock_elem])

    result = await extract_posted_date_by_class(page, "posted-time")
    assert result == {"posted_date": None, "error": NO_MATCHING_TEXT}

@pytest.mark.asyncio
async def test_extract_posted_date_by_class_raises_exception() -> None:
    page = MagicMock()
    page.query_selector_all = AsyncMock(side_effect=RuntimeError("Something went wrong"))

    with pytest.raises(RuntimeError, match="Something went wrong"):
        await extract_posted_date_by_class(page, "posted_date")

@pytest.mark.asyncio
@patch("jobs.extractor.extract_logo_src", new_callable=AsyncMock)
async def test_safe_extract_logo_src_success(mock_extract_logo_src: AsyncMock) -> None:
    mock_extract_logo_src.return_value = "https://seek.com.au/logo.png"

    result = await safe_extract_logo_src(page=MagicMock(), job_url="https://seek.com.au/job/123")

    assert result == "https://seek.com.au/logo.png"
    mock_extract_logo_src.assert_awaited_once()

@pytest.mark.asyncio
@patch("jobs.extractor.extract_logo_src", new_callable=AsyncMock)
@patch("sentry_sdk.capture_exception")
@patch("sentry_sdk.push_scope")
async def test_safe_extract_logo_src_handles_exception(
    mock_push_scope: MagicMock,
    mock_capture_exception: MagicMock,
    mock_extract_logo_src: AsyncMock,
) -> None:
    mock_extract_logo_src.side_effect = RuntimeError("logo failed")
    mock_scope_instance = MagicMock()
    mock_push_scope.return_value.__enter__.return_value = mock_scope_instance

    result = await safe_extract_logo_src(page=MagicMock(), job_url="https://seek.com.au/job/456")

    assert result == ""
    mock_extract_logo_src.assert_awaited_once()
    mock_scope_instance.set_tag.assert_called_with("component", "extract_logo_src")
    mock_scope_instance.set_extra.assert_called_with("job_url", "https://seek.com.au/job/456")
    mock_capture_exception.assert_called_once()

@pytest.mark.asyncio
@patch("jobs.extractor.extract_job_metadata_fields", new_callable=AsyncMock)
@patch("sentry_sdk.capture_message")
@patch("sentry_sdk.push_scope")
async def test_safe_extract_job_metadata_fields_with_field_errors(
    mock_push_scope: MagicMock, mock_capture_message: MagicMock, mock_extract_metadata: AsyncMock
) -> None:
    mock_extract_metadata.return_value = (
        {"location": "", "company": "Google"},
        {"location": "Element not found"}
    )
    mock_scope_instance = MagicMock()
    mock_push_scope.return_value.__enter__.return_value = mock_scope_instance

    fields = {"location": ["job-detail-location"], "company": ["advertiser-name"]}
    result = await safe_extract_job_metadata_fields(MagicMock(), fields, "https://seek.com.au/job/123")

    assert result == {"location": "", "company": "Google"}

    mock_extract_metadata.assert_awaited_once()
    mock_capture_message.assert_called_once_with(
        "Job metadata extraction issue for field 'location': Element not found",
        level="error"
    )
    mock_scope_instance.set_tag.assert_called_with("component", "extract_job_metadata_fields")
    mock_scope_instance.set_extra.assert_any_call("job_url", "https://seek.com.au/job/123")
    mock_scope_instance.set_extra.assert_any_call("field", "location")
    mock_scope_instance.set_extra.assert_any_call("error_detail", "Element not found")

@pytest.mark.asyncio
@patch("jobs.extractor.extract_job_metadata_fields", new_callable=AsyncMock)
@patch("sentry_sdk.capture_exception")
@patch("sentry_sdk.push_scope")
async def test_safe_extract_job_metadata_fields_raises_exception(
    mock_push_scope: MagicMock, mock_capture_exception: MagicMock, mock_extract_metadata: AsyncMock
) -> None:
    mock_extract_metadata.side_effect = RuntimeError("Metadata Fail")
    mock_scope_instance = MagicMock()
    mock_push_scope.return_value.__enter__.return_value = mock_scope_instance

    result = await safe_extract_job_metadata_fields(MagicMock(), {}, "https://seek.com.au/job/456")

    assert result == {}
    mock_extract_metadata.assert_awaited_once()
    mock_capture_exception.assert_called_once()
    mock_scope_instance.set_tag.assert_called_with("component", "extract_job_metadata_fields")
    mock_scope_instance.set_extra.assert_called_with("job_url", "https://seek.com.au/job/456")

@pytest.mark.asyncio
@patch("jobs.extractor.extract_job_metadata_fields", new_callable=AsyncMock)
@patch("sentry_sdk.capture_message")
@patch("sentry_sdk.push_scope")
async def test_safe_extract_job_metadata_fields_no_errors(
    mock_push_scope: MagicMock, mock_capture_message: MagicMock, mock_extract_metadata: AsyncMock
) -> None:
    mock_extract_metadata.return_value = (
        {"location": "Sydney", "company": "Google"},
        {}
    )

    result = await safe_extract_job_metadata_fields(MagicMock(), {
        "location": ["job-detail-location"],
        "company": ["advertiser-name"]
    }, "https://seek.com.au/job/789")

    assert result == {"location": "Sydney", "company": "Google"}
    mock_extract_metadata.assert_awaited_once()
    mock_capture_message.assert_not_called()
    mock_push_scope.assert_not_called()

@pytest.mark.asyncio
@patch("jobs.extractor.extract_posted_date_by_class", new_callable=AsyncMock)
async def test_safe_extract_posted_date_by_class_success(mock_extract_posted_date: AsyncMock) -> None:
    mock_extract_posted_date.return_value = {"posted_date": "06/01/2024", "error": None}

    result = await safe_extract_posted_date_by_class(MagicMock(), "posted_date", "https://seek.com.au/job/123")

    assert result == "06/01/2024"
    mock_extract_posted_date.assert_awaited_once()

@pytest.mark.asyncio
@patch("sentry_sdk.push_scope")
@patch("jobs.extractor.extract_posted_date_by_class", new_callable=AsyncMock)
async def test_safe_extract_posted_date_by_class_no_elements(
    mock_extract_posted_date: AsyncMock,
    mock_push_scope: MagicMock
) -> None:
    mock_extract_posted_date.return_value = {"posted_date": None, "error": NO_ELEMENTS}
    mock_scope = MagicMock()
    mock_push_scope.return_value.__enter__.return_value = mock_scope

    result = await safe_extract_posted_date_by_class(MagicMock(), "posted_date", "https://seek.com.au/job/456")

    assert result is None
    mock_scope.set_tag.assert_called_with("component", "extract_posted_date_by_class")
    mock_scope.set_extra.assert_called_with("job_url", "https://seek.com.au/job/456")
    mock_scope.capture_message.assert_called_once_with(
        "Posted date extraction warning: 'posted_date' selector broke - no elements found",
        level="error"
    )

@pytest.mark.asyncio
@patch("sentry_sdk.push_scope")
@patch("jobs.extractor.extract_posted_date_by_class", new_callable=AsyncMock)
async def test_safe_extract_posted_date_by_class_no_matching_text(
    mock_extract_posted_date: AsyncMock,
    mock_push_scope: MagicMock
) -> None:
    mock_extract_posted_date.return_value = {"posted_date": None, "error": NO_MATCHING_TEXT}
    mock_scope = MagicMock()
    mock_push_scope.return_value.__enter__.return_value = mock_scope

    result = await safe_extract_posted_date_by_class(MagicMock(), "posted_date", "https://seek.com.au/job/789")

    assert result is None
    mock_scope.set_tag.assert_called_with("component", "extract_posted_date_by_class")
    mock_scope.set_extra.assert_called_with("job_url", "https://seek.com.au/job/789")
    mock_scope.capture_message.assert_called_once_with(
        "Posted date extraction warning: no matching 'Posted X ago' text found",
        level="error"
    )

@pytest.mark.asyncio
@patch("sentry_sdk.capture_exception")
@patch("sentry_sdk.push_scope")
@patch("jobs.extractor.extract_posted_date_by_class", new_callable=AsyncMock)
async def test_safe_extract_posted_date_by_class_raises_exception(
    mock_extract_posted_date: AsyncMock, mock_push_scope: MagicMock, mock_capture_exception: MagicMock
) -> None:
    mock_extract_posted_date.side_effect = RuntimeError("Unexpected failure")
    mock_scope = MagicMock()
    mock_push_scope.return_value.__enter__.return_value = mock_scope

    result = await safe_extract_posted_date_by_class(MagicMock(), "posted_date", "https://seek.com.au/job/000")

    assert result is None
    mock_capture_exception.assert_called_once()
    mock_scope.set_tag.assert_called_with("component", "extract_posted_date_by_class")
    mock_scope.set_extra.assert_called_with("job_url", "https://seek.com.au/job/000")

@pytest.mark.asyncio
@patch("jobs.extractor.safe_extract_logo_src", new_callable=AsyncMock)
@patch("jobs.extractor.safe_extract_job_metadata_fields", new_callable=AsyncMock)
@patch("jobs.extractor.safe_extract_posted_date_by_class", new_callable=AsyncMock)
async def test_extract_metadata_from_page_success(
    mock_posted_date: AsyncMock, mock_metadata_fields: AsyncMock, mock_logo_src: AsyncMock
) -> None:
    page = MagicMock()
    job_url = "https://seek.com.au/job/123"
    fields = {"salary": ["job-detail-salary"]}

    mock_logo_src.return_value = "https://logo.url/logo.png"
    mock_metadata_fields.return_value = {"salary": "$100k - $120k"}
    mock_posted_date.return_value = "05/05/2024"

    result = await extract_metadata_from_page(page, job_url, fields)

    assert result == {
        "logo_src": "https://logo.url/logo.png",
        "posted_date": "05/05/2024",
        "salary": "$100k - $120k"
    }

    mock_logo_src.assert_awaited_once_with(page, job_url)
    mock_metadata_fields.assert_awaited_once_with(page, fields, job_url)
    mock_posted_date.assert_awaited_once_with(page, POSTED_DATE_SELECTOR, job_url)

@pytest.mark.asyncio
@patch("jobs.extractor.safe_extract_logo_src", new_callable=AsyncMock)
@patch("jobs.extractor.safe_extract_job_metadata_fields", new_callable=AsyncMock)
@patch("jobs.extractor.safe_extract_posted_date_by_class", new_callable=AsyncMock)
async def test_extract_metadata_multiple_from_page_success(
    mock_posted_date: AsyncMock, mock_metadata_fields: AsyncMock, mock_logo_src: AsyncMock
) -> None:
    page = MagicMock()
    job_url = "https://seek.com.au/job/123"
    fields = {"salary": ["job-detail-salary"]}

    mock_logo_src.return_value = "https://logo.url/logo.png"
    mock_metadata_fields.return_value = {"salary": "$100k - $120k", "location": "Sydney"}
    mock_posted_date.return_value = "05/05/2024"

    result = await extract_metadata_from_page(page, job_url, fields)

    assert result == {
        "logo_src": "https://logo.url/logo.png",
        "posted_date": "05/05/2024",
        "salary": "$100k - $120k",
        "location": "Sydney",
    }

    mock_logo_src.assert_awaited_once_with(page, job_url)
    mock_metadata_fields.assert_awaited_once_with(page, fields, job_url)
    mock_posted_date.assert_awaited_once_with(page, POSTED_DATE_SELECTOR, job_url)


@pytest.mark.asyncio
@patch("jobs.extractor.navigate_to_page", new_callable=AsyncMock)
@patch("jobs.extractor.extract_metadata_from_page", new_callable=AsyncMock)
@patch("jobs.extractor.pause_briefly", new_callable=AsyncMock)
async def test_extract_job_metadata_success(
    mock_pause: AsyncMock, mock_extract_metadata: AsyncMock, mock_navigate: AsyncMock
) -> None:
    job_url = "https://seek.com.au/job/1"
    job_metadata_fields = {"title": ["job-title"]}
    mock_page = MagicMock()

    page_pool = MagicMock()
    page_pool.acquire = AsyncMock(return_value=mock_page)
    page_pool.release = AsyncMock()

    mock_extract_metadata.return_value = {
        "logo_src": "https://logo.png",
        "posted_date": "05/05/2024",
        "title": "Senior Engineer"
    }

    result = await extract_job_metadata(job_url, job_metadata_fields, page_pool)

    assert result == {
        "logo_src": "https://logo.png",
        "posted_date": "05/05/2024",
        "title": "Senior Engineer"
    }

    mock_navigate.assert_awaited_once_with(mock_page, job_url)
    mock_extract_metadata.assert_awaited_once_with(mock_page, job_url, job_metadata_fields)
    page_pool.acquire.assert_awaited_once()
    page_pool.release.assert_awaited_once_with(mock_page)
    mock_pause.assert_awaited_once()

@pytest.mark.asyncio
@patch("jobs.extractor.fetch_job_markdown", new_callable=AsyncMock)
@patch("jobs.extractor.extract_job_metadata", new_callable=AsyncMock)
@patch("jobs.extractor.pause_briefly", new_callable=AsyncMock)
async def test_scrape_job_details_success(
    mock_pause: AsyncMock, mock_extract_metadata: AsyncMock, mock_fetch_markdown: AsyncMock
) -> None:
    job_url = "https://seek.com.au/job/123"
    crawler = MagicMock()
    page_pool = MagicMock()

    mock_fetch_markdown.return_value = "## Job Description\n- Do stuff"
    mock_extract_metadata.return_value = {
        "logo_src": "https://logo.png",
        "posted_date": "06/06/2024",
        "salary": "$100k",
    }

    result = await scrape_job_details(job_url, crawler, page_pool)

    mock_fetch_markdown.assert_awaited_once_with(job_url, crawler)
    mock_extract_metadata.assert_awaited_once_with(job_url, JOB_METADATA_FIELDS, page_pool)
    mock_pause.assert_awaited_once_with(0.05, 0.25)

    assert result == (
        "## Job Description\n- Do stuff",
        {
            "logo_src": "https://logo.png",
            "posted_date": "06/06/2024",
            "salary": "$100k",
        }
    )

@pytest.mark.asyncio
@patch("jobs.extractor.scrape_job_details", new_callable=AsyncMock)
@patch("jobs.extractor.is_recent_job", new_callable=MagicMock)
@patch("jobs.extractor.parse_job_data_from_markdown", new_callable=AsyncMock)
async def test_extract_job_data_success(
    mock_parse: AsyncMock,
    mock_is_recent: MagicMock,
    mock_scrape: AsyncMock
) -> None:
    mock_scrape.return_value = (
        "## Markdown",
        {
            "logo_src": "https://logo.png",
            "posted_date": "05/05/2024",
            "salary": "$100k"
        },
    )
    mock_is_recent.return_value = True
    mock_parse.return_value = {"experience_level": "junior"}

    ctx = ScrapeContext(
        crawler=AsyncMock(),
        page_pool=AsyncMock(),
        location_search="Sydney",
        terminate_event=MagicMock(),
        semaphore=asyncio.Semaphore(1),
        day_range_limit=7
    )

    result = await extract_job_data("url", ctx, 1)

    assert result == {
        "status": SUCCESS,
        "job": {"experience_level": "junior"},
        "job_metadata": {"logo_src":"https://logo.png", "posted_date": "05/05/2024", "salary": "$100k"}
    }
    mock_parse.assert_awaited_once_with("## Markdown", 1)
    ctx.terminate_event.set.assert_not_called()

@pytest.mark.asyncio
@patch("jobs.extractor.scrape_job_details", new_callable=AsyncMock)
async def test_extract_job_data_missing_metadata(mock_scrape: AsyncMock) -> None:
    mock_scrape.return_value = ("## Markdown", None)

    ctx = ScrapeContext(
        crawler=AsyncMock(),
        page_pool=AsyncMock(),
        location_search="Sydney",
        terminate_event=MagicMock(),
        semaphore=asyncio.Semaphore(1),
        day_range_limit=7
    )

    result = await extract_job_data("url", ctx, 1)

    assert result == {
        "status": SKIPPED,
        "job": None,
        "job_metadata": None
    }

@pytest.mark.asyncio
@patch("jobs.extractor.scrape_job_details", new_callable=AsyncMock)
async def test_extract_job_data_missing_markdown(mock_scrape: AsyncMock) -> None:
    mock_scrape.return_value = (None, {"logo_src": "https://logo.png", "posted_date": "05/05/2024", "salary": "$100k"})

    ctx = ScrapeContext(
        crawler=AsyncMock(),
        page_pool=AsyncMock(),
        location_search="Sydney",
        terminate_event=MagicMock(),
        semaphore=asyncio.Semaphore(1),
        day_range_limit=7
    )

    result = await extract_job_data("url", ctx, 1)

    assert result == {
        "status": SKIPPED,
        "job": None,
        "job_metadata": {
            "logo_src": "https://logo.png",
            "posted_date": "05/05/2024",
            "salary": "$100k"
        }
    }

@pytest.mark.asyncio
@patch("jobs.extractor.scrape_job_details", new_callable=AsyncMock)
async def test_extract_job_data_not_recent(mock_scrape: AsyncMock) -> None:
    mock_scrape.return_value = (
        "## Markdown",
        {
            "logo_src": "https://logo.png",
            "posted_date": "05/05/2024",
            "salary": "$100k"
        },
    )

    ctx = ScrapeContext(
        crawler=AsyncMock(),
        page_pool=AsyncMock(),
        location_search="Sydney",
        terminate_event=MagicMock(),
        semaphore=asyncio.Semaphore(1),
        day_range_limit=7
    )

    result = await extract_job_data("url", ctx, 1)

    assert result == {
        "status": TERMINATE,
        "job": None,
        "job_metadata": {
            "logo_src": "https://logo.png",
            "posted_date": "05/05/2024",
            "salary": "$100k"
        }
    }
    ctx.terminate_event.set.assert_called_once()

@patch("jobs.extractor.is_recent_job", return_value=True)
@patch("jobs.extractor.scrape_job_details", new_callable=AsyncMock)
@patch("jobs.extractor.parse_job_data_from_markdown", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_extract_job_data_parsing_failed(
    mock_parse: AsyncMock,
    mock_scrape: AsyncMock,
    mock_is_recent: MagicMock
) -> None:
    mock_scrape.return_value = (
        "## Markdown",
        {
            "logo_src": "https://logo.png",
            "posted_date": "05/05/2024",
            "salary": "$100k"
        },
    )
    mock_parse.return_value = None
    mock_is_recent.return_value = True

    ctx = ScrapeContext(
        crawler=AsyncMock(),
        page_pool=AsyncMock(),
        location_search="Sydney",
        terminate_event=MagicMock(),
        semaphore=asyncio.Semaphore(1),
        day_range_limit=7
    )

    result = await extract_job_data("url", ctx, 1)

    assert result == {
        "status": SKIPPED,
        "job": None,
        "job_metadata": {
            "logo_src": "https://logo.png",
            "posted_date": "05/05/2024",
            "salary": "$100k"
        }
    }






