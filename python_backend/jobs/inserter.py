import logging

from clients.node_client import send_page_jobs_to_node

logger = logging.getLogger(__name__)

async def insert_jobs_into_database(cleaned_jobs: dict, page_num: int, job_count: int) -> int:
    if not cleaned_jobs:
        return job_count

    logger.debug("Cleaned job data: %s", cleaned_jobs)

    try:
        await send_page_jobs_to_node(cleaned_jobs)
        job_count += len(cleaned_jobs)
        logger.info("Inserted %s jobs from page %s", len(cleaned_jobs), page_num)
    except Exception:
        logger.exception("Failed to insert jobs for page %s", page_num)

    return job_count
