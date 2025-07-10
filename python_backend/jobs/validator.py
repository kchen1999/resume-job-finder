from datetime import datetime
from urllib.parse import urlparse

import sentry_sdk
from llm.parser import infer_experience_level, infer_work_model
from tzlocal import get_localzone
from utils.constants import (
    ALLOWED_EXPERIENCE_LEVEL_VALUES,
    ALLOWED_WORK_MODEL_VALUES,
    FALLBACK_EXPERIENCE_LEVEL,
    FALLBACK_POSTED_WITHIN,
    FALLBACK_WORK_MODEL,
    LIST_FIELDS,
    NON_REQUIRED_FIELDS,
    REQUIRED_FIELDS,
    URL_FIELDS,
)
from utils.utils import flatten_field


async def validate_work_model(job: dict, job_url: str) -> None:
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


def apply_required_field_fallbacks(job: dict, job_url: str) -> None:
    for field in REQUIRED_FIELDS:
        if not job.get(field):
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "validate_job")
                scope.set_extra("job_url", job_url)
                scope.set_extra("field", field)
                scope.capture_message(f"Missing required field '{field}', applying fallback", level="warning")

            if field == "posted_date":
                local_tz = get_localzone()
                job["posted_date"] = datetime.now(local_tz).strftime("%d/%m/%Y")
                job["posted_within"] = FALLBACK_POSTED_WITHIN
            else:
                job[field] = ""


def validate_url_fields(job: dict, job_url: str) -> None:
    for url_field in URL_FIELDS:
        url = job.get(url_field)
        if url:
            parsed = urlparse(url)
            if not (parsed.scheme in ("http", "https") and parsed.netloc):
                with sentry_sdk.push_scope() as scope:
                    scope.set_tag("component", "validate_job")
                    scope.set_extra("job_url", job_url)
                    scope.set_extra("invalid_url", url)
                    scope.set_extra("field", url_field)
                    scope.capture_message(f"Invalid URL format in '{url_field}'", level="error")
                job[url_field] = ""


async def validate_experience_level(job: dict, job_url: str) -> None:
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


def normalize_string_fields(job: dict, job_url: str) -> None:
    for field in REQUIRED_FIELDS + NON_REQUIRED_FIELDS:
        val = job.get(field)
        if val is not None and not isinstance(val, str):
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "validate_job")
                scope.set_extra("job_url", job_url)
                scope.set_extra("field", field)
                scope.set_extra("original_type", type(val).__name__)
                scope.capture_message(
                    f"Field '{field}' expected string but got {type(val).__name__}, converting",
                    level="warning"
                )
            try:
                job[field] = ", ".join(map(str, val)) if isinstance(val, list) else str(val)
            except Exception as e:
                with sentry_sdk.push_scope() as scope:
                    scope.set_tag("component", "validate_job")
                    scope.set_extra("job_url", job_url)
                    scope.set_extra("field", field)
                    sentry_sdk.capture_exception(e)
                job[field] = ""


def normalize_list_fields(job: dict, job_url: str) -> None:
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
                msg = (
                    f"Field '{list_field}' expected list but got {type(val).__name__}, converting"
                )
                scope.capture_message(msg, level="warning")
            job[list_field] = [val] if isinstance(val, str) else []
        else:
            cleaned_list = []
            for item in val:
                try:
                    cleaned_list.append(str(item))
                except Exception as e:
                    with sentry_sdk.push_scope() as scope:
                        scope.set_tag("component", "validate_job")
                        scope.set_extra("job_url", job_url)
                        scope.set_extra("field", list_field)
                        scope.set_extra("bad_item", repr(item))
                        sentry_sdk.capture_exception(e)
            job[list_field] = cleaned_list

def normalize_salary_field(job: dict) -> None:
    original_salary = job.get("salary", "").strip().lower()

    if original_salary == "add expected salary to your profile for insights":
        job["salary"] = "Salary unspecified"


async def validate_job(job: dict) -> dict:
    job_url = job.get("job_url", "Unknown URL")

    await validate_work_model(job, job_url)
    apply_required_field_fallbacks(job, job_url)
    validate_url_fields(job, job_url)

    await validate_experience_level(job, job_url)
    normalize_string_fields(job, job_url)
    normalize_list_fields(job, job_url)
    normalize_salary_field(job)

    return job

async def validate_jobs(page_job_data: list) -> list:
    cleaned_jobs = []
    for job in page_job_data:
        cleaned_job = await validate_job(job)
        cleaned_jobs.append(cleaned_job)
    return cleaned_jobs
