import re
import json
from datetime import datetime, timedelta
from scraper.extractJobJson import extract_fields_from_job_link_with_groq
import httpx

from json_repair import repair_json

POSTED_TIME_SPAN_CLASS = "gg45di0 _1ubeeig4z _1oxsqkd0 _1oxsqkd1 _1oxsqkd22 _18ybopc4 _1oxsqkd7"

def extract_json_from_response(response):
    try:
        if isinstance(response, dict) or isinstance(response, list):
            return response
        start = response.find('{')
        end = response.rfind('}') + 1
        return json.loads(response[start:end])
    except Exception as e:
        print(f"Raw response: {repr(response)}")
        print("Error parsing JSON:", e)
        return response

def extract_job_links(markdown):
    job_links = []
    for item in markdown:
        links = re.findall(
            r"https://www\.seek\.com\.au/job/\d+\?[^)\s]*origin=cardTitle", item
        )
    job_links.extend(links)
    return job_links 

def extract_job_url_and_quick_apply_url(job_link):
    job_url = re.search(r"https:\/\/www\.seek\.com\.au\/job\/\d+", job_link).group()
    quick_apply_url = job_url + "/apply"
    return [job_url, quick_apply_url]


def process_markdown_to_job_links(markdown):
    try:
        job_links = extract_job_links(markdown)
        if not job_links:
            print("Step 1 failed: No job links extracted")
            return None
        
        for link in job_links:
            print("Scraping:", link)
        return job_links
            
    except Exception as e:
        print("Processing error:", e)
        return None

def truncate_logo_url(url):
    if isinstance(url, str) and "https://cpp-prod-seek-company-image-uploads.s3.ap-southeast-2.amazonaws.com/" in url:
        logo_index = url.find("/logo/")
        if logo_index != -1:
            return url[:logo_index + len("/logo/")]
    return url  # or return "" if you want to clear it instead

def clean_string(raw_string):
    # Remove backslashes and newline characters
    cleaned = raw_string.replace('\\', '').replace('\n', '')
    return cleaned

async def extract_job_data(job_md):
    # Run the job extraction logic
    response_text = await extract_fields_from_job_link_with_groq(job_md)
    raw_result = extract_json_from_response(response_text)
    print(f"Type of raw_result: {type(raw_result)}")

     # If it's already a dict (parsed JSON), no need to decode
    if isinstance(raw_result, dict):
        return raw_result
    
    # Clean the extracted JSON using json_repair (if needed)
    try:
        if isinstance(raw_result, str):
            raw_result = clean_string(raw_result)
            print("Cleaned json: ")
            print(raw_result)
        repaired_json_string = repair_json(raw_result)  # Raw string goes here
        print("repairing json...")
        job_json = json.loads(repaired_json_string)
        print("repaired json: ")
        print(job_json)
    except Exception as e:
        return {'error': f'JSON repair failed: {str(e)}'}

    return job_json


def is_within_last_n_days(job_json, within_days=7):
    try:
        posted_date_str = job_json.get("posted_date", "")
        posted_date = datetime.strptime(posted_date_str, "%d/%m/%Y").date()
        today = datetime.today().date()
        return (today - posted_date).days <= within_days
    except Exception as e:
        print("Date parsing error:", e)
        return None

def get_posted_date(posted_days_ago: int) -> str:
    """
    Given the number of days ago a job was posted, return the date in DD/MM/YYYY format.
    """
    posted_date = datetime.today() - timedelta(days=posted_days_ago)
    return posted_date.strftime("%d/%m/%Y")   

def get_posted_within(job_json):
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
    elif 2 <= delta <= 7:
        return f'{delta} days ago'
    
def enrich_job_data(job_json, location_search, job_url, quick_apply_url, job_data):
    job_json["job_url"] = job_url
    job_json["quick_apply_url"] = quick_apply_url
    job_json["location_search"] = location_search
    job_json["posted_date"] = job_data["posted_time"]
    job_json["posted_within"] = get_posted_within(job_json)
    job_json["logo_link"] = truncate_logo_url(job_data["logo_src"])
    job_json["location"] = job_data["location"]
    job_json["classification"] = job_data["classification"]
    job_json["work_type"] = job_data["work_type"]
    job_json["salary"] = job_data["salary"]
    job_json["title"] = job_data["title"]
    job_json["company"] = job_data["company"]
    return job_json

async def send_page_jobs_to_node(job_data_list):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:3000/api/jobs/page-batch",  # or your deployed URL
                json={"jobs": job_data_list}
            )
            response.raise_for_status()
            print("Successfully sent jobs to Node")
    except httpx.HTTPStatusError as exc:
        print(f"Failed to insert jobs: {exc.response.status_code} - {exc.response.text}")
        raise




