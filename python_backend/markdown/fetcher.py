import logging

import sentry_sdk
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from utils.constants import MAX_RETRIES
from utils.retry import retry_with_backoff
from utils.utils import backoff_if_high_cpu, pause_briefly

logger = logging.getLogger(__name__)

async def fetch_page_markdown(base_url: str, crawler: AsyncWebCrawler, page_num: int) -> str | None:
    page_url = f"{base_url}&page={page_num}"
    await pause_briefly(1.0, 2.5)

    try:
        result = await crawler.arun(page_url)
    except Exception as e:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "fetch_page_markdown")
            scope.set_tag("page_num", page_num)
            scope.set_extra("page_url", page_url)
            sentry_sdk.capture_exception(e)
        return None

    await backoff_if_high_cpu()

    if not result.success:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "fetch_page_markdown")
            scope.set_tag("page_num", page_num)
            scope.set_extra("page_url", page_url)
            scope.set_extra("status_code", result.status_code)
            sentry_sdk.capture_message(
                f"Crawl failed on page {page_num}: {result.error_message or 'Unknown error'}",
                level="error"
            )
        return None

    if not result.markdown:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "fetch_page_markdown")
            scope.set_tag("page_num", page_num)
            scope.set_extra("page_url", page_url)
            sentry_sdk.capture_message(
                f"No markdown found on page {page_num}",
                level="warning"
            )
        return None

    return result.markdown

async def fetch_job_markdown(job_url: str, crawler: AsyncWebCrawler) -> str | None:
    async def crawl():
        prune_filter = PruningContentFilter(threshold=0.5, threshold_type="fixed")
        md_generator = DefaultMarkdownGenerator(
            content_filter=prune_filter,
            options={"ignore_links": True, "ignore_images": True}
        )
        config = CrawlerRunConfig(markdown_generator=md_generator)

        logger.debug("Starting crawl for job URL: %s", job_url)
        result = await crawler.arun(job_url, config=config)
        await pause_briefly(0.05, 0.25)
        await backoff_if_high_cpu()

        if not result.success:
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "fetch_job_markdown")
                scope.set_extra("job_url", job_url)
                scope.set_extra("crawler_error", result.error_message)
                sentry_sdk.capture_message("Crawler failed to fetch markdown", level="error")
            return None

        return result.markdown.fit_markdown

    return await retry_with_backoff(
        crawl,
        max_retries=MAX_RETRIES,
        base_delay=1.0,
        label=f"fetch_job_markdown: {job_url}"
    )

