# crawl.py
import asyncio
import random
import math
import re
import logging

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
from playwright.async_api import async_playwright
from scraper.utils import process_markdown_to_job_links, extract_job_data, enrich_job_data, is_within_last_n_days, extract_job_url_and_quick_apply_url, get_posted_date, validate_and_insert_jobs, POSTED_TIME_SPAN_CLASS

DAY_RANGE_LIMIT = 1

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
semaphore = asyncio.Semaphore(4)
# Function to add a delay between requests to mimic human behavior
async def delay_request(page_num):
    if page_num % 10 == 0:
        delay = random.uniform(3, 5)
        print(f"Waiting for {delay:.2f} seconds...")
        await asyncio.sleep(delay)
    else:
        delay = random.uniform(1, 2.5)
        print(f"Waiting for {delay:.2f} seconds...")
        await asyncio.sleep(delay)

# Extract total job count from markdown using regex
def extract_total_job_count(markdown: str) -> int | None:
    match = re.search(r'^#\s*([\d,]+)\s+.*?jobs', markdown, re.MULTILINE | re.IGNORECASE)
    if match:
        number_str = match.group(1).replace(',', '') 
        return int(number_str)
    return None

async def create_browser_context():
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(
        viewport={"width": 1280, "height": 720},
        locale="en-US",
        timezone_id="Australia/Sydney",
    )
    await context.set_extra_http_headers({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    })
    return playwright, browser, context

async def scrape_logo_src(page):
    logging.debug("Starting scrape_logo_src function.")
    await asyncio.sleep(random.uniform(2, 4))
    logging.debug("Trying to find logo image..")

    logo_element = await page.query_selector('img._3txkbm0')
    if logo_element:
        logo_src = await logo_element.get_attribute('src')
        logging.debug(f"Logo found with src: {logo_src}")
        return logo_src
    else:
        logging.warning("Logo element not found.")
        return ""

async def extract_multiple_texts_by_automation(page, automation_ids):
    results = {}
    logging.debug(f"Extracting texts for automation IDs: {automation_ids}")
    for key, automation_id in automation_ids.items():
        try:
            elem = await page.query_selector(f'[data-automation="{automation_id}"]')
            if elem:
                text = (await elem.inner_text()).strip()
                results[key] = text
                logging.debug(f"Extracted {key}: {text}")
            else:
                results[key] = ""
                logging.warning(f"Element not found for automation ID: {automation_id}")
        except Exception as e:
            logging.error(f"Error extracting {automation_id}: {e}")
            results[key] = ""
        if random.random() < 0.8:  
            pause_duration = random.uniform(0.2, 0.6)  
            logging.debug(f"Pausing for {pause_duration:.2f} seconds.")
            await asyncio.sleep(pause_duration)
    return results

async def extract_posted_date_by_class(page, class_name: str) -> str:
    if random.random() < 0.8:  
            pause_duration = random.uniform(0.2, 0.6)  
            logging.debug(f"Pausing for {pause_duration:.2f} seconds.")
            await asyncio.sleep(pause_duration)
    try:
        selector = f'span.{class_name.replace(" ", ".")}'
        elements = await page.query_selector_all(selector)
        for elem in elements:
            text = (await elem.inner_text()).strip()
            logging.debug(f"Found element text: {text}")
            # Extract the number and unit (e.g., 2d, 13h, 45m)
            match = re.search(r'Posted (\d+)([dhm]) ago', text)
            if match:
                value, unit = int(match.group(1)), match.group(2)
                days_ago = value if unit == 'd' else 0
                posted_date = get_posted_date(days_ago)
                logging.debug(f"Extracted posted date: {posted_date}")
                return posted_date
    
        logging.warning("No matching 'Posted X ago' text found.")
        return ""
    except Exception as e:
        logging.error(f"Error extracting posted date: {e}")
        return ""

async def scrape_job_details(url, automation_ids):
    logging.debug(f"Scraping job details for URL: {url}")
    playwright, browser, context = await create_browser_context()
    page = await context.new_page()
    try:
        await page.goto(url)
        logging.debug(f"Page loaded: {url}")
        
        logo_src = await scrape_logo_src(page)
        logging.debug(f"Logo src: {logo_src}")
        
        texts = await extract_multiple_texts_by_automation(page, automation_ids)
        logging.debug(f"Extracted texts: {texts}")

        posted_time = await extract_posted_date_by_class(page, POSTED_TIME_SPAN_CLASS)
        
    except Exception as e:
        logging.error(f"Error during scraping job details: {e}")
        return {"error": f"Failed to scrape job details: {e}"}

    finally:
        try:
            if browser:  
                await browser.close()
            if playwright:
                await playwright.stop()
        except Exception as close_error:
            logging.error(f"Error during browser close: {close_error}")
    
    logging.debug("Finished scraping job details.")
    return {
        "logo_src": logo_src,
        "posted_time": posted_time,
        **texts
    }

#Function to scrape first page of job listings only
async def scrape_first_page_only(base_url, crawler):
    page_url = f"{base_url}&page=1"
    await delay_request(1)
    result = await crawler.arun(page_url)

    if result.markdown:
        print("Successfully scraped page 1")
        return result.markdown
    else:
        print("No markdown found on page 1")
        return []
    
#Function to scrape first page of job listings only
async def scrape_page_markdown(base_url, crawler, page):
    page_url = f"{base_url}&page={page}"
    await delay_request(1)
    result = await crawler.arun(page_url)

    if result.markdown:
        print(f"Successfully scraped page {page}")
        return [result.markdown]
    else:
        print("No markdown found on page 1")
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
        automation_ids = {
            "location": "job-detail-location",
            "classification": "job-detail-classifications",
            "work_type": "job-detail-work-type",
            "salary": "job-detail-salary",
            "title": "job-detail-title",
            "company": "advertiser-name"
        }
        page_url = f"{job_url}"
        await delay_request(1)
        result = await crawler.arun(page_url, config=config)
        job_data = await scrape_job_details(page_url, automation_ids)

        if result.markdown:
            logging.debug("Successfully scraped job markdown.")
            return [result.markdown.fit_markdown, job_data]
        else:
            logging.warning(f"Skipping job URL {job_url}, no markdown extracted.")
            return []
        
async def process_job_with_backoff(job_link, count, crawler, location_search, terminate_event, max_retries=3):
    delay = 1
    for attempt in range(max_retries):
        try:
            print("Scraping job:", count + 1)
            print("Scraping:", job_link)
            job_md, job_data = await scrape_individual_job_url(job_link, crawler)

            if not job_data.get("title"):
                print(f"Skipping job {job_link}, title missing.")
                return None

            job_json = await extract_job_data(job_md, count)
            if not job_json:
                print(f"Skipping job {job_link}, no JSON extracted.")
                return None

            job_url, quick_apply_url = extract_job_url_and_quick_apply_url(job_link)
            enrich_job_data(job_json, location_search, job_url, quick_apply_url, job_data)
            print("Enriched Job JSON: ", job_json)

            if not is_within_last_n_days(job_json, DAY_RANGE_LIMIT):
                print(f"Skipping job {job_link}, posted too old.")
                terminate_event.set()
                return "TERMINATE_EARLY"

            return job_json

        except Exception as e:
            print(f"[Attempt {attempt+1}] Error scraping {job_link}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
                delay *= 2
            else:
                return f"{job_link} failed after {max_retries} retries: {str(e)}"
            
async def bounded_process_job(job_link, count, crawler, location_search, terminate_event):
    if terminate_event.is_set():
        return None
    
    async with semaphore:
        await asyncio.sleep(random.uniform(0.5, 1.5))  # human-like delay
        return await process_job_with_backoff(job_link, count, crawler, location_search, terminate_event)
    
async def process_all_jobs(job_urls, crawler, location_search):
    terminate_event = asyncio.Event()

    tasks = [
        bounded_process_job(job_link, idx, crawler, location_search, terminate_event)
        for idx, job_link in enumerate(job_urls)
    ]
    results = await asyncio.gather(*tasks)

    final_jobs = []
    early_termination = False
    for r in results:
        if r == "TERMINATE_EARLY":
            print("Terminating early due to outdated job.")
            early_termination = True
            break
        elif isinstance(r, dict):
            final_jobs.append(r)
        elif isinstance(r, str):
            print("Error:", r)

    return final_jobs, early_termination

async def scrape_job_listing(base_url, location_search, pagesize=22):
    async with AsyncWebCrawler() as crawler:
        print("AsyncWebCrawler initialized successfully!")
        markdown = await scrape_first_page_only(base_url, crawler)

        if not markdown:
            return {'error': 'No markdown scraped'}

        total_jobs = extract_total_job_count(markdown)
        total_pages = math.ceil(total_jobs / pagesize) if total_jobs else 1
        print(f"Detected {total_jobs or '?'} jobs — scraping {total_pages} pages.")

        job_total_count = 0
        all_errors = []

        #for page in range(1, 2):
        for page in range(1, total_pages + 1):
            markdown = await scrape_page_markdown(base_url, crawler, page)
            if not markdown:
                return {'error': 'No markdown scraped'}
            job_urls = process_markdown_to_job_links(markdown)
            if not job_urls:
                print(f"No job links found on page {page}")
                continue
            page_job_data, terminated_early = await process_all_jobs(job_urls, crawler, location_search)
            if page_job_data:
                job_total_count = await validate_and_insert_jobs(
                    page_job_data, page, job_total_count, all_errors
                )
            
            if terminated_early:
                print(f"Inserted {job_total_count} jobs before early termination.")
                print(f"Early termination triggered on page {page}. Stopping scraping.")
                break

        return {
            'message': f"Scraped and inserted {job_total_count} jobs.",
            'errors': all_errors if all_errors else None
        }





