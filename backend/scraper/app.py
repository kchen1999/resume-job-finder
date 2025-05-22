from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from scraper.job_scrape import scrape_job_listing
from scraper.constants import DAY_RANGE_LIMIT

app = FastAPI()

# Manual scraping (immediate, returns result)
@app.post("/jobs")
async def get_jobs(request: Request):
    try:
        data = await request.json()
        job_title = data.get('job_title', 'software engineer')
        location = data.get('location', 'sydney')
        base_url = f"https://www.seek.com.au/jobs?keywords={job_title}&where={location}&sortmode=ListedDate"

        result = await scrape_job_listing(base_url, location)
        return JSONResponse(content=result, status_code=200)

    except Exception as e:
        print("Scraping all jobs error:", e)
        return JSONResponse(content={'error': str(e)}, status_code=500)

# Background scraping trigger
@app.post("/start-scraping")
async def start_scraping(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await request.json()
        job_title = data.get('job_title', 'software engineer')
        location = data.get('location', 'sydney')
        max_pages = data.get('max_pages')
        day_range_limit = data.get('day_range_limit')
        base_url = f"https://www.seek.com.au/jobs?keywords={job_title}&where={location}&sortmode=ListedDate"

        background_tasks.add_task(
            scrape_job_listing, 
            base_url, 
            location, 
            max_pages=int(max_pages) if max_pages is not None else None,
            day_range_limit=int(day_range_limit) if day_range_limit is not None else DAY_RANGE_LIMIT
        )

        return JSONResponse(content={"status": "Scraping started"}, status_code=202)

    except Exception as e:
        print("Error triggering scraping:", e)
        return JSONResponse(content={'error': str(e)}, status_code=500)

    

