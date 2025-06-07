import logging
from urllib.parse import urlparse
from datetime import datetime
import sentry_sdk
from llm_job_parser import infer_experience_level, infer_work_model
from utils import flatten_field
from node_client import send_page_jobs_to_node
from constants import ALLOWED_EXPERIENCE_LEVEL_VALUES, ALLOWED_WORK_MODEL_VALUES, REQUIRED_FIELDS, NON_REQUIRED_FIELDS, URL_FIELDS, LIST_FIELDS, FALLBACK_EXPERIENCE_LEVEL, FALLBACK_WORK_MODEL, FALLBACK_POSTED_WITHIN

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

async def validate_job(job):
    job_url = job.get("job_url", "Unknown URL")

    # 1. Validate work_model
    if job.get("work_model") not in ALLOWED_WORK_MODEL_VALUES:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "validate_job")
            scope.set_extra("job_url", job_url)
            scope.set_extra("field", "work_model")
            scope.capture_message("Invalid or missing 'work_model', attempting inference", level="warning")

        job_text = "\n".join([
            job.get("description", ""),
            flatten_field(job.get("responsibilities", "")),
            flatten_field(job.get("requirements", ""))
        ])
        inferred_work_model = await infer_work_model(job_text)
        job["work_model"] = inferred_work_model or FALLBACK_WORK_MODEL

    # 2. Check required fields presence
    for field in REQUIRED_FIELDS:
        if not job.get(field):
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "validate_job")
                scope.set_extra("job_url", job_url)
                scope.set_extra("field", field)
                scope.capture_message(f"Missing required field '{field}', applying fallback", level="warning")

            if field == "posted_date":
                job["posted_date"] = datetime.today().strftime('%d/%m/%Y')
                job["posted_within"] = FALLBACK_POSTED_WITHIN
            else:
                job[field] = ""

    # 3. Validate URL fields
    for url_field in URL_FIELDS:
        url = job.get(url_field)
        if url:
            parsed = urlparse(url)
            if not (parsed.scheme in ('http', 'https') and parsed.netloc):
                with sentry_sdk.push_scope() as scope:
                    scope.set_tag("component", "validate_job")
                    scope.set_extra("job_url", job_url)
                    scope.set_extra("invalid_url", url)
                    scope.set_extra("field", url_field)
                    scope.capture_message(f"Invalid URL format in '{url_field}'", level="error")
                job[url_field] = ""

    # 4. Validate experience_level
    exp = job.get("experience_level")
    if not exp or exp not in ALLOWED_EXPERIENCE_LEVEL_VALUES:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "validate_job")
            scope.set_extra("job_url", job_url)
            scope.set_extra("field", "experience_level")
            scope.capture_message(f"Invalid or missing 'experience_level': {exp}", level="warning")

        job_text = "\n".join([
            job.get("description", ""),
            flatten_field(job.get("responsibilities", "")),
            flatten_field(job.get("requirements", ""))
        ])
        inferred_exp = await infer_experience_level(job.get("title", ""), job_text)
        job["experience_level"] = inferred_exp or FALLBACK_EXPERIENCE_LEVEL

    # 5. Validate all string fields
    for field in REQUIRED_FIELDS + NON_REQUIRED_FIELDS:
        val = job.get(field)
        if val is not None and not isinstance(val, str):
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "validate_job")
                scope.set_extra("job_url", job_url)
                scope.set_extra("field", field)
                scope.set_extra("original_type", type(val).__name__)
                scope.capture_message(f"Field '{field}' expected string but got {type(val).__name__}, converting", level="warning")
            try:
                job[field] = ", ".join(map(str, val)) if isinstance(val, list) else str(val)
            except Exception as e:
                with sentry_sdk.push_scope() as scope:
                    scope.set_tag("component", "validate_job")
                    scope.set_extra("job_url", job_url)
                    scope.set_extra("field", field)
                    sentry_sdk.capture_exception(e)
                job[field] = ""

    # 6. Validate list fields
    for list_field in LIST_FIELDS:
        val = job.get(list_field)
        if val is None:
            job[list_field] = []
        elif not isinstance(val, list):
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "validate_job")
                scope.set_extra("job_url", job_url)
                scope.set_extra("field", list_field)
                scope.set_extra("original_type", type(val).__name__)
                scope.capture_message(f"Field '{list_field}' expected list but got {type(val).__name__}, converting", level="warning")
            job[list_field] = [val] if isinstance(val, str) else []

    return job

async def validate_jobs(page_job_data):
    cleaned_jobs = []
    for job in page_job_data:
        cleaned_job = await validate_job(job)
        cleaned_jobs.append(cleaned_job)
    return cleaned_jobs


async def insert_jobs_into_database(cleaned_jobs, page_num, job_count):
    if not cleaned_jobs:
        return job_count

    logging.debug(f"Cleaned job data: {cleaned_jobs}")

    try:
        await send_page_jobs_to_node(cleaned_jobs)
        job_count += len(cleaned_jobs)
        logging.info(f"Inserted {len(cleaned_jobs)} jobs from page {page_num}")
    except Exception as db_error:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "insert_jobs_into_database")
            scope.set_extra("page_num", page_num)
            scope.capture_exception(db_error)

    return job_count



