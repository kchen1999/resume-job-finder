# app.py
import asyncio
import random
import re
from flask import Flask, request, jsonify
from crawl import scrape_individual_job_url, scrape_first_page_only, scrape_job_listing
from utils import process_markdown_to_job_links, extract_job_data, truncate_logo_url
from crawl4ai import AsyncWebCrawler

app = Flask(__name__)

@app.route('/scrape', methods=['POST'])
def scrape():
    try:
        print("Received POST request to /scrape")
        data = request.get_json()

        job_title = data.get('job_title', 'software engineer')
        location = data.get('location', 'sydney')

        base_url = f"https://www.seek.com.au/jobs?keywords={job_title}&where={location}"

        # Create a fresh event loop for this request
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        markdown_results = loop.run_until_complete(scrape_job_listing(base_url))
        loop.close()

        # Convert scraped markdown to JSON using the utility function
        json_results = []
        for markdown in markdown_results:
            json_data = process_markdown_to_json(markdown)
            if json_data:
                json_results.append(json_data)

        return jsonify({'results': json_results})

    except Exception as e:
        print("Scraping failed:", e)
        return jsonify({'error': 'Scraping failed', 'details': str(e)}), 500
    
@app.route('/test-db', methods=['POST'])
def test_db():
    try:
        data = request.get_json()
        job_title = data.get('job_title', 'software engineer')
        location = data.get('location', 'sydney')
        base_url = f"https://www.seek.com.au/jobs?keywords={job_title}&where={location}"

        result = asyncio.run(scrape_and_process(base_url))
        return jsonify(result), 200

    except Exception as e:
        print("Test DB error:", e)
        return jsonify({'error': str(e)}), 500


async def scrape_and_process(base_url):
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
        # Scrape each job link
        count = 0
        for job_link in job_urls:
            if count == 8: 
                break
            delay = random.uniform(1, 3)
            print(f"Waiting for {delay:.2f} seconds...")
            await asyncio.sleep(delay)
            print("Scraping:", job_link)
            #Scrape individual job markdown from job url
            job_md = await scrape_individual_job_url(job_link, crawler)
            #Extract JSON from each individual job markdown
            job_url = re.search(r"https:\/\/www\.seek\.com\.au\/job\/\d+", job_link).group()
            quick_apply_url = job_url + "/apply"
            job_json = await extract_job_data(job_md, job_url, quick_apply_url)
            if not job_json:
                return {'error': 'Unable to extract JSON fields from job link'}
            if "logo_link" in job_json:
                job_json["logo_link"] = truncate_logo_url(job_json["logo_link"])
            print(job_json)
            job_data_list.append(job_json)
            count += 1
            
        return {'message': 'Job saved to DB', 'result': job_data_list}


if __name__ == '__main__':
    app.run(port=5000)
