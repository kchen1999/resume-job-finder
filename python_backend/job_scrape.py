import asyncio
import logging
import sentry_sdk

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
from utils import process_markdown_to_job_urls, enrich_job_data, is_recent_job, pause_briefly, backoff_if_high_cpu, get_total_pages, parse_json_block_from_text
from utils import get_job_urls, get_total_job_count, extract_logo_src, extract_posted_date_by_class, extract_job_metadata_fields, clean_repair_parse_json, create_browser_context
from llm_job_parser import parse_job_posting
from job_validate_and_db_insert import validate_jobs, insert_jobs_into_database
from node_client import send_scrape_summary_to_node
from typing import Callable, Any
from page_pool import PagePool
from constants import DAY_RANGE_LIMIT, TOTAL_JOBS_PER_PAGE, MAX_RETRIES, SUCCESS, TERMINATE, SKIPPED, ERROR, CONCURRENT_JOBS_NUM, POSTED_TIME_SELECTOR, JOB_METADATA_FIELDS, NO_ELEMENTS, NO_MATCHING_TEXT

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

sentry_sdk.init(
    dsn="https://dee8a80719e302f786f197d99dfaf812@o4509440055640064.ingest.us.sentry.io/4509440080543744",
    # Add data like request headers and IP for users,
    # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
    send_default_pii=True,
)

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
            logging.warning(f"[Attempt {attempt}] {label} failed: {e}")

            if attempt < max_retries:
                await asyncio.sleep(base_delay * (2 ** (attempt - 1)))

    with sentry_sdk.push_scope() as scope:
        scope.set_tag("component", "retry_with_backoff")
        scope.set_extra("operation_label", label)
        scope.set_extra("last_exception", str(last_exception))
        sentry_sdk.capture_exception(last_exception)
    
    return None


async def navigate_to_page(page, job_url):
    async def go():
        await backoff_if_high_cpu()
        await page.goto(job_url, timeout=60000, wait_until="domcontentloaded")
        await pause_briefly(0.05, 0.25)

    result = await retry_with_backoff(
        go, max_retries=MAX_RETRIES, base_delay=1.0, label=f"page.goto({job_url})"
    )
    return result

async def extract_metadata_from_page(page, job_url, fields):
    logo_src = await safe_extract_logo_src(page, job_url)
    job_metadata = await safe_extract_job_metadata_fields(page, fields, job_url)
    posted_date = await safe_extract_posted_date_by_class(page, POSTED_TIME_SELECTOR, job_url)
    return {
        "logo_src": logo_src,
        "posted_date": posted_date,
        **job_metadata
    }

async def extract_job_metadata(job_url, job_metadata_fields, page_pool):
    page = await page_pool.acquire()
    try:
        result = await navigate_to_page(page, job_url)
        if result is None:
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "extract_job_metadata")
                scope.set_extra("job_url", job_url)
                sentry_sdk.capture_message("Navigation failed after retries", level="error")
        metadata = await extract_metadata_from_page(page, job_url, job_metadata_fields)

    finally:
        await page_pool.release(page)
        await pause_briefly(0.05, 0.25)
    return metadata
    
async def fetch_job_markdown(job_url, crawler):
    async def crawl():
        prune_filter = PruningContentFilter(threshold=0.5, threshold_type="fixed")
        md_generator = DefaultMarkdownGenerator(
            content_filter=prune_filter,
            options={"ignore_links": True, "ignore_images": True}
        )
        config = CrawlerRunConfig(markdown_generator=md_generator)

        logging.debug(f"Starting crawl for job URL: {job_url}")
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

    result = await retry_with_backoff(
        crawl,
        max_retries=MAX_RETRIES,
        base_delay=1.0,
        label=f"fetch_job_markdown: {job_url}"
    )
    return result

async def scrape_job_details(job_url, crawler, page_pool):
    markdown = await fetch_job_markdown(job_url, crawler)
    job_metadata = await extract_job_metadata(job_url, JOB_METADATA_FIELDS, page_pool)
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
                scope.capture_message("Parsed job data is empty after JSON repair", level="warning")
            return None

        return job_data
    
    except Exception as e:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "parse_job_data_from_markdown")
            sentry_sdk.capture_exception(e)
        return None
    
async def extract_job_data(job_url, crawler, page_pool, count):
    job_markdown, job_metadata = await scrape_job_details(job_url, crawler, page_pool)
    if not job_metadata:
        return {"status": SKIPPED, "job": None, "job_metadata": None}
    
    if not job_markdown:
        return {"status": SKIPPED, "job": None, "job_metadata": job_metadata}
    
    job_data = await parse_job_data_from_markdown(job_markdown, count)
    if not job_data:
        return {"status": SKIPPED, "job": None, "job_metadata": job_metadata}

    return {"status": SUCCESS, "job": job_data, "job_metadata": job_metadata}

async def validate_and_enrich_job_data(job_data, job_url, location_search, job_metadata, day_range_limit, terminate_event):
    job_url, quick_apply_url = get_job_urls(job_url)
    enrich_job_data(job_data, location_search, job_url, quick_apply_url, job_metadata)

    if not is_recent_job(job_data, day_range_limit):
        terminate_event.set()
        return {"status": TERMINATE, "job": None}

    return {"status": SUCCESS, "job": job_data}
         
async def process_job_with_retries(job_url, count, crawler, page_pool, location_search, terminate_event, day_range_limit):
    try:
        await backoff_if_high_cpu()
        job_extraction = await extract_job_data(job_url, crawler, page_pool, count)
        await pause_briefly(0.05, 0.25)

        if job_extraction ["status"] != SUCCESS:
            return job_extraction 

        job_result = await validate_and_enrich_job_data(
            job_extraction["job"],
            job_url,
            location_search,
            job_extraction["job_metadata"],
            day_range_limit,
            terminate_event
        )
        await pause_briefly(0.05, 0.25)
        return job_result

    except Exception as e:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "process_job_with_retries")
            scope.set_extra("job_url", job_url)
            sentry_sdk.capture_exception(e)
        return {"status": ERROR, "job": None}
            
async def process_job_with_semaphore(job_url, count, crawler, page_pool, location_search, terminate_event, day_range_limit, semaphore):
    if terminate_event.is_set():
        return {"status": "terminate", "job": None}

    async with semaphore: 
        await backoff_if_high_cpu()  
        await pause_briefly(0.05, 0.25) 
        return await process_job_with_retries(
            job_url, count, crawler, page_pool, location_search, terminate_event, day_range_limit
        )
    
def aggregate_job_results(job_results):
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

    return final_jobs, early_termination, n_skipped, n_errors
    
async def process_jobs_concurrently(job_urls, crawler, page_pool, page_num, location_search, day_range_limit):
    terminate_event = asyncio.Event()
    semaphore = asyncio.Semaphore(CONCURRENT_JOBS_NUM)
    tasks = []

    for idx, job_url in enumerate(job_urls):
        await backoff_if_high_cpu() 
        task = asyncio.create_task(
            process_job_with_semaphore(
                job_url, idx, crawler, page_pool, location_search, terminate_event, day_range_limit, semaphore
            )
        )
        tasks.append(task)

    job_results = await asyncio.gather(*tasks)

    final_jobs, early_termination, n_skipped, n_errors = aggregate_job_results(job_results)
    n_success = len(final_jobs)
    
    with sentry_sdk.push_scope() as scope:
        scope.set_tag("component", "process_jobs_concurrently")
        scope.set_tag("page_num", page_num)
        scope.set_extra("total_jobs_attempted", len(job_results))
        scope.set_extra("jobs_successful", n_success)
        scope.set_extra("jobs_skipped", n_skipped)
        scope.set_extra("jobs_errored", n_errors)
        scope.set_extra("early_termination", early_termination)
        sentry_sdk.capture_message("Scraping job batch completed", level="info")

    return final_jobs, early_termination

async def fetch_page_markdown(base_url, crawler, page_num):
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

async def process_job_listing_page(base_url, location_search, crawler, page_pool, page_num, job_count, day_range_limit):
    markdown = await fetch_page_markdown(base_url, crawler, page_num)
    if not markdown:
        return {'job_count': job_count, 'terminated_early': False}

    job_urls = process_markdown_to_job_urls(markdown)
    if not job_urls:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "process_job_listing_page")
            scope.set_tag("page_num", page_num)
            scope.set_extra("base_url", base_url)
            scope.set_extra("markdown_preview", markdown[:500] if markdown else "N/A")
            sentry_sdk.capture_message(
                f"No job links found in markdown on page {page_num}", level="warning"
            )
        return {'job_count': job_count, 'terminated_early': False}

    page_job_data, terminated_early = await process_jobs_concurrently(job_urls, crawler, page_pool, page_num, location_search, day_range_limit)

    if page_job_data:
        cleaned_jobs = await validate_jobs(page_job_data)
        job_count = await insert_jobs_into_database(cleaned_jobs, page_num, job_count)
    
    await pause_briefly(0.05, 0.25)
    await backoff_if_high_cpu()

    return {
        'job_count': job_count, 
        'terminated_early': terminated_early
    }

async def setup_scraping_context():
    playwright, browser, context = await create_browser_context()
    page_pool = PagePool(context, max_pages=CONCURRENT_JOBS_NUM)
    await page_pool.init_pages()
    return playwright, browser, page_pool


async def teardown_scraping_context(playwright, browser, page_pool):
    await page_pool.close_all()
    await browser.close()
    await playwright.stop()


async def scrape_pages(base_url, location_search, crawler, page_pool, total_pages, day_range_limit):
    job_count = 0
    terminated_early = False
    terminated_page_num = None

    for page_num in range(1, total_pages + 1):
        result = await process_job_listing_page(
            base_url,
            location_search,
            crawler,
            page_pool,
            page_num,
            job_count,
            day_range_limit
        )
        job_count = result['job_count']

        if result.get('terminated_early'):
            terminated_early = True
            terminated_page_num = page_num
            break

    message = f"Scraped and inserted {job_count} jobs."
    if terminated_early:
        message += f" Early termination triggered on page {terminated_page_num} due to day range limit of {day_range_limit} days."

    return {
        'message': message,
        'terminated_early': terminated_early
    }

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

                scrape_summary = await scrape_pages(
                    base_url,
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

        for var in ['total_jobs', 'total_pages', 'terminated_page_num', 'job_count']:
            if var in locals():
                sentry_sdk.set_extra(var, locals()[var])

        sentry_sdk.capture_message("Fatal error during job scrape startup or teardown — full job run failed")
        sentry_sdk.capture_exception(e)

        return await return_and_report({
            'message': f'Fatal exception during job scrape startup or teardown: {type(e).__name__}: {e}',
            'terminated_early': False
        })

    






