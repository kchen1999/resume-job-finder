import logging

logger = logging.getLogger(__name__)
import re

import sentry_sdk
from markdown.fetcher import fetch_job_markdown
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
from utils.retry import retry_with_backoff
from utils.utils import backoff_if_high_cpu, get_posted_date, is_recent_job, pause_briefly

from jobs.parser import parse_job_data_from_markdown


async def extract_logo_src(page):
    await pause_briefly()
    logo_element = await page.query_selector(LOGO_SELECTOR)
    await backoff_if_high_cpu()
    if logo_element:
        logo_src = await logo_element.get_attribute("src")
        logger.debug(f"Logo found with src: {logo_src}")
        return logo_src
    logger.warning("Logo element not found.")
    return ""

async def extract_job_metadata_fields(page, job_metadata_fields):
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
                logger.exception(f"Error extracting {key} with selector '{selector}': {e}")
                field_errors[key] = str(e)

        if not value_found:
            results[key] = ""
            logger.warning(f"No valid element found for job field '{key}'")
            if key not in field_errors:
                field_errors[key] = "Element not found"

        await pause_briefly()

    return results, field_errors

async def extract_posted_date_by_class(page, class_name):
    await pause_briefly()
    try:
        selector = f'span.{class_name.replace(" ", ".")}'
        elements = await page.query_selector_all(selector)

        if not elements:
            logger.warning("No elements found for posted date selector.")
            return {"posted_date": None, "error": NO_ELEMENTS}

        for elem in elements:
            await backoff_if_high_cpu()
            text = (await elem.inner_text()).strip()
            logger.debug(f"Found element text: {text}")

            match = re.search(r"Posted (\d+)([dhm]) ago", text)
            if match:
                value, unit = int(match.group(1)), match.group(2)
                days_ago = value if unit == "d" else 0
                posted_date = get_posted_date(days_ago)
                logger.debug(f"Extracted posted date: {posted_date}")
                return {"posted_date": posted_date, "error": None}

        return {"posted_date": None, "error": NO_MATCHING_TEXT}

    except Exception:
        raise

async def safe_extract_logo_src(page, job_url):
    try:
        return await extract_logo_src(page)
    except Exception as e:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "extract_logo_src")
            scope.set_extra("job_url", job_url)
            sentry_sdk.capture_exception(e)
        return ""

async def safe_extract_job_metadata_fields(page, fields, job_url):
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

        return results

    except Exception as e:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "extract_job_metadata_fields")
            scope.set_extra("job_url", job_url)
            sentry_sdk.capture_exception(e)
        return {}

async def safe_extract_posted_date_by_class(page, class_name, job_url):
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


async def extract_metadata_from_page(page, job_url, fields):
    logo_src = await safe_extract_logo_src(page, job_url)
    job_metadata = await safe_extract_job_metadata_fields(page, fields, job_url)
    posted_date = await safe_extract_posted_date_by_class(page, POSTED_DATE_SELECTOR, job_url)
    return {
        "logo_src": logo_src,
        "posted_date": posted_date,
        **job_metadata
    }

async def navigate_to_page(page, job_url):
    async def go():
        await backoff_if_high_cpu()
        await page.goto(job_url, timeout=60000, wait_until="domcontentloaded")
        await pause_briefly(0.05, 0.25)

    result = await retry_with_backoff(
        go, max_retries=MAX_RETRIES, base_delay=1.0, label=f"page.goto({job_url})"
    )
    return result


async def extract_job_metadata(job_url, job_metadata_fields, page_pool):
    page = await page_pool.acquire()
    try:
        await navigate_to_page(page, job_url)
        metadata = await extract_metadata_from_page(page, job_url, job_metadata_fields)

    finally:
        await page_pool.release(page)
        await pause_briefly(0.05, 0.25)
    return metadata

async def scrape_job_details(job_url, crawler, page_pool):
    markdown = await fetch_job_markdown(job_url, crawler)
    job_metadata = await extract_job_metadata(job_url, JOB_METADATA_FIELDS, page_pool)
    await pause_briefly(0.05, 0.25)
    return markdown, job_metadata

async def extract_job_data(job_url, crawler, page_pool, count, terminate_event, day_range_limit):
    job_markdown, job_metadata = await scrape_job_details(job_url, crawler, page_pool)
    if not job_metadata:
        return {"status": SKIPPED, "job": None, "job_metadata": None}

    if not job_markdown:
        return {"status": SKIPPED, "job": None, "job_metadata": job_metadata}

    if not is_recent_job(job_metadata, day_range_limit):
        terminate_event.set()
        return {"status": TERMINATE, "job": None, "job_metadata": job_metadata}

    job_data = await parse_job_data_from_markdown(job_markdown, count)
    if not job_data:
        return {"status": SKIPPED, "job": None, "job_metadata": job_metadata}

    return {"status": SUCCESS, "job": job_data, "job_metadata": job_metadata}




