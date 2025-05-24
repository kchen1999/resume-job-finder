import logging
import copy
from urllib.parse import urlparse
from datetime import datetime
from llm_job_parser import infer_experience_level, infer_work_model
from utils import flatten_field
from node_client import send_page_jobs_to_node
from constants import ALLOWED_EXPERIENCE_LEVEL_VALUES, ALLOWED_WORK_MODEL_VALUES, REQUIRED_FIELDS, NON_REQUIRED_FIELDS, URL_FIELDS, LIST_FIELDS, FALLBACK_EXPERIENCE_LEVEL, FALLBACK_WORK_MODEL, FALLBACK_POSTED_WITHIN

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

async def validate_job(job):
    job_url = job.get("job_url", "Unknown URL")
    was_invalid = False 
    invalid_fields = set()

    # 1. Validate work_model
    if job.get("work_model") not in ALLOWED_WORK_MODEL_VALUES:
        logging.info(f"{job_url}: 'work_model' invalid, inferring...")
        job_text = "\n".join([
            job.get("description", ""), 
            flatten_field(job.get("responsibilities", "")), 
            flatten_field(job.get("requirements", ""))
        ])
        inferred_work_model = await infer_work_model(job_text)
        job["work_model"] = inferred_work_model or FALLBACK_WORK_MODEL
        logging.info(f"{job_url}: 'work_model' set to '{job['work_model']}'")
        was_invalid = True
        invalid_fields.add("work_model")

    # 2. Check required fields presence
    for field in REQUIRED_FIELDS:
        if not job.get(field):
            if field == "posted_date":
                today_str = datetime.today().strftime('%d/%m/%Y')
                logging.warning(f"{job_url}: Missing 'posted_date', defaulting to today -> {today_str}.")
                job["posted_date"] = today_str
                job["posted_within"] = FALLBACK_POSTED_WITHIN
            else:
                logging.warning(f"{job_url}: Missing required field '{field}', defaulting to empty.")
                job[field] = ""
            was_invalid = True
            invalid_fields.add(field)

    # 3. Validate URL fields
    for url_field in URL_FIELDS:
        url = job.get(url_field)
        if url:
            parsed = urlparse(url)
            if not (parsed.scheme in ('http', 'https') and parsed.netloc):
                logging.error(f"{job_url}: Invalid URL in '{url_field}' -> {url}")
                job[url_field] = ""
                was_invalid = True
                invalid_fields.add(url_field)

    # 4. Validate experience_level
    exp = job.get("experience_level")
    if not exp or exp not in ALLOWED_EXPERIENCE_LEVEL_VALUES:
        print(f"[INFO] {job_url}: Invalid or missing experience_level '{exp}', inferring...")
        job_text = "\n".join([
            job.get("description", ""),
            flatten_field(job.get("responsibilities", "")),
            flatten_field(job.get("requirements", ""))
        ])
        inferred_exp = await infer_experience_level(job.get("title", ""), job_text)
        job["experience_level"] = inferred_exp or FALLBACK_EXPERIENCE_LEVEL
        logging.info(f"{job_url}: 'experience_level' set to '{job['experience_level']}'")
        was_invalid = True
        invalid_fields.add("experience_level")

    # 5. Validate that all string fields are actually strings
    for field in REQUIRED_FIELDS + NON_REQUIRED_FIELDS:
        val = job.get(field)
        if val is not None and not isinstance(val, str):
            logging.warning(f"{job_url}: '{field}' should be a string, converting.")
            try:
                if isinstance(val, list):
                    job[field] = ", ".join(map(str, val))
                else:
                    job[field] = str(val)
            except Exception:
                job[field] = ""
            was_invalid = True
            invalid_fields.add(field)

    # 6. Validate list fields
    for list_field in LIST_FIELDS:
        val = job.get(list_field)
        if val is None:
            job[list_field] = []
            was_invalid = True
            invalid_fields.add(list_field)
        elif not isinstance(val, list):
            logging.warning(f"{job_url}: '{list_field}' should be a list, converting.")
            job[list_field] = [val] if isinstance(val, str) else []
            was_invalid = True
            invalid_fields.add(list_field)

    return job, was_invalid, invalid_fields

async def validate_and_insert_jobs(page_job_data, page_num, job_count):
    cleaned_jobs = []
    invalid_jobs = []
    all_errors = []

    for job in page_job_data:
        original_job = copy.deepcopy(job)
        cleaned_job, was_invalid, invalid_fields = await validate_job(job)
        cleaned_jobs.append(cleaned_job)
        if was_invalid:
            original_job["invalid_fields"] = list(invalid_fields)
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

    return job_count, invalid_jobs, all_errors



