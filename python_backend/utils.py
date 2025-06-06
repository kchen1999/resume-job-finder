#utils.py
import re
import json
import asyncio
import random
import logging
import psutil
import math

from json_repair import repair_json
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from constants import LOGO_SELECTOR, BROWSER_USER_AGENT

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

async def create_browser_context():
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--single-process",
            "--no-zygote"
        ],
    )
    context = await browser.new_context(
        viewport={"width": 1280, "height": 720},
        locale="en-US",
        timezone_id="Australia/Sydney",
        user_agent=BROWSER_USER_AGENT["User-Agent"],
        java_script_enabled=False
    )
    await context.add_init_script(
        """() => {
            Object.defineProperty(navigator, 'webdriver', {get: () => false});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        }"""
    )

    await context.route("**/*", lambda route, request: asyncio.create_task(
        route.abort() if request.resource_type in ["image", "font", "stylesheet"] else route.continue_()
    ))

    return playwright, browser, context

async def backoff_if_high_cpu(soft_limit=70, hard_limit=90):
    try:
        cpu = psutil.cpu_percent(interval=0.1)  
        if cpu >= hard_limit:
            logging.warning(f"CPU usage at {cpu}%. Hard backoff...")
            await pause_briefly(1.0, 3.0)
        elif cpu >= soft_limit:
            logging.warning(f"CPU usage at {cpu}%. Soft backoff...")
            await pause_briefly(0.25, 0.75)
    except Exception as e:
        logging.warning(f"Failed to measure CPU usage: {e}")

async def pause_briefly(min_delay: float = 0.2, max_delay: float = 0.6):
    delay = random.uniform(min_delay, max_delay)
    logging.debug(f"Pausing for {delay:.2f} seconds...")
    await asyncio.sleep(delay)

def get_posted_date(posted_days_ago: int) -> str:
    posted_date = datetime.today() - timedelta(days=posted_days_ago)
    return posted_date.strftime("%d/%m/%Y") 

async def extract_logo_src(page):
    await pause_briefly()
    logo_element = await page.query_selector(LOGO_SELECTOR)
    await backoff_if_high_cpu()
    if logo_element:
        logo_src = await logo_element.get_attribute('src')
        logging.debug(f"Logo found with src: {logo_src}")
        return logo_src
    else:
        logging.warning("Logo element not found.")
        return ""

async def extract_job_metadata_fields(page, job_metadata_fields):
    results = {}
    field_errors = {}

    for key, job_metadata_field in job_metadata_fields.items():
        await backoff_if_high_cpu()
        try:
            elem = await page.query_selector(f'[data-automation="{job_metadata_field}"]')
            if elem:
                text = (await elem.inner_text()).strip()
                results[key] = text
                logging.debug(f"Extracted {key}: {text}")
            else:
                results[key] = ""
                logging.warning(f"Element not found for job field: {key}")
                field_errors[key] = "Element not found"
        except Exception as e:
            logging.error(f"Error extracting {key}: {e}")
            results[key] = ""
            field_errors[key] = str(e)

        await pause_briefly()

    return results

async def extract_posted_date_by_class(page, class_name: str) -> str:
    if random.random() < 0.8:  
        await pause_briefly()
    try:
        selector = f'span.{class_name.replace(" ", ".")}'
        elements = await page.query_selector_all(selector)

        if not elements:
            logging.warning("No elements found for posted date selector.")
            return {"posted_date": None, "error": "__NO_ELEMENTS__"}

        for elem in elements:
            await backoff_if_high_cpu()
            text = (await elem.inner_text()).strip()
            logging.debug(f"Found element text: {text}")

            match = re.search(r'Posted (\d+)([dhm]) ago', text)
            if match:
                value, unit = int(match.group(1)), match.group(2)
                days_ago = value if unit == 'd' else 0
                posted_date = get_posted_date(days_ago)
                logging.debug(f"Extracted posted date: {posted_date}")
                return {"posted_date": posted_date, "error": None}
        
        return {"posted_date": None, "error": "__NO_MATCHING_TEXT__"}
    
    except Exception as e:
        raise 

def get_total_job_count(markdown: str) -> int:
    match = re.search(r'#\s*([\d,]+)\s+.*?\bjob[s]?\b', markdown, re.MULTILINE | re.IGNORECASE)
    if match:
        number_str = match.group(1).replace(',', '') 
        return int(number_str)
    return 0


def parse_json_block_from_text(response):
    try:
        start = response.find('{')
        end = response.rfind('}') + 1
        return json.loads(response[start:end])
    except Exception as e:
        print("Error parsing JSON:", e)
        print(f"Raw response: {repr(response)}")
        return response
    
def clean_repair_parse_json(json_block):
    try:
        if isinstance(json_block, str):
            json_block = clean_string(json_block)
            print("Cleaned json: ")
            print(json_block)
        repaired_json_string = repair_json(json_block)
        print("repairing json...")
        job_data = json.loads(repaired_json_string)
        print("repaired json: ")
        print(job_data)
        return job_data
    except Exception as e:
        raise e

def extract_job_links(markdown):
    job_links = re.findall(r"https://www\.seek\.com\.au/job/\d+\?[^)\s]*origin=cardTitle", markdown)
    return job_links 


def get_job_urls(job_link):
    job_url = re.search(r"https:\/\/www\.seek\.com\.au\/job\/\d+", job_link).group()
    quick_apply_url = job_url + "/apply"
    return [job_url, quick_apply_url]


def process_markdown_to_job_links(markdown):
    try:
        job_links = extract_job_links(markdown)
        if not job_links:
            print("No job links extracted from page markdowm")
            return None
        
        for link in job_links:
            print("Scraping:", link)
        return job_links
            
    except Exception as e:
        print("Processing error:", e)
        return None
    
def clean_string(raw_string):
    cleaned = raw_string.replace('\\', '').replace('\n', '')
    return cleaned

def set_default_work_model(job_data):
    if job_data.get("work_model") is None:
        job_data["work_model"] = "On-site"
    return job_data

def normalize_experience_level(job_data: dict) -> dict:
    level = job_data.get("experience_level", "").lower()
    if level in {"mid", "senior"}:
        job_data["experience_level"] = "mid_or_senior"
    return job_data

def infer_experience_level_from_title(title: str) -> str:
    title = title.lower()
    if any(term in title for term in ["intern", "internship"]):
        return "intern"
    if any(term in title for term in ["junior", "graduate", "entry"]):
        return "junior"
    if any(term in title for term in ["lead", "manager", "principal", "head", "director", "vp", "chief"]):
        return "lead+"
    return ""

def override_experience_level_with_title(job_data: dict):
    title = job_data.get("title", "")
    if isinstance(title, str) and title.strip():
        inferred = infer_experience_level_from_title(title)
        if inferred:
            job_data["experience_level"] = inferred
    return job_data

def get_total_pages(total_jobs, pagesize, max_pages):
    total_pages = math.ceil(total_jobs / pagesize)
    if max_pages is not None:
        total_pages = min(total_pages, max_pages)
    return total_pages


def is_recent_job(job_data, within_days=7):
    try:
        posted_date_str = job_data.get("posted_date", "")
        posted_date = datetime.strptime(posted_date_str, "%d/%m/%Y").date()
        today = datetime.today().date()
        return (today - posted_date).days <= within_days
    except Exception as e:
        print("Date parsing error:", e)
        return None  

def get_relative_posted_time(job_data):
    posted_date_str = job_data.get("posted_date")
    if not posted_date_str:
        return None

    try: 
        posted_date = datetime.strptime(posted_date_str, '%d/%m/%Y').date()
        today = datetime.today().date()
        delta = (today - posted_date).days
    except Exception as e:
        print("Date parsing error:", e)
        return None

    if delta == 0:
        return 'Today'
    elif delta == 1:
        return 'Yesterday'
    elif 2 <= delta <= 14:
        return f'{delta} days ago'
    
def enrich_job_data(job_data, location_search, job_url, quick_apply_url, job_metadata):
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
    job_data = normalize_experience_level(job_data)
    return job_data

def flatten_field(field):
    if isinstance(field, list):
        return " ".join(str(item) for item in field)
    return str(field)






