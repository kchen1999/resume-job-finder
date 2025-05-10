import logging
import httpx
from urllib.parse import urlparse
from scraper.groq_utils import extract_missing_work_model_with_groq, extract_missing_experience_level_with_groq
from scraper.utils import flatten_field

REQUIRED_FIELDS = ["title", "company", "classification", "posted_date", "posted_within", "work_type", "work_model"]
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

async def send_page_jobs_to_node(job_data_list):
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
            response = await client.post(
                "http://localhost:3000/api/jobs/page-batch",  
                json={"jobs": job_data_list}
            )
            response.raise_for_status()
            logging.info("Successfully sent jobs to Node")
    except httpx.HTTPStatusError as exc:
        logging.error(f"Failed to insert jobs: {exc.response.status_code} - {exc.response.text}")
        raise

async def validate_job(job):
    job_url = job.get("job_url", "Unknown URL")

    if not job.get("work_model"):
        logging.info(f"{job_url}: 'work_model' missing, inferring...")
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
        
    for url_field in ["quick_apply_url", "job_url"]:
        url = job.get(url_field)
        if url:
            parsed = urlparse(url)
            if not (parsed.scheme in ('http', 'https') and parsed.netloc):
                logging.error(f"{job_url}: Invalid URL in '{url_field}' -> {url}")
                return False

    exp = job.get("experience_level")
    if not exp or exp not in ["intern", "junior", "mid", "senior", "lead+"]:
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

    for list_field in ["responsibilities", "requirements", "other"]:
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




