import asyncio
import logging
import sentry_sdk

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
from utils import process_markdown_to_job_links, enrich_job_data, is_recent_job, pause_briefly, backoff_if_high_cpu, get_total_pages, parse_json_block_from_text
from utils import get_job_urls, get_total_job_count, extract_logo_src, extract_posted_date_by_class, extract_job_metadata_fields, clean_repair_parse_json, create_browser_context
from llm_job_parser import parse_job_posting
from job_validate_and_db_insert import validate_and_insert_jobs
from node_client import send_scrape_summary_to_node
from typing import Callable, Any
from page_pool import PagePool
from constants import DAY_RANGE_LIMIT, TOTAL_JOBS_PER_PAGE, MAX_RETRIES, SUCCESS, TERMINATE, SKIPPED, ERROR, CONCURRENT_JOBS_NUM, POSTED_TIME_SELECTOR, JOB_METADATA_FIELDS, BROWSER_USER_AGENT

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

sentry_sdk.init(
    dsn="https://dee8a80719e302f786f197d99dfaf812@o4509440055640064.ingest.us.sentry.io/4509440080543744",
    # Add data like request headers and IP for users,
    # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
    send_default_pii=True,
)

async def safe_extract_logo_src(page, job_url):
    sentry_sdk.add_breadcrumb(
        category="extraction",
        message=f"Attempting to extract logo src from {job_url}",
        level="info",
    )
    try:
        return await extract_logo_src(page)
    except Exception as e:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "extract_logo_src")
            scope.set_extra("job_url", job_url)
            sentry_sdk.capture_exception(e)
        return ""

async def safe_extract_job_metadata_fields(page, fields, job_url):
    sentry_sdk.add_breadcrumb(
        category="extraction",
        message=f"Attempting to extract job metadata fields from {job_url}",
        level="info",
    )
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
    sentry_sdk.add_breadcrumb(
        category="extraction",
        message=f"Attempting to extract posted date from {job_url}",
        level="info",
    )
    try:
        result = await extract_posted_date_by_class(page, class_name)
        error = result.get("error")
        if error in {"__NO_ELEMENTS__", "__NO_MATCHING_TEXT__"}:
            error_messages = {
                "__NO_ELEMENTS__": "'posted_date' selector broke - no elements found",
                "__NO_MATCHING_TEXT__": "no matching 'Posted X ago' text found"
            }
            error_message = error_messages.get(error)

            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "extract_posted_date_by_class")
                scope.set_extra("job_url", job_url)
                scope.capture_message(
                    f"Posted date extraction warning: {error_message}", 
                    level="error"
                )
            
            return {"posted_date": None}

        return {"posted_date": result.get("posted_date")}

    except Exception as e:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "extract_posted_date_by_class")
            scope.set_extra("job_url", job_url)
            sentry_sdk.capture_exception(e)
        return {"posted_date": None}
    
async def retry_with_backoff(
    func: Callable[[], Any],
    max_retries: int = 3,
    base_delay: float = 1.0,
    label: str = "operation"
):
    attempt = 0
    last_exception = None

    while attempt < max_retries:
        try:
            return await func()
        except Exception as e:
            last_exception = e
            attempt += 1

            sentry_sdk.add_breadcrumb(
                category="retry",
                message=f"[Attempt {attempt}] {label} failed: {str(e)}",
                level="warning",
            )
            logging.warning(f"[Attempt {attempt}] {label} failed: {e}")

            if attempt < max_retries:
                await asyncio.sleep(base_delay * (2 ** (attempt - 1)))

    with sentry_sdk.push_scope() as scope:
        scope.set_tag("component", "retry_with_backoff")
        scope.set_extra("operation_label", label)
        scope.set_extra("last_exception", str(last_exception))
        sentry_sdk.capture_exception(last_exception)
    
    return None


async def scrape_job_metadata(job_url, job_metadata_fields, page_pool):
    page = await page_pool.acquire()
    sentry_sdk.add_breadcrumb(
        category="navigation",
        message=f"Navigating to job URL: {job_url}",
        level="info",
    )
    try:
        async def go_to_page():
            await backoff_if_high_cpu()
            await page.goto(job_url, timeout=60000, wait_until="domcontentloaded")
            await pause_briefly(0.05, 0.25)

        result = await retry_with_backoff(
            go_to_page,
            max_retries=MAX_RETRIES,
            base_delay=1.0,
            label=f"page.goto({job_url})"
        )

        if result is None:
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "scrape_job_metadata")
                scope.set_extra("job_url", job_url)
                sentry_sdk.capture_message("Navigation to job URL failed after retries", level="error")

        sentry_sdk.add_breadcrumb(
            category="navigation",
            message=f"Page loaded successfully: {job_url}",
            level="info",
        )

        logo_src = await safe_extract_logo_src(page, job_url)
        job_metadata = await safe_extract_job_metadata_fields(page, job_metadata_fields, job_url)
        posted_date = await safe_extract_posted_date_by_class(page, POSTED_TIME_SELECTOR, job_url)

        result = {
            "logo_src": logo_src,
            "posted_date": posted_date,
            **job_metadata
        }

    finally:
        sentry_sdk.add_breadcrumb(
            category="resource",
            message=f"Releasing page for job URL: {job_url}",
            level="info"
        )
        await page_pool.release(page)
        await pause_briefly(0.05, 0.25)

    return result
    
async def generate_job_markdown(job_url, crawler):
    async def crawl():
        prune_filter = PruningContentFilter(threshold=0.5, threshold_type="fixed")
        md_generator = DefaultMarkdownGenerator(
            content_filter=prune_filter,
            options={"ignore_links": True, "ignore_images": True}
        )
        config = CrawlerRunConfig(markdown_generator=md_generator)

        sentry_sdk.add_breadcrumb(
            category="crawl",
            message=f"Starting crawl for job URL: {job_url}",
            level="info",
        )

        logging.debug(f"Starting crawl for job URL: {job_url}")
        result = await crawler.arun(job_url, config=config)
        await pause_briefly(0.05, 0.25)
        await backoff_if_high_cpu()

        if not result.success:
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "generate_job_markdown")
                scope.set_extra("job_url", job_url)
                scope.set_extra("crawler_error", result.error_message)
                sentry_sdk.capture_message("Crawler failed to generate markdown", level="error")
            return None 

        sentry_sdk.add_breadcrumb(
            category="crawl",
            message=f"Crawl successful for job URL: {job_url}",
            level="info",
        ) 

        return result.markdown.fit_markdown

    result = await retry_with_backoff(
        crawl,
        max_retries=MAX_RETRIES,
        base_delay=1.0,
        label=f"generate_job_markdown: {job_url}"
    )
    return result

async def scrape_individual_job_url(job_url, crawler, page_pool):
    markdown = await generate_job_markdown(job_url, crawler)
    job_metadata = await scrape_job_metadata(job_url, JOB_METADATA_FIELDS, page_pool)
    await pause_briefly(0.05, 0.25)
    return markdown, job_metadata

async def parse_job_data_from_markdown(job_markdown, count):
    raw_llm_output  = await parse_job_posting(job_markdown, count)
    json_block = parse_json_block_from_text(raw_llm_output)

    if isinstance(json_block, dict):
        return json_block
  
    try:
        job_data = clean_repair_parse_json(json_block)
        if not job_data:
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "parse_job_data_from_markdown")
                scope.set_extra("job_count", count)
                scope.capture_message("Parsed job data is empty after JSON repair", level="warning")
            return None

        return job_data
    
    except Exception as e:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "parse_job_data_from_markdown")
            sentry_sdk.capture_exception(e)
        return None
         
async def process_job_with_backoff(job_link, count, crawler, page_pool, location_search, terminate_event, day_range_limit):
    try:
        sentry_sdk.add_breadcrumb(
            category="process_job",
            message=f"Processing job {count + 1}: {job_link}",
            level="info",
        )

        await backoff_if_high_cpu()

        job_markdown, job_metadata = await scrape_individual_job_url(job_link, crawler, page_pool)
        await pause_briefly(0.05, 0.25)

        if not job_metadata:
            sentry_sdk.add_breadcrumb(
                category="process_job",
                message=f"Skipping job due to empty metadata: {job_link}",
                level="warning",
            )
            return {"status": SKIPPED, "job": None}

        job_data = await parse_job_data_from_markdown(job_markdown, count)
        await pause_briefly(0.05, 0.25)

        if not job_data:
            sentry_sdk.add_breadcrumb(
                category="process_job",
                message=f"Skipping job due to no JSON extracted: {job_link}",
                level="warning",
            )
            return {"status": SKIPPED, "job": None}

        job_url, quick_apply_url = get_job_urls(job_link)
        enrich_job_data(job_data, location_search, job_url, quick_apply_url, job_metadata)
        logging.debug(f"Enriched job data: {job_data}")

        if not is_recent_job(job_data, day_range_limit):
            terminate_event.set()
            sentry_sdk.add_breadcrumb(
                category="process_job",
                message=f"Early termination triggered by job date limit: {job_link}",
                level="info",
            )
            return {"status": TERMINATE, "job": None}

        return {"status": SUCCESS, "job": job_data}

    except Exception as e:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "process_job_with_backoff")
            scope.set_extra("job_url", job_link)
            sentry_sdk.capture_exception(e)
        return {"status": ERROR, "job": None}
            
async def bounded_process_job(job_link, count, crawler, page_pool, location_search, terminate_event, day_range_limit, semaphore):
    if terminate_event.is_set():
        return {"status": "terminate", "job": None, "error": None}

    async with semaphore: 
        await backoff_if_high_cpu()  
        await pause_briefly(0.05, 0.25) 
        return await process_job_with_backoff(
            job_link, count, crawler, page_pool, location_search, terminate_event, day_range_limit
        )
    
async def process_all_jobs_concurrently(job_urls, crawler, page_pool, page_num, location_search, day_range_limit):
    terminate_event = asyncio.Event()
    semaphore = asyncio.Semaphore(CONCURRENT_JOBS_NUM)
    tasks = []

    sentry_sdk.add_breadcrumb(
        category="batch",
        message=f"Starting concurrent job processing for page {page_num} with {len(job_urls)} jobs",
        level="info",
    )

    for idx, job_link in enumerate(job_urls):
        await backoff_if_high_cpu() 
        task = asyncio.create_task(
            bounded_process_job(
                job_link, idx, crawler, page_pool, location_search, terminate_event, day_range_limit, semaphore
            )
        )
        tasks.append(task)

    job_results = await asyncio.gather(*tasks)

    final_jobs = []
    early_termination = False
    n_skipped = 0
    n_errors = 0

    for job_result in job_results:
        status = job_result["status"]
        if status == TERMINATE:
            early_termination = True
        elif status == SUCCESS:
            final_jobs.append(job_result["job"])
        elif status == SKIPPED:
            n_skipped += 1
        elif status == ERROR:
            n_errors += 1
    
    n_success = len(final_jobs)
    with sentry_sdk.push_scope() as scope:
        scope.set_tag("component", "process_all_jobs_concurrently")
        scope.set_tag("page_num", page_num)
        scope.set_extra("total_jobs_attempted", len(job_results))
        scope.set_extra("jobs_successful", n_success)
        scope.set_extra("jobs_skipped", n_skipped)
        scope.set_extra("jobs_errored", n_errors)
        scope.set_extra("early_termination", early_termination)
        sentry_sdk.capture_message("Scraping job batch completed", level="info")

    sentry_sdk.add_breadcrumb(
        category="batch",
        message=f"Completed concurrent job processing for page {page_num}: success={n_success}, skipped={n_skipped}, errors={n_errors}, early_termination={early_termination}",
        level="info",
    )

    return final_jobs, early_termination

async def scrape_page_markdown(base_url, crawler, page_num):
    page_url = f"{base_url}&page={page_num}"
    await pause_briefly(1.0, 2.5)

    try:
        sentry_sdk.add_breadcrumb(
            category="crawl",
            message=f"Fetching markdown for page {page_num}: {page_url}",
            level="info",
        )
        result = await crawler.arun(page_url)
    except Exception as e:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "scrape_page_markdown")
            scope.set_tag("page_num", page_num)
            scope.set_extra("page_url", page_url)
            sentry_sdk.capture_exception(e)
        return None
    
    await backoff_if_high_cpu()

    if not result.success:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "scrape_page_markdown")
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
            scope.set_tag("component", "scrape_page_markdown")
            scope.set_tag("page_num", page_num)
            scope.set_extra("page_url", page_url)
            sentry_sdk.capture_message(
                f"No markdown found on page {page_num}",
                level="warning"
            )
        return None

    return result.markdown

async def scrape_job_listing_page(base_url, location_search, crawler, page_pool, page_num, job_count, day_range_limit):
    markdown = await scrape_page_markdown(base_url, crawler, page_num)
    if not markdown:
        return {'job_count': job_count, 'terminated_early': False, 'invalid_jobs': []}

    job_urls = process_markdown_to_job_links(markdown)
    if not job_urls:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "scrape_job_listing_page")
            scope.set_tag("page_num", page_num)
            scope.set_extra("base_url", base_url)
            scope.set_extra("markdown_preview", markdown[:500] if markdown else "N/A")
            sentry_sdk.capture_message(
                f"No job links found in markdown on page {page_num}", level="warning"
            )
        return {'job_count': job_count, 'terminated_early': False, 'invalid_jobs': []}

    page_job_data, terminated_early = await process_all_jobs_concurrently(job_urls, crawler, page_pool, page_num, location_search, day_range_limit)

    invalid_jobs = []
    if page_job_data:
        job_count, invalid_jobs = await validate_and_insert_jobs(page_job_data, page_num, job_count)
    
    await pause_briefly(0.05, 0.25)
    await backoff_if_high_cpu()

    return {
        'job_count': job_count, 
        'terminated_early': terminated_early,
        'invalid_jobs': invalid_jobs  
    }

async def scrape_job_listing(base_url, location_search, pagesize=TOTAL_JOBS_PER_PAGE, max_pages=None, day_range_limit=DAY_RANGE_LIMIT):
    async def return_and_report(summary: dict):
        await send_scrape_summary_to_node(summary)
        return summary

    try:
        async with AsyncWebCrawler() as crawler:
            logging.info("AsyncWebCrawler initialized successfully!")
            playwright, browser, context = await create_browser_context()
            page_pool = PagePool(context, max_pages=CONCURRENT_JOBS_NUM)
            await page_pool.init_pages()

            try: 
                markdown = await scrape_page_markdown(base_url, crawler, 1)
                if not markdown:
                    return await return_and_report({
                        'message': 'No job search markdown found. Scraped 0 jobs.',
                        'invalid_jobs': [],
                        'terminated_early': False
                    })

                total_jobs = get_total_job_count(markdown)
                if total_jobs == 0:
                    return await return_and_report({
                        'message': 'No jobs found. Scraped 0 jobs.',
                        'invalid_jobs': [],
                        'terminated_early': False
                    })
                
                total_pages = get_total_pages(total_jobs, pagesize, max_pages)
                logging.info(f"Detected {total_jobs} jobs — scraping {total_pages} pages.")

                job_count = 0
                all_invalid_jobs = []
                terminated_early = False
                terminated_page_num = None

                for page_num in range(1, total_pages + 1):
                    sentry_sdk.add_breadcrumb(
                        category="scraper",
                        message=f"Starting scrape for page {page_num}",
                        level="info",
                    )
                    result = await scrape_job_listing_page(base_url, location_search, crawler, page_pool, page_num, job_count, all_errors, day_range_limit)
                    job_count = result['job_count']
                    if result['invalid_jobs']:
                        all_invalid_jobs.extend(result['invalid_jobs'])
                    if result['terminated_early']:
                        terminated_early = True
                        terminated_page_num = page_num
                        break
                
                message = f"Scraped and inserted {job_count} jobs."
                if terminated_early:
                    message += f" Early termination triggered on page {terminated_page_num} due to day range limit of {day_range_limit} days."

            finally:
                sentry_sdk.add_breadcrumb(
                    category="scraper",
                    message="Cleaning up crawler and browser context",
                    level="info",
                )
                await page_pool.close_all()
                await browser.close()
                await playwright.stop()

            return await return_and_report({
                'message': message,
                'invalid_jobs': all_invalid_jobs,
                'terminated_early': terminated_early
            })
        
    except Exception as e:
        sentry_sdk.set_tag("component", "scrape_job_listing")
        sentry_sdk.set_extra("base_url", base_url)

        if 'total_jobs' in locals():
            sentry_sdk.set_extra("total_jobs", total_jobs)
        if 'total_pages' in locals():
            sentry_sdk.set_extra("total_pages", total_pages)
        if 'terminated_page_num' in locals():
            sentry_sdk.set_extra("terminated_page_num", terminated_page_num)
        if 'job_count' in locals():
            sentry_sdk.set_extra("job_count", job_count)

        sentry_sdk.capture_message("Fatal error during job scrape startup or teardown — full job run failed")
        sentry_sdk.capture_exception(e)

        return await return_and_report({
            'message': f'Fatal exception during job scrape startup or teardown: {type(e).__name__}: {e}',
            'invalid_jobs': [],
            'terminated_early': False
        })

    






