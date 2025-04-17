# app.py
import asyncio
from flask import Flask, request, jsonify
from crawl import scrape_job, scrape_first_page_only, scrape_job_listing
from utils import process_markdown_to_job_links
from database import init_db, create_tables
from crawl4ai import AsyncWebCrawler

app = Flask(__name__)
init_db(app)
create_tables(app)

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
        print(markdown)

        if not markdown:
            return {'error': 'No markdown scraped'}

        # Extract job links
        job_links = process_markdown_to_job_links(markdown)
        if not job_links:
            return {'error': 'Processing to job links failed'}

        # Scrape each job link
        all_job_markdowns = []
        for link in job_links:
            job_md = await scrape_job(link, crawler)
            print(job_md)
            if job_md:
                all_job_markdowns.append(job_md)
            break

        return {'message': 'Job saved to DB', 'result': job_links}


if __name__ == '__main__':
    app.run(port=5000)
