import asyncio
import logging

logger = logging.getLogger(__name__)

import math
import random
import re
from datetime import datetime, timedelta

import psutil
import sentry_sdk


async def backoff_if_high_cpu(soft_limit=70, hard_limit=90):
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        if cpu >= hard_limit:
            logger.warning(f"CPU usage at {cpu}%. Hard backoff...")
            await pause_briefly(1.0, 3.0)
        elif cpu >= soft_limit:
            logger.warning(f"CPU usage at {cpu}%. Soft backoff...")
            await pause_briefly(0.25, 0.75)
    except Exception as e:
        logger.exception(f"Failed to measure CPU usage: {e}")
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "backoff_if_high_cpu")
            scope.set_extra("soft_limit", soft_limit)
            scope.set_extra("hard_limit", hard_limit)
            sentry_sdk.capture_exception(e)

async def pause_briefly(min_delay: float = 0.2, max_delay: float = 0.6):
    delay = random.uniform(min_delay, max_delay)
    logger.debug(f"Pausing for {delay:.2f} seconds...")
    await asyncio.sleep(delay)

def get_posted_date(posted_days_ago):
    posted_date = datetime.today() - timedelta(days=posted_days_ago)
    return posted_date.strftime("%d/%m/%Y")

def get_total_job_count(markdown):
    match = re.search(r"#\s*([\d,]+)\s+.*?\bjob[s]?\b", markdown, re.MULTILINE | re.IGNORECASE)
    if match:
        number_str = match.group(1).replace(",", "")
        return int(number_str)
    return 0

def extract_job_urls(markdown):
    job_urls = re.findall(r"https://www\.seek\.com\.au/job/\d+\?[^)\s]*origin=cardTitle", markdown)
    return job_urls

def get_job_urls(job_url):
    job_url = re.search(r"https:\/\/www\.seek\.com\.au\/job\/\d+", job_url).group()
    quick_apply_url = job_url + "/apply"
    return [job_url, quick_apply_url]

def clean_string(raw_string):
    cleaned = raw_string.replace("\\", "").replace("\n", "")
    return cleaned

def get_total_pages(total_jobs, pagesize, max_pages):
    total_pages = math.ceil(total_jobs / pagesize)
    if max_pages is not None:
        total_pages = min(total_pages, max_pages)
    return total_pages

def is_recent_job(job_metadata, within_days=7):
    try:
        posted_date_str = job_metadata.get("posted_date", "")
        if posted_date_str is None:
            return False
        posted_date = datetime.strptime(posted_date_str, "%d/%m/%Y").date()
        today = datetime.today().date()
        return (today - posted_date).days <= within_days
    except Exception as e:
        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "is_recent_job")
            scope.set_extra("posted_date_str", job_metadata.get("posted_date"))
            scope.set_extra("job_metadata", job_metadata)
            sentry_sdk.capture_exception(e)
        return False

def flatten_field(field):
    if isinstance(field, list):
        return " ".join(str(item) for item in field)
    return str(field)






