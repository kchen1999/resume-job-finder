# crawl.py
import asyncio
import math
import logging

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
from playwright.async_api import async_playwright
from scraper.utils import process_markdown_to_job_links, parse_job_json_from_markdown, enrich_job_json, is_job_within_date_range, pause_briefly
from scraper.utils import extract_job_urls, extract_total_job_count, extract_logo_src, extract_posted_date_by_class, extract_job_metadata_fields
from scraper.validate_and_db_insert import validate_and_insert_jobs

DAY_RANGE_LIMIT = 0
TOTAL_JOBS_PER_PAGE = 22
MAX_RETRIES = 3
TERMINATE_EARLY = "TERMINATE EARLY"
SUCCESS = "success"
TERMINATE = "terminate" 
SKIPPED = "skipped"
ERROR = "error"
CONCURRENT_JOBS_NUM = 4
POSTED_TIME_SELECTOR = "gg45di0 _1ubeeig4z _1oxsqkd0 _1oxsqkd1 _1oxsqkd22 _18ybopc4 _1oxsqkd7"
JOB_METADATA_FIELDS = {
    "location": "job-detail-location",
    "classification": "job-detail-classifications",
    "work_type": "job-detail-work-type",
    "salary": "job-detail-salary",
    "title": "job-detail-title",
    "company": "advertiser-name"
}
BROWSER_USER_AGENT = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36" 
}

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
semaphore = asyncio.Semaphore(CONCURRENT_JOBS_NUM)

async def create_browser_context():
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        viewport={"width": 1280, "height": 720},
        locale="en-US",
        timezone_id="Australia/Sydney",
    )
    await context.set_extra_http_headers(BROWSER_USER_AGENT)
    return playwright, browser, context

async def scrape_job_metadata(url, job_metadata_fields):
    logging.debug(f"Scraping job metadata for URL: {url}")
    playwright, browser, context = await create_browser_context()
    page = await context.new_page()
    try:
        await page.goto(url)
        logging.debug(f"Page loaded: {url}")

        logo_src = await extract_logo_src(page)
        logging.debug(f"Logo src: {logo_src}")
        
        job_metadata = await extract_job_metadata_fields(page, job_metadata_fields)
        logging.debug(f"Extracted metadata fields: {job_metadata}")  

        posted_time = await extract_posted_date_by_class(page, POSTED_TIME_SELECTOR)
        
    except Exception as e:
        logging.error(f"Error during scraping job metadata: {e}")
        return {"error": f"Failed to scrape job metadata: {e}"}

    finally:
        try:
            if browser:  
                await browser.close()
            if playwright:
                await playwright.stop()
        except Exception as close_error:
            logging.error(f"Error during browser close: {close_error}")
    
    logging.debug("Finished scraping job metadat.")
    return {
        "logo_src": logo_src,
        "posted_time": posted_time,
        **job_metadata
    }

async def scrape_page_markdown(base_url, crawler, page_num):
    page_url = f"{base_url}&page={page_num}"
    await pause_briefly(1, 3)
    result = await crawler.arun(page_url)
    if result is None: 
        print(f"No markdown found on page {page_num}")
        return []
    if result.markdown:
        print(f"Successfully scraped page {page_num}")
        return [result.markdown]
    else:
        print(f"No markdown found on page {page_num}")
        return []
        
async def scrape_individual_job_url(job_url, crawler): 
        logging.debug(f"Starting to scrape job URL: {job_url}")

        prune_filter = PruningContentFilter(
            threshold=0.5,
            threshold_type="fixed",
        )
        md_generator = DefaultMarkdownGenerator(
            content_filter=prune_filter,
            options={"ignore_links": True}
        )
        config = CrawlerRunConfig(
            markdown_generator=md_generator  
        )
        
        page_url = f"{job_url}"
        await pause_briefly(1, 3)
        result = await crawler.arun(page_url, config=config)
        if result is None: 
            logging.warning(f"Skipping job URL {job_url}, no markdown extracted.")
            return []
        job_metadata = await scrape_job_metadata(page_url, JOB_METADATA_FIELDS)

        if result.markdown:
            logging.debug("Successfully scraped job markdown.")
            return [result.markdown.fit_markdown, job_metadata]
        else:
            logging.warning(f"Skipping job URL {job_url}, no markdown extracted.")
            return []
        
async def process_job_with_backoff(job_link, count, crawler, location_search, terminate_event, max_retries=MAX_RETRIES):
    delay = 1
    for attempt in range(max_retries):
        try:
            print("Scraping job:", count + 1)
            print("Scraping:", job_link)
            job_markdown, job_metadata = await scrape_individual_job_url(job_link, crawler)
            if not isinstance(job_metadata, dict) or not job_metadata.get("title"):
                print(f"Skipping job {job_link}, title missing.")
                return {"status": SKIPPED, "job": None, "error": "Missing title"}

            job_json = await parse_job_json_from_markdown(job_markdown, count)
            if not job_json:
                print(f"Skipping job {job_link}, no JSON extracted.")
                return {"status": SKIPPED, "job": None, "error": "No JSON extracted"}

            job_url, quick_apply_url = extract_job_urls(job_link)
            enrich_job_json(job_json, location_search, job_url, quick_apply_url, job_metadata)
            print("Enriched Job JSON: ", job_json)

            if not is_job_within_date_range(job_json, DAY_RANGE_LIMIT):
                print(f"Skipping job {job_link}, posted too old.")
                terminate_event.set()
                return {"status": TERMINATE, "job": None, "error": None}

            return {"status": SUCCESS, "job": job_json, "error": None}

        except Exception as e:
            print(f"[Attempt {attempt+1}] Error scraping {job_link}: {e}")
            if attempt < max_retries - 1:
                await pause_briefly(delay, delay)
                delay *= 2
            else:
                print(f"{job_link} failed after {max_retries} retries: {str(e)}")
                return {
                    "status": "error",
                    "job": None,
                    "error": f"{job_link} failed after {max_retries} retries: {str(e)}"
                }
            
async def bounded_process_job(job_link, count, crawler, location_search, terminate_event):
    if terminate_event.is_set():
        return {"status": "terminate", "job": None, "error": None}
    
    async with semaphore:
        await pause_briefly(0.5, 1.5) 
        return await process_job_with_backoff(job_link, count, crawler, location_search, terminate_event)
    
async def process_all_jobs_concurrently(job_urls, crawler, location_search):
    terminate_event = asyncio.Event()
    tasks = [
        bounded_process_job(job_link, idx, crawler, location_search, terminate_event)
        for idx, job_link in enumerate(job_urls)
    ]
    job_results = await asyncio.gather(*tasks)
    final_jobs = []
    early_termination = False

    for job_result in job_results:
        if job_result["status"] == TERMINATE:
            print("Terminating early due to outdated job.")
            early_termination = True
        elif job_result["status"] == SUCCESS:
            final_jobs.append(job_result["job"])
        elif job_result["status"] == SKIPPED:
            print("Skipped:", job_result["error"])
        elif job_result["status"] == ERROR:
            print("Error:", job_result["error"])

    return final_jobs, early_termination

async def scrape_job_listing_page(base_url, location_search, crawler, page_num, job_count, all_errors):
    markdown = await scrape_page_markdown(base_url, crawler, page_num)
    if not markdown:
        print(f"No markdown scraped on page {page_num}")
        return {'job_count': job_count, 'all_errors': all_errors, 'terminated_early': True, 'invalid_jobs': []}

    job_urls = process_markdown_to_job_links(markdown)
    if not job_urls:
        print(f"No job links found on page {page_num}")
        return {'job_count': job_count, 'all_errors': all_errors, 'terminated_early': True, 'invalid_jobs': []}

    page_job_data, terminated_early = await process_all_jobs_concurrently(job_urls, crawler, location_search)
    if page_job_data:
        job_count, invalid_jobs = await validate_and_insert_jobs(page_job_data, page_num, job_count, all_errors)

    return {
        'job_count': job_count, 
        'all_errors': all_errors, 
        'terminated_early': terminated_early,
        'invalid_jobs': invalid_jobs  
    }


async def scrape_job_listing(base_url, location_search, pagesize=TOTAL_JOBS_PER_PAGE):
    async with AsyncWebCrawler() as crawler:
        print("AsyncWebCrawler initialized successfully!")
        markdown = await scrape_page_markdown(base_url, crawler, 1)
        if not markdown:
            return {'error': 'No markdown scraped'}

        total_jobs = extract_total_job_count(markdown[0])
        if total_jobs == 0:
            print("No jobs found.")
            return {
                'message': 'Scraped and inserted 0 jobs.',
                'errors': None,
                'invalid_jobs': []
            }
        total_pages = math.ceil(total_jobs / pagesize) if total_jobs else 1
        print(f"Detected {total_jobs} jobs — scraping {total_pages} pages.")

        job_count = 0
        all_errors = []
        all_invalid_jobs = []

        #for page_num in range(1, 2):
        for page_num in range(1, total_pages + 1):
            result = await scrape_job_listing_page(base_url, location_search, crawler, page_num, job_count, all_errors)
            job_count = result['job_count']
            all_errors = result['all_errors']
            if result['invalid_jobs']:
                all_invalid_jobs.extend(result['invalid_jobs'])
            if result['terminated_early']:
                print(f"Inserted {job_count} jobs before early termination.")
                print(f"Early termination triggered on page {page_num}. Stopping scraping.")
                break

        return {
            'message': f"Scraped and inserted {job_count} jobs.",
            'errors': all_errors if all_errors else None,
            'invalid_jobs': all_invalid_jobs
        }
    

    






