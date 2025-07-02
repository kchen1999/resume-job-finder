
from jobs.enricher import enrich_job
from jobs.extractor import extract_job_data
from utils.constants import SUCCESS, TERMINATE
from utils.context import ScrapeContext
from utils.utils import backoff_if_high_cpu, pause_briefly


async def process_job_with_retries(job_url: str, count: int, ctx: ScrapeContext) -> dict:

    await backoff_if_high_cpu()
    job_extraction = await extract_job_data(job_url, ctx, count)
    await pause_briefly(0.05, 0.25)

    if job_extraction["status"] != SUCCESS:
        return job_extraction

    job_data = enrich_job(job_extraction["job"], job_url, ctx.location_search, job_extraction["job_metadata"])
    await pause_briefly(0.05, 0.25)
    return {"status": SUCCESS, "job": job_data}

async def process_job_with_semaphore(job_url: str, count: int, ctx: ScrapeContext) -> dict:
    if ctx.terminate_event.is_set():
        return {"status": TERMINATE, "job": None}

    async with ctx.semaphore:
        await backoff_if_high_cpu()
        await pause_briefly(0.05, 0.25)
        return await process_job_with_retries(job_url, count, ctx)
