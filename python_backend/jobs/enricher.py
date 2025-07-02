from datetime import datetime

import sentry_sdk
from tzlocal import get_localzone
from utils.constants import INTERN_TITLES, JUNIOR_TITLES, LEAD_TITLES
from utils.utils import get_job_urls


def get_relative_posted_time(job_data: dict) -> str | None:
    posted_date_str = job_data.get("posted_date")
    if not posted_date_str:
        return None

    try:
        local_tz = get_localzone()
        posted_date = datetime.strptime(posted_date_str, "%d/%m/%Y").replace(tzinfo=local_tz)
        today = datetime.now(local_tz)
        delta = (today.date() - posted_date.date()).days

        if delta == 0:
            return "Today"
        if delta == 1:
            return "Yesterday"

    except Exception as e:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "get_relative_posted_time")
            scope.set_extra("posted_date_str", posted_date_str)
            scope.set_extra("job_data", job_data)
            sentry_sdk.capture_exception(e)
        return None

    else:
        return f"{delta} days ago" if delta > 1 else None

def set_default_work_model(job_data: dict) -> dict:
    if job_data.get("work_model") is None:
        job_data["work_model"] = "On-site"
    return job_data

def infer_experience_level_from_title(title: str) -> str:
    title = title.lower()
    if any(term in title for term in INTERN_TITLES):
        return "intern"
    if any(term in title for term in JUNIOR_TITLES):
        return "junior"
    if any(term in title for term in LEAD_TITLES):
        return "lead+"
    return ""

def override_experience_level_with_title(job_data: dict) -> dict:
    title = job_data.get("title", "")
    if isinstance(title, str) and title.strip():
        inferred = infer_experience_level_from_title(title)
        if inferred:
            job_data["experience_level"] = inferred
    return job_data

def normalize_experience_level(job_data: dict) -> dict:
    level = job_data.get("experience_level", "").lower()
    if level in {"mid", "senior"}:
        job_data["experience_level"] = "mid_or_senior"
    return job_data

def enrich_job_data(
        job_data: dict,
        location_search: str,
        job_url: str,
        quick_apply_url: str,
        job_metadata: dict
    ) -> dict:
    job_data["job_url"] = job_url
    job_data["quick_apply_url"] = quick_apply_url
    job_data["location_search"] = location_search
    job_data["posted_date"] = job_metadata["posted_date"]
    job_data["posted_within"] = get_relative_posted_time(job_data)
    job_data["logo_link"] = job_metadata["logo_src"]
    job_data["location"] = job_metadata.get("location", "")
    job_data["classification"] = job_metadata.get("classification", "")
    job_data["work_type"] = job_metadata.get("work_type", "")
    job_data["salary"] = job_metadata.get("salary", "")
    job_data["title"] = job_metadata.get("title", "")
    job_data["company"] = job_metadata.get("company", "")
    job_data = set_default_work_model(job_data)
    job_data = override_experience_level_with_title(job_data)
    return normalize_experience_level(job_data)


def enrich_job(job_data: dict, job_url: str, location_search: str, job_metadata: dict) -> dict:
    job_url, quick_apply_url = get_job_urls(job_url)
    return enrich_job_data(job_data, location_search, job_url, quick_apply_url, job_metadata)


