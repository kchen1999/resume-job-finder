import logging
import copy
from urllib.parse import urlparse
from datetime import datetime
from scraper.groq_utils import extract_missing_work_model_with_groq, extract_missing_experience_level_with_groq
from scraper.utils import flatten_field
from scraper.node_client import send_page_jobs_to_node
from scraper.constants import ALLOWED_EXPERIENCE_LEVEL_VALUES, ALLOWED_WORK_MODEL_VALUES, REQUIRED_FIELDS, URL_FIELDS, LIST_FIELDS

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

async def validate_job(job):
    job_url = job.get("job_url", "Unknown URL")
    was_invalid = False 

    if job.get("work_model") not in ALLOWED_WORK_MODEL_VALUES:
        logging.info(f"{job_url}: 'work_model' invalid, inferring...")
        job_text = "\n".join([
            job.get("description", ""), 
            flatten_field(job.get("responsibilities", "")), 
            flatten_field(job.get("requirements", ""))
        ])
        inferred_work_model = await extract_missing_work_model_with_groq(job_text)
        job["work_model"] = inferred_work_model or "On-site"
        logging.info(f"{job_url}: 'work_model' set to '{job['work_model']}'")
        was_invalid = True

    for field in REQUIRED_FIELDS:
        if field not in job or not job.get(field):
            if field == "posted_date":
                today_str = datetime.today().strftime('%d/%m/%Y')
                logging.warning(f"{job_url}: Missing 'posted_date', defaulting to today -> {today_str}.")
                job["posted_date"] = today_str
                job["posted_within"] = "Today"
            else: 
                logging.warning(f"{job_url}: Missing required field '{field}', defaulting to empty.")
                job[field] = ""
            was_invalid = True

    for url_field in URL_FIELDS:
        url = job.get(url_field)
        if url:
            parsed = urlparse(url)
            if not (parsed.scheme in ('http', 'https') and parsed.netloc):
                logging.error(f"{job_url}: Invalid URL in '{url_field}' -> {url}")
                job[url_field] = ""
                was_invalid = True

    exp = job.get("experience_level")
    if not exp or exp not in ALLOWED_EXPERIENCE_LEVEL_VALUES:
        print(f"[INFO] {job_url}: Invalid or missing experience_level '{exp}', inferring...")
        job_text = "\n".join([
            job.get("description", ""),
            flatten_field(job.get("responsibilities", "")),
            flatten_field(job.get("requirements", ""))
        ])
        inferred_exp = await extract_missing_experience_level_with_groq(job.get("title", ""), job_text)
        job["experience_level"] = inferred_exp or "mid_or_senior"
        logging.info(f"{job_url}: 'experience_level' set to '{job['experience_level']}'")
        was_invalid = True

    for list_field in LIST_FIELDS:
        val = job.get(list_field)
        if val is None:
            job[list_field] = []
            was_invalid = True
        elif not isinstance(val, list):
            logging.warning(f"{job_url}: '{list_field}' should be a list, converting.")
            job[list_field] = [val] if isinstance(val, str) else []
            was_invalid = True

    return job, was_invalid

async def validate_and_insert_jobs(page_job_data, page_num, job_count, all_errors):
    cleaned_jobs = []
    invalid_jobs = []

    for job in page_job_data:
        original_job = copy.deepcopy(job)
        cleaned_job, was_invalid = await validate_job(job)
        cleaned_jobs.append(cleaned_job)
        if was_invalid:
            invalid_jobs.append(original_job)

    if cleaned_jobs:
        logging.debug("Cleaned job data:")
        logging.debug(cleaned_jobs)
        try:
            await send_page_jobs_to_node(cleaned_jobs)
            job_count += len(cleaned_jobs)
            logging.info(f"Inserted {len(cleaned_jobs)} jobs from page {page_num}")
        except Exception as db_error:
            logging.error(f"DB insert error on page {page_num}:", exc_info=True)
            all_errors.append(f"DB insert error on page {page_num}: {str(db_error)}")

    return job_count, invalid_jobs



