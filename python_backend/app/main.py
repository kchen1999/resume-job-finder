import logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

from crawl4ai import AsyncWebCrawler
from markdown.fetcher import fetch_page_markdown
from pages.context import setup_scraping_context, teardown_scraping_context
from pages.listing_handler import scrape_pages
from utils.constants import TOTAL_JOBS_PER_PAGE, DAY_RANGE_LIMIT
from utils.utils import get_total_job_count, get_total_pages
from utils.sentry import *
from clients.node_client import send_scrape_summary_to_node

async def scrape_job_listing(base_url, location_search, pagesize=TOTAL_JOBS_PER_PAGE, max_pages=None, day_range_limit=DAY_RANGE_LIMIT):
    async def return_and_report(summary: dict):
        await send_scrape_summary_to_node(summary)
        return summary

    try:
        async with AsyncWebCrawler() as crawler:
            logging.info("AsyncWebCrawler initialized successfully!")
            playwright, browser, page_pool = await setup_scraping_context()

            try: 
                markdown = await fetch_page_markdown(base_url, crawler, 1)
                if not markdown:
                    return await return_and_report({
                        'message': 'No job search markdown found. Scraped 0 jobs.',
                        'terminated_early': False
                    })

                total_jobs = get_total_job_count(markdown)
                if total_jobs == 0:
                    return await return_and_report({
                        'message': 'No jobs found. Scraped 0 jobs.',
                        'terminated_early': False
                    })
                
                total_pages = get_total_pages(total_jobs, pagesize, max_pages)
                logging.info(f"Detected {total_jobs} jobs — scraping {total_pages} pages.")

                scrape_summary = await scrape_pages(base_url,
                    location_search,
                    crawler,
                    page_pool,
                    total_pages,
                    day_range_limit
                )

                return await return_and_report(scrape_summary)

            finally:
                await teardown_scraping_context(playwright, browser, page_pool)

    except Exception as e:
        sentry_sdk.set_tag("component", "scrape_job_listing")
        sentry_sdk.set_extra("base_url", base_url)
        sentry_sdk.capture_message("Failed initializing AsyncWebCrawler")
        sentry_sdk.capture_exception(e)

        return await return_and_report({
            'message': f'Fatal error during job scrape: {type(e).__name__}: {e}',
            'terminated_early': False
        })



    






