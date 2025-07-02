import logging
import re

import sentry_sdk
from crawl4ai import AsyncWebCrawler
from jobs.parser import parse_job_data_from_markdown
from markdown.fetcher import fetch_job_markdown
from pages.pool import PagePool
from playwright.async_api import Page
from utils.constants import (
    JOB_METADATA_FIELDS,
    LOGO_SELECTOR,
    MAX_RETRIES,
    NO_ELEMENTS,
    NO_MATCHING_TEXT,
    POSTED_DATE_SELECTOR,
    SKIPPED,
    SUCCESS,
    TERMINATE,
)
from utils.context import ScrapeContext
from utils.retry import retry_with_backoff
from utils.utils import backoff_if_high_cpu, get_posted_date, is_recent_job, pause_briefly

logger = logging.getLogger(__name__)

async def extract_logo_src(page: Page) -> str:
    await pause_briefly()
    logo_element = await page.query_selector(LOGO_SELECTOR)
    await backoff_if_high_cpu()
    if logo_element:
        logo_src = await logo_element.get_attribute("src")
        logger.debug("Logo found with src: %s", logo_src)
        return logo_src
    logger.warning("Logo element not found.")
    return ""

async def extract_job_metadata_fields(page: Page, job_metadata_fields: dict) -> tuple:
    results = {}
    field_errors = {}

    for key, selectors in job_metadata_fields.items():
        await backoff_if_high_cpu()
        value_found = False
        for selector in selectors:
            try:
                elem = await page.query_selector(f'[data-automation="{selector}"]')
                if elem:
                    text = (await elem.inner_text()).strip()
                    results[key] = text
                    value_found = True
                    break

            except Exception as e:
                logger.exception("Error extracting %s with selector '%s'", key, selector)
                field_errors[key] = str(e)

        if not value_found:
            results[key] = ""
            logger.warning("No valid element found for job field '%s'", key)
            if key not in field_errors:
                field_errors[key] = "Element not found"

        await pause_briefly()

    return results, field_errors

async def extract_posted_date_by_class(page: Page, class_name: str) -> dict:
    await pause_briefly()

    selector = f'span.{class_name.replace(" ", ".")}'
    elements = await page.query_selector_all(selector)

    if not elements:
        logger.warning("No elements found for posted date selector.")
        return {"posted_date": None, "error": NO_ELEMENTS}

    for elem in elements:
        await backoff_if_high_cpu()
        text = (await elem.inner_text()).strip()
        logger.debug("Found element text: %s", text)

        match = re.search(r"Posted (\d+)([dhm]) ago", text)
        if match:
            value, unit = int(match.group(1)), match.group(2)
            days_ago = value if unit == "d" else 0
            posted_date = get_posted_date(days_ago)
            logger.debug("Extracted posted date: %s", posted_date)
            return {"posted_date": posted_date, "error": None}

    return {"posted_date": None, "error": NO_MATCHING_TEXT}

async def safe_extract_logo_src(page: Page, job_url: str) -> str:
    try:
        return await extract_logo_src(page)
    except Exception as e:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "extract_logo_src")
            scope.set_extra("job_url", job_url)
            sentry_sdk.capture_exception(e)
        return ""

async def safe_extract_job_metadata_fields(page: Page, fields: dict, job_url: str) -> dict:
    try:
        results, field_errors = await extract_job_metadata_fields(page, fields)

        for key, error in field_errors.items():
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "extract_job_metadata_fields")
                scope.set_extra("job_url", job_url)
                scope.set_extra("field", key)
                scope.set_extra("error_detail", error)
                sentry_sdk.capture_message(
                    f"Job metadata extraction issue for field '{key}': {error}",
                    level="error"
                )

    except Exception as e:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "extract_job_metadata_fields")
            scope.set_extra("job_url", job_url)
            sentry_sdk.capture_exception(e)
        return {}

    else:
        return results

async def safe_extract_posted_date_by_class(page: Page, class_name: str, job_url: str) -> str | None:
    try:
        result = await extract_posted_date_by_class(page, class_name)
        error = result.get("error")
        if error in {NO_ELEMENTS, NO_MATCHING_TEXT}:
            error_messages = {
                NO_ELEMENTS: "'posted_date' selector broke - no elements found",
                NO_MATCHING_TEXT: "no matching 'Posted X ago' text found"
            }
            error_message = error_messages.get(error)

            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "extract_posted_date_by_class")
                scope.set_extra("job_url", job_url)
                scope.capture_message(
                    f"Posted date extraction warning: {error_message}",
                    level="error"
                )

            return None

        return result.get("posted_date")

    except Exception as e:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "extract_posted_date_by_class")
            scope.set_extra("job_url", job_url)
            sentry_sdk.capture_exception(e)
        return None


async def extract_metadata_from_page(page: Page, job_url: str, fields: dict) -> dict:
    logo_src = await safe_extract_logo_src(page, job_url)
    job_metadata = await safe_extract_job_metadata_fields(page, fields, job_url)
    posted_date = await safe_extract_posted_date_by_class(page, POSTED_DATE_SELECTOR, job_url)
    return {
        "logo_src": logo_src,
        "posted_date": posted_date,
        **job_metadata
    }

async def navigate_to_page(page: Page, job_url: str) -> None:
    async def go() -> None:
        await backoff_if_high_cpu()
        await page.goto(job_url, timeout=60000, wait_until="domcontentloaded")
        await pause_briefly(0.05, 0.25)

    return await retry_with_backoff(
        go, max_retries=MAX_RETRIES, base_delay=1.0, label=f"page.goto({job_url})"
    )


async def extract_job_metadata(job_url: str, job_metadata_fields: dict, page_pool: PagePool) -> dict:
    page = await page_pool.acquire()
    try:
        await navigate_to_page(page, job_url)
        metadata = await extract_metadata_from_page(page, job_url, job_metadata_fields)

    finally:
        await page_pool.release(page)
        await pause_briefly(0.05, 0.25)
    return metadata

async def scrape_job_details(job_url: str, crawler: AsyncWebCrawler, page_pool: PagePool) -> tuple:
    markdown = await fetch_job_markdown(job_url, crawler)
    job_metadata = await extract_job_metadata(job_url, JOB_METADATA_FIELDS, page_pool)
    await pause_briefly(0.05, 0.25)
    return markdown, job_metadata

async def extract_job_data(job_url : str, ctx: ScrapeContext, count: int) -> dict:
    job_markdown, job_metadata = await scrape_job_details(job_url, ctx.crawler, ctx.page_pool)
    if not job_metadata:
        return {"status": SKIPPED, "job": None, "job_metadata": None}

    if not job_markdown:
        return {"status": SKIPPED, "job": None, "job_metadata": job_metadata}

    if not is_recent_job(job_metadata, ctx.day_range_limit):
        ctx.terminate_event.set()
        return {"status": TERMINATE, "job": None, "job_metadata": job_metadata}

    job_data = await parse_job_data_from_markdown(job_markdown, count)
    if not job_data:
        return {"status": SKIPPED, "job": None, "job_metadata": job_metadata}

    return {"status": SUCCESS, "job": job_data, "job_metadata": job_metadata}




