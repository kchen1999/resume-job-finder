# crawl.py
import asyncio
import math
import logging

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
from playwright.async_api import async_playwright
from scraper.utils import process_markdown_to_job_links, parse_job_json_from_markdown, enrich_job_json, is_job_within_date_range, pause_briefly, override_experience_level_with_title
from scraper.utils import extract_job_urls, extract_total_job_count, extract_logo_src, extract_posted_date_by_class, extract_job_metadata_fields, set_default_work_model, normalize_experience_level
from scraper.validate_and_insert_db import validate_and_insert_jobs
from scraper.constants import DAY_RANGE_LIMIT, TOTAL_JOBS_PER_PAGE, MAX_RETRIES, SUCCESS, TERMINATE, SKIPPED, ERROR, CONCURRENT_JOBS_NUM, POSTED_TIME_SELECTOR, JOB_METADATA_FIELDS, BROWSER_USER_AGENT

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

        posted_result = await extract_posted_date_by_class(page, POSTED_TIME_SELECTOR)
        posted_time = posted_result.get("posted_time")
        posted_time_error = posted_result.get("error")
        
    except Exception as e:
        logging.error(f"Error during scraping job metadata: {e}")
        raise

    finally:
        try:
            if browser:  
                await browser.close()
            if playwright:
                await playwright.stop()
        except Exception as close_error:
            logging.error(f"Error during browser close: {close_error}")
            raise
    
    logging.debug("Finished scraping job metadata.")
    return {
        "logo_src": logo_src,
        "posted_time": posted_time,
        "posted_time_error": posted_time_error,
        **job_metadata
    }
     
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

        try:
            result = await crawler.arun(page_url, config=config)
        except Exception as e:
            logging.error(f"Error extracting markdown: {e}")
            return None, {"error": f"Markdown extraction error: {str(e)}"}

        if result is None or not result.markdown:
            logging.warning(f"Skipping job URL {job_url}, no markdown extracted.")
            return None, {"error": "No markdown extracted"}

        try:
            job_metadata = await scrape_job_metadata(page_url, JOB_METADATA_FIELDS)
            if job_metadata is None:
                return result.markdown.fit_markdown, {"error": "Metadata scraping returned None"}
        except Exception as e:
            logging.error(f"Error scraping metadata: {e}")
            return result.markdown.fit_markdown, {"error": str(e)}

        logging.debug("Successfully scraped job markdown and metadata.")
        return result.markdown.fit_markdown, job_metadata
        
async def process_job_with_backoff(job_link, count, crawler, location_search, terminate_event, day_range_limit, max_retries=MAX_RETRIES):
    delay = 1
    for attempt in range(max_retries):
        try:
            print("Scraping job:", count + 1)
            print("Scraping:", job_link)
            job_markdown, job_metadata = await scrape_individual_job_url(job_link, crawler)

            if job_metadata.get("error"):
                print(f"Skipping job {job_link}, error scraping metadata: {job_metadata['error']}")
                return {"status": SKIPPED, "job": None, "error": job_metadata["error"]}
           
            if job_metadata.get("posted_time_error") in {"__NO_ELEMENTS__", "__NO_MATCHING_TEXT__"}:
                if job_metadata["posted_time_error"] == "__NO_ELEMENTS__":
                    error_message = "'posted_date' selector broke (most likely)"
                else: 
                    error_message = "no matching 'Posted X ago' text found"

                print(f"Skipping job {job_link}, posted date issue: {error_message}")
                return {
                    "status": SKIPPED,
                    "job": None,
                    "error": f"Posted date selector issue: {error_message}"
                }

            job_json = await parse_job_json_from_markdown(job_markdown, count)
            if not job_json:
                print(f"Skipping job {job_link}, no JSON extracted.")
                return {"status": SKIPPED, "job": None, "error": "No JSON extracted"}
            
            job_json = set_default_work_model(job_json)
            job_url, quick_apply_url = extract_job_urls(job_link)
            enrich_job_json(job_json, location_search, job_url, quick_apply_url, job_metadata)
            print("Enriched Job JSON: ", job_json)

            if not is_job_within_date_range(job_json, day_range_limit):
                print(f"Skipping job {job_link}, posted too old.")
                terminate_event.set()
                return {"status": TERMINATE, "job": None, "error": None}

            job_json = override_experience_level_with_title(job_json)
            job_json = normalize_experience_level(job_json)
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
            
async def bounded_process_job(job_link, count, crawler, location_search, terminate_event, day_range_limit):
    if terminate_event.is_set():
        return {"status": "terminate", "job": None, "error": None}
    
    async with semaphore:
        await pause_briefly(0.5, 1.5) 
        return await process_job_with_backoff(job_link, count, crawler, location_search, terminate_event, day_range_limit)
    
async def process_all_jobs_concurrently(job_urls, crawler, location_search, day_range_limit):
    terminate_event = asyncio.Event()
    tasks = [
        bounded_process_job(job_link, idx, crawler, location_search, terminate_event, day_range_limit)
        for idx, job_link in enumerate(job_urls)
    ]
    job_results = await asyncio.gather(*tasks)
    
    final_jobs = []
    all_errors = []
    early_termination = False

    for job_result in job_results:
        if job_result["status"] == TERMINATE:
            print("Terminating early due to outdated job.")
            early_termination = True
        elif job_result["status"] == SUCCESS:
            final_jobs.append(job_result["job"])
        elif job_result["status"] == SKIPPED:
            print("Skipped:", job_result["error"])
            all_errors.append(job_result["error"])
        elif job_result["status"] == ERROR:
            print("Error:", job_result["error"])
            all_errors.append(job_result["error"])

    return final_jobs, early_termination, all_errors

async def scrape_job_listing_page(base_url, location_search, crawler, page_num, job_count, all_errors, day_range_limit):
    markdown = await scrape_page_markdown(base_url, crawler, page_num)
    if not markdown:
        error_msg = f"No markdown scraped on page {page_num}"
        all_errors.append(error_msg)
        print(error_msg)
        return {'job_count': job_count, 'all_errors': all_errors, 'terminated_early': False, 'invalid_jobs': []}

    job_urls = process_markdown_to_job_links(markdown)
    if not job_urls:
        error_msg = f"No job links found on page {page_num}"
        all_errors.append(error_msg)
        print(error_msg)
        return {'job_count': job_count, 'all_errors': all_errors, 'terminated_early': False, 'invalid_jobs': []}

    page_job_data, terminated_early, job_errors = await process_all_jobs_concurrently(job_urls, crawler, location_search, day_range_limit)
    all_errors.extend(job_errors)

    invalid_jobs = []
    if page_job_data:
        job_count, invalid_jobs, validation_errors = await validate_and_insert_jobs(page_job_data, page_num, job_count)
        all_errors.extend(validation_errors)

    return {
        'job_count': job_count, 
        'all_errors': all_errors, 
        'terminated_early': terminated_early,
        'invalid_jobs': invalid_jobs  
    }

async def scrape_job_listing(base_url, location_search, pagesize=TOTAL_JOBS_PER_PAGE, max_pages=None, day_range_limit=DAY_RANGE_LIMIT):
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
                'invalid_jobs': [],
                'terminated_early': False
            }
        total_pages = math.ceil(total_jobs / pagesize) if total_jobs else 1
        if max_pages is not None:
            total_pages = min(total_pages, max_pages)
        print(f"Detected {total_jobs} jobs — scraping {total_pages} pages.")

        job_count = 0
        all_errors = []
        all_invalid_jobs = []
        terminated_early = False

        for page_num in range(1, total_pages + 1):
            result = await scrape_job_listing_page(base_url, location_search, crawler, page_num, job_count, all_errors, day_range_limit)
            job_count = result['job_count']
            all_errors = result['all_errors']
            if result['invalid_jobs']:
                all_invalid_jobs.extend(result['invalid_jobs'])
            if result['terminated_early']:
                terminated_early = True
                print(f"Early termination triggered on page {page_num}. Stopping scraping.")
                break

        return {
            'message': f"Scraped and inserted {job_count} jobs.",
            'errors': all_errors if all_errors else None,
            'invalid_jobs': all_invalid_jobs,
            'terminated_early': terminated_early
        }
    

    






