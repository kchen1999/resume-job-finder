# crawl.py
import asyncio
import random
import math
import re
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
from playwright.async_api import async_playwright
from utils import process_markdown_to_job_links, extract_job_data, truncate_logo_url, enrich_job_data, is_within_last_n_days, get_posted_within, extract_job_url_and_quick_apply_url

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

#def extract_logo_link(html):
 #   match = re.search(r'<img[^>]*src="([^"]+)"[^>]*class="[^"]*\b_3txkbm0\b[^"]*"', html)
  #  if match:
   #     return match.group(1)
    #return ""

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
    await asyncio.sleep(random.uniform(1.5, 2.5))
    await page.wait_for_load_state('networkidle')

    logo_element = await page.query_selector('img._3txkbm0')
    if logo_element:
        return await logo_element.get_attribute('src')
    else:
        return ""

async def extract_multiple_texts_by_automation(page, automation_ids):
    results = {}
    for key, automation_id in automation_ids.items():
        try:
            elem = await page.query_selector(f'[data-automation="{automation_id}"]')
            if elem:
                text = (await elem.inner_text()).strip()
                results[key] = text
            else:
                results[key] = ""
        except Exception as e:
            print(f"Error extracting {automation_id}: {e}")
            results[key] = ""
    return results

async def scrape_job_details(url, automation_ids):
    playwright, browser, context = await create_browser_context()
    page = await context.new_page()
    await page.goto(url)

    logo_src = await scrape_logo_src(page)
    texts = await extract_multiple_texts_by_automation(page, automation_ids)

    await browser.close()
    await playwright.stop()

    return {
        "logo_src": logo_src,
        **texts
    }

#Function to scrape first page of job listings only
async def scrape_first_page_only(base_url, crawler):
    page_url = f"{base_url}&page=1"
    await delay_request(1)
    result = await crawler.arun(page_url)

    if result.markdown:
        print("Successfully scraped page 1")
        return [result.markdown]
    else:
        print("No markdown found on page 1")
        return []
        
async def scrape_individual_job_url(job_url, crawler): 
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
        }
        page_url = f"{job_url}"
        await delay_request(1)
        result = await crawler.arun(page_url, config=config)
        job_data = await scrape_job_details(page_url, automation_ids)

        if result.markdown:
            print("Successfully scraped job url")
            return [result.markdown.fit_markdown, job_data]
        else:
            print("No markdown found in job url")
            return []

# Function to scrape job listings
async def scrape_job_listing(base_url, pagesize=22):
    all_results = []

    async with AsyncWebCrawler() as crawler:
        # First page to get total job count
        first_page_url = f"{base_url}&page=1"
        await delay_request(1)
        first_result = await crawler.arun(first_page_url)

        if not first_result.markdown:
            print("No markdown on page 1")
            return []

        all_results.append(first_result.markdown)

        # Extract total job count and calculate pages
        total_jobs = extract_total_job_count(first_result.markdown)
        if not total_jobs:
            print("Couldn't extract total job count, scraping just the first page.")
            return all_results

        total_pages = math.ceil(total_jobs / pagesize)
        print(f"Detected {total_jobs} jobs — scraping {total_pages} pages total.")

        # Now scrape the remaining pages
        for page in range(2, total_pages + 1):
            page_url = f"{base_url}&page={page}"
            await delay_request(page)
            result = await crawler.arun(page_url)

            if result.markdown:
                all_results.append(result.markdown)
                print(f"Scraped page {page}")
            else:
                print(f"Skipping page {page}, no markdown found.")

    return all_results


async def scrape_all_jobs(base_url, location_search):
    # First scrape job listing page
    async with AsyncWebCrawler() as crawler:
        print("AsyncWebCrawler initialized successfully!")
        markdown = await scrape_first_page_only(base_url, crawler)

        if not markdown:
            return {'error': 'No markdown scraped'}

        # Extract job links
        job_urls = process_markdown_to_job_links(markdown)
        if not job_urls:
            return {'error': 'Processing to job urls failed'}

        job_data_list = []
        count = 0

        for job_link in job_urls:
            print("Scraping job:", count + 1)
            if count == 1:
                break
            print("Scraping:", job_link)
            job_md, job_data = await scrape_individual_job_url(job_link, crawler)
            print("logo url: ", job_data["logo_src"])
            print("location: ", job_data["location"])
            print("classification: ", job_data["classification"])
            print("work type: ", job_data["work_type"])
            job_json = await extract_job_data(job_md)
            if not job_json:
                print(f"Skipping job {job_link}, no JSON extracted.")
                continue
                
            if not is_within_last_n_days(job_json, 14):
                print(f"Skipping job {job_link}, posted too old.")
                break

            job_url, quick_apply_url = extract_job_url_and_quick_apply_url(job_link)

            if "logo_link" in job_json:
                job_json["logo_link"] = truncate_logo_url(job_json["logo_link"])
                    
            posted_within = get_posted_within(job_json)
            #enrich_job_data(job_json, location_search, job_url, quick_apply_url, logo_link, posted_within)
                
            print("Enriched Job JSON: ", job_json)
            job_data_list.append(job_json)
            count += 1
       
    return {'message': 'Job saved to DB', 'result': job_data_list}


