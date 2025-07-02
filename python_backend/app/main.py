import asyncio
import logging

from clients.node_client import send_scrape_summary_to_node
from crawl4ai import AsyncWebCrawler
from markdown.fetcher import fetch_page_markdown
from pages.context import setup_scraping_context, teardown_scraping_context
from pages.listing_handler import scrape_pages
from utils.constants import CONCURRENT_JOBS_NUM, DAY_RANGE_LIMIT, TOTAL_JOBS_PER_PAGE
from utils.context import ScrapeContext
from utils.sentry import sentry_sdk
from utils.utils import get_total_job_count, get_total_pages

logger = logging.getLogger(__name__)

async def scrape_job_listing(
        base_url: str,
        location_search: str,
        pagesize: int = TOTAL_JOBS_PER_PAGE,
        max_pages: int | None = None,
        day_range_limit: int = DAY_RANGE_LIMIT
    ) -> dict:
    async def return_and_report(summary: dict):
        await send_scrape_summary_to_node(summary)
        return summary

    try:
        async with AsyncWebCrawler() as crawler:
            logger.info("AsyncWebCrawler initialized successfully!")
            playwright, browser, page_pool = await setup_scraping_context()

            try:
                markdown = await fetch_page_markdown(base_url, crawler, 1)
                if not markdown:
                    return await return_and_report({
                        "message": "No job search markdown found. Scraped 0 jobs.",
                        "terminated_early": False
                    })

                total_jobs = get_total_job_count(markdown)
                if total_jobs == 0:
                    return await return_and_report({
                        "message": "No jobs found. Scraped 0 jobs.",
                        "terminated_early": False
                    })

                total_pages = get_total_pages(total_jobs, pagesize, max_pages)
                logger.info("Detected %s jobs — scraping %s pages.", total_jobs, total_pages)

                terminate_event = asyncio.Event()
                semaphore = asyncio.Semaphore(CONCURRENT_JOBS_NUM)

                ctx = ScrapeContext(
                    crawler=crawler,
                    page_pool=page_pool,
                    location_search=location_search,
                    terminate_event=terminate_event,
                    semaphore=semaphore,
                    day_range_limit=day_range_limit
                )

                scrape_summary = await scrape_pages(base_url, ctx, total_pages)

                return await return_and_report(scrape_summary)

            finally:
                await teardown_scraping_context(playwright, browser, page_pool)

    except Exception as e:
        sentry_sdk.set_tag("component", "scrape_job_listing")
        sentry_sdk.set_extra("base_url", base_url)
        sentry_sdk.capture_message("Failed initializing AsyncWebCrawler")
        sentry_sdk.capture_exception(e)

        return await return_and_report({
            "message": f"Fatal error during job scrape: {type(e).__name__}: {e}",
            "terminated_early": False
        })










