import asyncio
import logging
import math
import random
import re
from datetime import datetime, timedelta

import psutil
import sentry_sdk
from tzlocal import get_localzone

logger = logging.getLogger(__name__)

async def backoff_if_high_cpu(soft_limit: int = 70, hard_limit: int = 90) -> None:
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        if cpu >= hard_limit:
            logger.warning("CPU usage at %s%%. Hard backoff...", cpu)
            await pause_briefly(1.0, 3.0)
        elif cpu >= soft_limit:
            logger.warning("CPU usage at %s%%. Soft backoff...", cpu)
            await pause_briefly(0.25, 0.75)
    except Exception as e:
        logger.exception("Failed to measure CPU usage")
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "backoff_if_high_cpu")
            scope.set_extra("soft_limit", soft_limit)
            scope.set_extra("hard_limit", hard_limit)
            sentry_sdk.capture_exception(e)

async def pause_briefly(min_delay: float = 0.2, max_delay: float = 0.6) -> None:
    delay = random.uniform(min_delay, max_delay)
    logger.debug("Pausing for %.2f seconds...", delay)
    await asyncio.sleep(delay)

def get_posted_date(posted_days_ago: int) -> str:
    local_tz = get_localzone()
    posted_date = datetime.now(local_tz) - timedelta(days=posted_days_ago)
    return posted_date.strftime("%d/%m/%Y")

def get_total_job_count(markdown: str) -> int:
    match = re.search(r"#\s*([\d,]+)\s+.*?\bjob[s]?\b", markdown, re.MULTILINE | re.IGNORECASE)
    if match:
        number_str = match.group(1).replace(",", "")
        return int(number_str)
    return 0

def extract_job_urls(markdown: str) -> list:
    return re.findall(r"https://www\.seek\.com\.au/job/\d+\?[^)\s]*origin=cardTitle", markdown)

def get_job_urls(job_url: str) -> list:
    job_url = re.search(r"https:\/\/www\.seek\.com\.au\/job\/\d+", job_url).group()
    quick_apply_url = job_url + "/apply"
    return [job_url, quick_apply_url]

def clean_string(raw_string: str) -> str:
    return raw_string.replace("\\", "").replace("\n", "")

def get_total_pages(total_jobs: int, pagesize: int, max_pages: int | None) -> int:
    total_pages = math.ceil(total_jobs / pagesize)
    if max_pages is not None:
        total_pages = min(total_pages, max_pages)
    return total_pages

def is_recent_job(job_metadata: dict, within_days: int = 7) -> bool:
    try:
        posted_date_str = job_metadata.get("posted_date", "")
        if posted_date_str is None:
            return False
        local_tz = get_localzone()
        posted_date = datetime.strptime(posted_date_str, "%d/%m/%Y").replace(tzinfo=local_tz)

        today = datetime.now(local_tz)

        return (today.date() - posted_date.date()).days <= within_days
    except Exception as e:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "is_recent_job")
            scope.set_extra("posted_date_str", job_metadata.get("posted_date"))
            scope.set_extra("job_metadata", job_metadata)
            sentry_sdk.capture_exception(e)
        return False

def flatten_field(field: str | list) -> str:
    if isinstance(field, list):
        return " ".join(str(item) for item in field)
    return str(field)

def normalize_keys(d: dict) -> dict:
    def to_snake_case(key: str) -> str:
        key = key.strip().strip('({[<"\')').strip(')}]>"\'')
        key = re.sub(r"[\s\-]+", "_", key)
        return key.lower()

    normalized_dict = {}
    for k, v in d.items():
        new_key = to_snake_case(k)
        normalized_dict[new_key] = v

    return normalized_dict

def try_fix_missing_closing_brace(response: str) -> str:
    open_count = response.count("{")
    close_count = response.count("}")
    if open_count > close_count:
        return response + "}"
    return response






