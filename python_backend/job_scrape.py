import asyncio
import math
import logging
import traceback

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
from playwright.async_api import async_playwright
from utils import process_markdown_to_job_links, parse_job_data_from_markdown, enrich_job_data, is_job_within_date_range, pause_briefly, override_experience_level_with_title, backoff_if_high_cpu
from utils import extract_job_urls, extract_total_job_count, extract_logo_src, extract_posted_date_by_class, extract_job_metadata_fields, set_default_work_model, normalize_experience_level, retry_with_backoff
from job_validate_and_db_insert import validate_and_insert_jobs
from node_client import send_scrape_summary_to_node
from page_pool import PagePool
from constants import DAY_RANGE_LIMIT, TOTAL_JOBS_PER_PAGE, MAX_RETRIES, SUCCESS, TERMINATE, SKIPPED, ERROR, CONCURRENT_JOBS_NUM, POSTED_TIME_SELECTOR, JOB_METADATA_FIELDS, BROWSER_USER_AGENT

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

async def create_browser_context():
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--single-process",
            "--no-zygote"
        ],
    )
    context = await browser.new_context(
        viewport={"width": 1280, "height": 720},
        locale="en-US",
        timezone_id="Australia/Sydney",
        user_agent=BROWSER_USER_AGENT["User-Agent"],
        java_script_enabled=False
    )
    await context.add_init_script(
        """() => {
            Object.defineProperty(navigator, 'webdriver', {get: () => false});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        }"""
    )

    await context.route("**/*", lambda route, request: asyncio.create_task(
        route.abort() if request.resource_type in ["image", "font", "stylesheet"] else route.continue_()
    ))

    return playwright, browser, context

async def scrape_job_metadata(url, job_metadata_fields, page_pool):
    attempt = 0
    page = await page_pool.acquire()
    try:
        async def go_to_page():
            logging.debug(f"[Attempt {attempt+1}] Navigating to page: {url}")
            await backoff_if_high_cpu()
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await pause_briefly(0.05, 0.25)

        await retry_with_backoff(
            go_to_page,
            max_retries=MAX_RETRIES,
            base_delay=1.0,
            label=f"page.goto({url})"
        )
        logging.debug(f"Page loaded: {url}")

        logo_src = await extract_logo_src(page)
        job_metadata = await extract_job_metadata_fields(page, job_metadata_fields)
        posted_result = await extract_posted_date_by_class(page, POSTED_TIME_SELECTOR)

        return {
            "logo_src": logo_src,
            "posted_time": posted_result.get("posted_time"),
            "posted_time_error": posted_result.get("error"),
            **job_metadata
        }

    except Exception as e:
        logging.error(f"Failed to scrape metadata for {url}: {e}")
        return {"error": f"Failed to scrape metadata: {str(e)}"}

    finally:
        await page_pool.release(page)
        await pause_briefly(0.05, 0.25)
    
async def generate_job_markdown(job_url, crawler):
    async def crawl():
        prune_filter = PruningContentFilter(threshold=0.5, threshold_type="fixed")
        md_generator = DefaultMarkdownGenerator(
            content_filter=prune_filter,
            options={"ignore_links": True, "ignore_images": True}
        )
        config = CrawlerRunConfig(markdown_generator=md_generator)

        logging.debug(f"Crawling job URL: {job_url}")
        result = await crawler.arun(job_url, config=config)
        await pause_briefly(0.05, 0.25)
        await backoff_if_high_cpu()

        if not result.success:
            raise Exception(result.error_message)

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
         
async def process_job_with_backoff(job_link, count, crawler, page_pool, location_search, terminate_event, day_range_limit):
    try:
        print("Scraping job:", count + 1)
        print("Scraping:", job_link)
        await backoff_if_high_cpu()
        job_markdown, job_metadata = await scrape_individual_job_url(job_link, crawler, page_pool)
        await pause_briefly(0.05, 0.25)

        if job_metadata.get("error"):
            print(f"Skipping job {job_link}, error scraping metadata: {job_metadata['error']}")
            return {"status": SKIPPED, "job": None, "error": job_metadata["error"]}

        if job_metadata.get("posted_time_error") in {"__NO_ELEMENTS__", "__NO_MATCHING_TEXT__"}:
            error_message = "'posted_date' selector broke" if job_metadata["posted_time_error"] == "__NO_ELEMENTS__" \
                            else "no matching 'Posted X ago' text found"
            print(f"Skipping job {job_link}, posted date issue: {error_message}")
            return {
                "status": SKIPPED,
                "job": None,
                "error": f"Posted date selector issue: {error_message}"
            }

        job_data = await parse_job_data_from_markdown(job_markdown, count)
        await pause_briefly(0.05, 0.25)
        if not job_data:
            print(f"Skipping job {job_link}, no JSON extracted.")
            return {"status": SKIPPED, "job": None, "error": "No JSON extracted"}

        job_data = set_default_work_model(job_data)
        job_url, quick_apply_url = extract_job_urls(job_link)
        enrich_job_data(job_data, location_search, job_url, quick_apply_url, job_metadata)
        print("Enriched job data: ", job_data)

        if not is_job_within_date_range(job_data, day_range_limit):
            terminate_event.set()
            return {"status": TERMINATE, "job": None, "error": None}

        job_data = override_experience_level_with_title(job_data)
        job_data = normalize_experience_level(job_data)
        await pause_briefly(0.05, 0.25)
        return {"status": SUCCESS, "job": job_data, "error": None}

    except Exception as e:
        return {
            "status": ERROR,
            "job": None,
            "error": f"Unexpected error in process_job_with_backoff: {str(e)}"
        }
            
async def bounded_process_job(job_link, count, crawler, page_pool, location_search, terminate_event, day_range_limit, semaphore):
    if terminate_event.is_set():
        return {"status": "terminate", "job": None, "error": None}

    async with semaphore: 
        await backoff_if_high_cpu()  
        await pause_briefly(1.0, 2.0) 
        return await process_job_with_backoff(
            job_link, count, crawler, page_pool, location_search, terminate_event, day_range_limit
        )
    
async def process_all_jobs_concurrently(job_urls, crawler, page_pool, location_search, day_range_limit):
    terminate_event = asyncio.Event()
    semaphore = asyncio.Semaphore(CONCURRENT_JOBS_NUM)

    tasks = []

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
    all_errors = []
    early_termination = False

    for job_result in job_results:
        if job_result["status"] == TERMINATE:
            early_termination = True
        elif job_result["status"] == SUCCESS:
            final_jobs.append(job_result["job"])
        elif job_result["status"] in {SKIPPED, ERROR}:
            all_errors.append(job_result["error"])

    return final_jobs, early_termination, all_errors

async def scrape_page_markdown(base_url, crawler, page_num, all_errors):
    page_url = f"{base_url}&page={page_num}"
    await pause_briefly(1, 3)

    try:
        result = await crawler.arun(page_url)
        await backoff_if_high_cpu()
    except Exception as e:
        error_msg = f"[scrape_page_markdown] Error scraping page {page_num}: {e}"
        all_errors.append(error_msg)
        return []

    if result is None:
        warning_msg = f"[scrape_page_markdown] No result returned for page {page_num}"
        all_errors.append(warning_msg)
        return []

    if result.markdown:
        return [result.markdown]
    else:
        warning_msg = f"[scrape_page_markdown] No markdown found on page {page_num}"
        all_errors.append(warning_msg)
        return []

async def scrape_job_listing_page(base_url, location_search, crawler, page_pool, page_num, job_count, all_errors, day_range_limit):
    markdown = await scrape_page_markdown(base_url, crawler, page_num, all_errors)
    if not markdown:
        return {'job_count': job_count, 'all_errors': all_errors, 'terminated_early': False, 'invalid_jobs': []}

    job_urls = process_markdown_to_job_links(markdown)
    if not job_urls:
        error_msg = f"No job links found on page {page_num}"
        all_errors.append(error_msg)
        return {'job_count': job_count, 'all_errors': all_errors, 'terminated_early': False, 'invalid_jobs': []}

    page_job_data, terminated_early, job_errors = await process_all_jobs_concurrently(job_urls, crawler, page_pool, location_search, day_range_limit)
    all_errors.extend(job_errors)

    invalid_jobs = []
    if page_job_data:
        job_count, invalid_jobs, validation_errors = await validate_and_insert_jobs(page_job_data, page_num, job_count)
        all_errors.extend(validation_errors)
    
    await pause_briefly(0.05, 0.25)
    await backoff_if_high_cpu()

    return {
        'job_count': job_count, 
        'all_errors': all_errors, 
        'terminated_early': terminated_early,
        'invalid_jobs': invalid_jobs  
    }

async def scrape_job_listing(base_url, location_search, pagesize=TOTAL_JOBS_PER_PAGE, max_pages=None, day_range_limit=DAY_RANGE_LIMIT):
    all_errors = []

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
                markdown = await scrape_page_markdown(base_url, crawler, 1, all_errors)
                if not markdown:
                    return await return_and_report({
                        'message': 'No job search markdown found. Scraped 0 jobs.',
                        'errors': all_errors if all_errors else None,
                        'invalid_jobs': [],
                        'terminated_early': False
                    })

                total_jobs = extract_total_job_count(markdown[0])
                if total_jobs == 0:
                    return await return_and_report({
                        'message': 'No jobs found. Scraped 0 jobs.',
                        'errors': all_errors if all_errors else None,
                        'invalid_jobs': [],
                        'terminated_early': False
                    })
                total_pages = math.ceil(total_jobs / pagesize) if total_jobs else 1
                if max_pages is not None:
                    total_pages = min(total_pages, max_pages)
                logging.info(f"Detected {total_jobs} jobs — scraping {total_pages} pages.")

                job_count = 0
                all_invalid_jobs = []
                terminated_early = False
                terminated_page_num = None

                for page_num in range(1, total_pages + 1):
                    result = await scrape_job_listing_page(base_url, location_search, crawler, page_pool, page_num, job_count, all_errors, day_range_limit)
                    job_count = result['job_count']
                    all_errors = result['all_errors']
                    if result['invalid_jobs']:
                        all_invalid_jobs.extend(result['invalid_jobs'])
                    if result['terminated_early']:
                        terminated_early = True
                        terminated_page_num = page_num
                        break
                    await pause_briefly(0.05, 0.25)
                    await backoff_if_high_cpu()
                
                message = f"Scraped and inserted {job_count} jobs."
                if terminated_early:
                    message += f" Early termination triggered on page {terminated_page_num} due to day range limit of {day_range_limit} days."

            finally:
                await page_pool.close_all()
                await browser.close()
                await playwright.stop()

            return await return_and_report({
                'message': message,
                'errors': all_errors if all_errors else None,
                'invalid_jobs': all_invalid_jobs,
                'terminated_early': terminated_early
            })
        
    except Exception as e:
        return await return_and_report({
            'message': f'Unexpected error: {e}',
            'errors': all_errors + [traceback.format_exc()],
            'invalid_jobs': [],
            'terminated_early': False
        })

    






