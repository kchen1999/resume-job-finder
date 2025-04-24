# crawl.py
import asyncio
import random
import math
import re
from crawl4ai import AsyncWebCrawler

# Function to add a delay between requests to mimic human behavior
async def delay_request(page_num):
    if page_num % 10 == 0:
        delay = random.uniform(3, 5)
        print(f"Waiting for {delay:.2f} seconds...")
        await asyncio.sleep(delay)
    else:
        delay = random.uniform(1, 3)
        print(f"Waiting for {delay:.2f} seconds...")
        await asyncio.sleep(delay)

# Extract total job count from markdown using regex
def extract_total_job_count(markdown: str) -> int | None:
    match = re.search(r'^#\s*([\d,]+)\s+.*?jobs', markdown, re.MULTILINE | re.IGNORECASE)
    if match:
        number_str = match.group(1).replace(',', '') 
        return int(number_str)
    return None

def extract_logo_link(html):
    match = re.search(r'<img[^>]*src="([^"]+)"[^>]*class="[^"]*\b_3txkbm0\b[^"]*"', html)
    if match:
        return match.group(1)
    return ""

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
        page_url = f"{job_url}"
        await delay_request(1)
        result = await crawler.arun(page_url)
        logo_link = extract_logo_link(result.html)

        if result.markdown:
            print("Successfully scraped job url")
            return [result.markdown, logo_link]
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


