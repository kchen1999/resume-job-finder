import asyncio
import random
import math
import re
import nest_asyncio

from flask import Flask, request, jsonify
from crawl4ai import AsyncWebCrawler

nest_asyncio.apply()
app = Flask(__name__)

# Function to add a delay between requests to mimic human behavior
async def delay_request(page_num):
    if page_num % 10 == 0:
        delay = random.uniform(3, 5)
        print(f"Waiting for {delay:.2f} seconds...")
        await asyncio.sleep(delay)  # mimic taking a sip of coffee
    else:
        delay = random.uniform(1, 3)
        print(f"Waiting for {delay:.2f} seconds...")
        await asyncio.sleep(random.uniform(1, 3))

# Extract total job count from markdown using regex
def extract_total_job_count(markdown: str) -> int | None:
    match = re.search(r'^#\s*([\d,]+)\s+.*?jobs', markdown, re.MULTILINE | re.IGNORECASE)
    if match:
        number_str = match.group(1).replace(',', '')  # remove comma
        return int(number_str)
    return None

@app.route('/scrape', methods=['POST'])
def scrape():
    try:
        print("Received POST request to /scrape")
        data = request.get_json()

        job_title = data.get('job_title', 'software engineer')
        location = data.get('location', 'sydney')

        base_url = f"https://www.seek.com.au/jobs?keywords={job_title}&where={location}"

        async def scrape_job():
            all_results = []
            pagesize = 22  # Seek default

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

        # Create a fresh event loop for this request
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(scrape_job())
        loop.close()

        return jsonify({'results': results})

    except Exception as e:
        print("Scraping failed:", e)
        return jsonify({'error': 'Scraping failed', 'details': str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000)
