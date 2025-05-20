#utils.py
import re
import json
import asyncio
import random
import logging

from json_repair import repair_json
from datetime import datetime, timedelta
from scraper.groq_utils import extract_fields_from_job_link_with_groq
from scraper.constants import LOGO_SELECTOR

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

async def pause_briefly(min_delay: float = 0.2, max_delay: float = 0.6):
    delay = random.uniform(min_delay, max_delay)
    logging.debug(f"Pausing for {delay:.2f} seconds...")
    await asyncio.sleep(delay)

def get_posted_date(posted_days_ago: int) -> str:
    posted_date = datetime.today() - timedelta(days=posted_days_ago)
    return posted_date.strftime("%d/%m/%Y") 

async def extract_logo_src(page):
    await pause_briefly(2, 4)
    logging.debug("Trying to find logo image..")

    logo_element = await page.query_selector(LOGO_SELECTOR)
    if logo_element:
        logo_src = await logo_element.get_attribute('src')
        logging.debug(f"Logo found with src: {logo_src}")
        return logo_src
    else:
        logging.warning("Logo element not found.")
        return ""

async def extract_job_metadata_fields(page, job_metadata_fields):
    results = {}
    logging.debug(f"Extracting job metadata for fields: {job_metadata_fields}")
    for key, job_metadata_field in job_metadata_fields.items():
        try:
            elem = await page.query_selector(f'[data-automation="{job_metadata_field}"]')
            if elem:
                text = (await elem.inner_text()).strip()
                results[key] = text
                logging.debug(f"Extracted {key}: {text}")
            else:
                results[key] = ""
                logging.warning(f"Element not found for job field: {key}")
        except Exception as e:
            logging.error(f"Error extracting {key}: {e}")
            results[key] = ""
        if random.random() < 0.8:  
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
            return {"posted_time": None, "error": "__NO_ELEMENTS__"}

        for elem in elements:
            text = (await elem.inner_text()).strip()
            logging.debug(f"Found element text: {text}")

            match = re.search(r'Posted (\d+)([dhm]) ago', text)
            if match:
                value, unit = int(match.group(1)), match.group(2)
                days_ago = value if unit == 'd' else 0
                posted_date = get_posted_date(days_ago)
                logging.debug(f"Extracted posted date: {posted_date}")
                return {"posted_time": posted_date, "error": None}
        
        logging.warning("No matching 'Posted X ago' text found.")
        return {"posted_time": None, "error": "__NO_MATCHING_TEXT__"}
    
    except Exception as e:
        logging.error(f"Unexpected error while extracting posted date: {e}")
        raise 

# Extract total job count from markdown using regex
def extract_total_job_count(markdown: str) -> int:
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

def extract_job_links(markdown):
    job_links = re.findall(r"https://www\.seek\.com\.au/job/\d+\?[^)\s]*origin=cardTitle", markdown[0])
    return job_links 


def extract_job_urls(job_link):
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

def set_default_work_model(job_json):
    if job_json.get("work_model") is None:
        job_json["work_model"] = "On-site"
    return job_json

def normalize_experience_level(job_json: dict) -> dict:
    level = job_json.get("experience_level", "").lower()
    if level in {"mid", "senior"}:
        job_json["experience_level"] = "mid_or_senior"
    return job_json

def infer_experience_level_from_title(title: str) -> str:
    title = title.lower()
    if any(term in title for term in ["intern", "internship"]):
        return "intern"
    if any(term in title for term in ["junior", "graduate", "entry"]):
        return "junior"
    if any(term in title for term in ["lead", "manager", "principal", "head", "director", "vp", "chief"]):
        return "lead+"
    return ""

def override_experience_level_with_title(job_json: dict):
    title = job_json.get("title", "")
    if isinstance(title, str) and title.strip():
        inferred = infer_experience_level_from_title(title)
        if inferred:
            job_json["experience_level"] = inferred
    return job_json

async def parse_job_json_from_markdown(job_markdown, count):
    groq_response  = await extract_fields_from_job_link_with_groq(job_markdown, count)
    json_candidate = parse_json_block_from_text(groq_response)
    print(f"Type of raw_result: {type(json_candidate)}")

     # If it's already a dict (parsed JSON), no need to decode
    if isinstance(json_candidate, dict):
        return json_candidate
    
    # Clean the extracted JSON using json_repair (if needed)
    try:
        if isinstance(json_candidate, str):
            json_candidate = clean_string(json_candidate)
            print("Cleaned json: ")
            print(json_candidate)
        repaired_json_string = repair_json(json_candidate)  # Raw string goes here
        print("repairing json...")
        job_json = json.loads(repaired_json_string)
        print("repaired json: ")
        print(job_json)
    except Exception as e:
        return {'error': f'JSON repair failed: {str(e)}'}
    return job_json

def is_job_within_date_range(job_json, within_days=7):
    try:
        posted_date_str = job_json.get("posted_date", "")
        posted_date = datetime.strptime(posted_date_str, "%d/%m/%Y").date()
        today = datetime.today().date()
        return (today - posted_date).days <= within_days
    except Exception as e:
        print("Date parsing error:", e)
        return None  

def get_relative_posted_time(job_json):
    try: 
        posted_date_str = job_json.get("posted_date", "")
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
    
def enrich_job_json(job_json, location_search, job_url, quick_apply_url, job_metadata):
    job_json["job_url"] = job_url
    job_json["quick_apply_url"] = quick_apply_url
    job_json["location_search"] = location_search
    job_json["posted_date"] = job_metadata["posted_time"]
    job_json["posted_within"] = get_relative_posted_time(job_json)
    job_json["logo_link"] = job_metadata["logo_src"]
    job_json["location"] = job_metadata["location"]
    job_json["classification"] = job_metadata["classification"]
    job_json["work_type"] = job_metadata["work_type"]
    job_json["salary"] = job_metadata["salary"]
    job_json["title"] = job_metadata["title"]
    job_json["company"] = job_metadata["company"]
    return job_json

def flatten_field(field):
    if isinstance(field, list):
        return " ".join(str(item) for item in field)
    return str(field)






