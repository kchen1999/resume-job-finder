import logging
from urllib.parse import urlparse
from scraper.groq_utils import extract_missing_work_model_with_groq, extract_missing_experience_level_with_groq
from scraper.utils import flatten_field
from scraper.node_client import send_page_jobs_to_node

REQUIRED_FIELDS = ["title", "company", "classification", "posted_date", "posted_within", "work_type", "work_model"]
ALLOWED_WORK_MODEL_VALUES = {"Remote", "Hybrid", "On-site"}
ALLOWED_EXPERIENCE_LEVEL_VALUES = ["intern", "junior", "mid_or_senior", "lead+"]
URL_FIELDS = ["quick_apply_url", "job_url"]
LIST_FIELDS = ["responsibilities", "requirements", "other"]
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

async def validate_job(job):
    job_url = job.get("job_url", "Unknown URL")

    if job.get("work_model") not in ALLOWED_WORK_MODEL_VALUES:
        logging.info(f"{job_url}: 'work_model' invalid, inferring...")
        job_text = "\n".join([
            job.get("description", ""), 
            flatten_field(job.get("responsibilities", "")), 
            flatten_field(job.get("requirements", ""))
        ])
        inferred_work_model = await extract_missing_work_model_with_groq(job_text)
        if inferred_work_model:
            job["work_model"] = inferred_work_model
            logging.info(f"{job_url}: 'work_model' inferred as '{inferred_work_model}'")
        else:
            logging.warning(f"{job_url}: Unable to infer 'work_model', defaulting to 'On-site'.")
            job["work_model"] = "On-site"  

    for field in REQUIRED_FIELDS:
        if not job.get(field):
            logging.error(f"{job_url}: Missing required field '{field}'")
            return False
        
    for url_field in URL_FIELDS:
        url = job.get(url_field)
        if url:
            parsed = urlparse(url)
            if not (parsed.scheme in ('http', 'https') and parsed.netloc):
                logging.error(f"{job_url}: Invalid URL in '{url_field}' -> {url}")
                return False

    exp = job.get("experience_level")
    if not exp or exp not in ALLOWED_EXPERIENCE_LEVEL_VALUES:
        print(f"[INFO] {job_url}: Invalid or missing experience_level '{exp}', inferring...")
        job_text = "\n".join([
            job.get("description", ""),
            flatten_field(job.get("responsibilities", "")),
            flatten_field(job.get("requirements", ""))
        ])
        inferred_exp = await extract_missing_experience_level_with_groq(job.get("title", ""), job_text)
        if inferred_exp:
            job["experience_level"] = inferred_exp
            logging.info(f"{job_url}: Inferred experience_level as '{inferred_exp}'")
        else:
            logging.error(f"{job_url}: Unable to infer valid experience_level.")
            return False

    for list_field in LIST_FIELDS:
        val = job.get(list_field)
        if val is not None and not isinstance(val, list):
            logging.error(f"{job_url}: '{list_field}' should be a list, got {type(val).__name__}")
            return False

    return True

async def validate_and_insert_jobs(page_job_data, page_num, job_count, all_errors):
    valid_jobs = []
    invalid_jobs = []

    for job in page_job_data:
        is_valid = await validate_job(job)
        if is_valid:
            valid_jobs.append(job)
        else:
            invalid_jobs.append(job)

    if invalid_jobs:
        logging.warning(f"Skipping {len(invalid_jobs)} invalid jobs from page {page_num}.")

    if valid_jobs:
        logging.debug("Valid job data:")
        logging.debug(valid_jobs)
        try:
            await send_page_jobs_to_node(valid_jobs)
            job_count += len(valid_jobs)
            logging.info(f"Inserted {len(valid_jobs)} jobs from page {page_num}")
        except Exception as db_error:
            logging.error(f"DB insert error on page {page_num}:", exc_info=True)
            all_errors.append(f"DB insert error on page {page_num}: {str(db_error)}")

    return job_count, invalid_jobs




