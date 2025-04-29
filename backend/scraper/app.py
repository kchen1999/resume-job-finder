# app.py
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from flask import jsonify
from scraper.crawl import scrape_all_jobs, scrape_job_listing

app = FastAPI()

@app.post('/scrape')
async def scrape(request: Request):
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
    
@app.post("/jobs")
async def get_jobs(request: Request):
    try:
        data = await request.json()
        job_title = data.get('job_title', 'software engineer')
        location = data.get('location', 'sydney')
        base_url = f"https://www.seek.com.au/jobs?keywords={job_title}&where={location}&sortmode=ListedDate"

        result = await scrape_all_jobs(base_url, location)
        return JSONResponse(content=result, status_code=200)

    except Exception as e:
        print("Scraping all jobs error:", e)
        return JSONResponse(content={'error': str(e)}, status_code=500)
    

