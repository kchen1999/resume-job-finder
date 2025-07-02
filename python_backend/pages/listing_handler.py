import logging

import sentry_sdk
from concurrency.batch_runner import process_jobs_concurrently
from jobs.inserter import insert_jobs_into_database
from jobs.validator import validate_jobs
from markdown.fetcher import fetch_page_markdown
from utils.context import ScrapeContext
from utils.utils import backoff_if_high_cpu, extract_job_urls, pause_briefly

logger = logging.getLogger(__name__)

def extract_job_urls_from_markdown(markdown: str) -> list | None:
    job_urls = extract_job_urls(markdown)
    if not job_urls:
        logger.warning("No job urls extracted from page markdown")
        return None
    for url in job_urls:
        logger.info("Scraping: %s", url)
    return job_urls

async def process_job_listing_page(base_url: str, ctx: ScrapeContext, page_num: int, job_count: int) -> dict:
    markdown = await fetch_page_markdown(base_url, ctx.crawler, page_num)
    if not markdown:
        return {"job_count": job_count, "terminated_early": False}

    job_urls = extract_job_urls_from_markdown(markdown)
    if not job_urls:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "process_job_listing_page")
            scope.set_tag("page_num", page_num)
            scope.set_extra("base_url", base_url)
            scope.set_extra("markdown_preview", markdown[:500] if markdown else "N/A")
            sentry_sdk.capture_message(
                f"No job urls found in markdown on page {page_num}", level="warning"
            )
        return {"job_count": job_count, "terminated_early": False}

    page_job_data, terminated_early = await process_jobs_concurrently(job_urls, ctx, page_num)

    if page_job_data:
        cleaned_jobs = await validate_jobs(page_job_data)
        job_count = await insert_jobs_into_database(cleaned_jobs, page_num, job_count)

    await pause_briefly(0.05, 0.25)
    await backoff_if_high_cpu()

    return {
        "job_count": job_count,
        "terminated_early": terminated_early
    }

async def scrape_pages(base_url: str, ctx: ScrapeContext, total_pages: int) -> dict:
    job_count = 0
    terminated_early = False
    terminated_page_num = None

    for page_num in range(1, total_pages + 1):
        result = await process_job_listing_page(
            base_url,
            ctx,
            page_num,
            job_count,
        )
        job_count = result["job_count"]

        if result.get("terminated_early"):
            terminated_early = True
            terminated_page_num = page_num
            break

    message = f"Scraped and inserted {job_count} jobs."
    if terminated_early:
        message += (
            f" Early termination triggered on page {terminated_page_num} "
            f"due to day range limit of {ctx.day_range_limit} days."
        )

    return {
        "message": message,
        "terminated_early": terminated_early
    }
