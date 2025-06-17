import logging

logger = logging.getLogger(__name__)

from clients.node_client import send_page_jobs_to_node


async def insert_jobs_into_database(cleaned_jobs, page_num, job_count):
    if not cleaned_jobs:
        return job_count

    logger.debug(f"Cleaned job data: {cleaned_jobs}")

    try:
        await send_page_jobs_to_node(cleaned_jobs)
        job_count += len(cleaned_jobs)
        logger.info(f"Inserted {len(cleaned_jobs)} jobs from page {page_num}")
    except Exception as db_error:
        logger.exception(f"Failed to insert jobs for page {page_num}: {db_error}")

    return job_count
