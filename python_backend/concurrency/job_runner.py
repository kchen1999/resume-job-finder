
from utils.constants import SUCCESS, TERMINATE
from utils.utils import pause_briefly, backoff_if_high_cpu
from jobs.enricher import enrich_job
from jobs.extractor import extract_job_data

async def process_job_with_retries(job_url, count, crawler, page_pool, location_search, terminate_event, day_range_limit):

    await backoff_if_high_cpu()
    job_extraction = await extract_job_data(job_url, crawler, page_pool, count, terminate_event, day_range_limit)
    await pause_briefly(0.05, 0.25)

    if job_extraction["status"] != SUCCESS:
        return job_extraction 
        
    job_data = enrich_job(job_extraction["job"], job_url, location_search, job_extraction["job_metadata"])
    await pause_briefly(0.05, 0.25)
    return {"status": SUCCESS, "job": job_data}

async def process_job_with_semaphore(job_url, count, crawler, page_pool, location_search, terminate_event, day_range_limit, semaphore):
    if terminate_event.is_set():
        return {"status": TERMINATE, "job": None}

    async with semaphore: 
        await backoff_if_high_cpu()  
        await pause_briefly(0.05, 0.25) 
        return await process_job_with_retries(
            job_url, count, crawler, page_pool, location_search, terminate_event, day_range_limit
        )
