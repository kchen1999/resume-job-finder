import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

from clients.node_client import send_page_jobs_to_node

async def insert_jobs_into_database(cleaned_jobs, page_num, job_count):
    if not cleaned_jobs:
        return job_count

    logging.debug(f"Cleaned job data: {cleaned_jobs}")

    try:
        await send_page_jobs_to_node(cleaned_jobs)
        job_count += len(cleaned_jobs)
        logging.info(f"Inserted {len(cleaned_jobs)} jobs from page {page_num}")
    except Exception as db_error:
        logging.error(f"Failed to insert jobs for page {page_num}: {db_error}")

    return job_count
