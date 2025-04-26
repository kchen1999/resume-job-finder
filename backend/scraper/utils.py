import re
import json
from datetime import datetime
from extractJobJson import extract_fields_from_job_link_with_groq

from json_repair import repair_json

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
        repaired_json_string = repair_json(raw_result)  # Raw string goes here
        print("repairing json...")
        job_json = json.loads(repaired_json_string)
        print("repaired json: ")
        print(job_json)
    except Exception as e:
        return {'error': f'JSON repair failed: {str(e)}'}

    return job_json


def is_within_last_n_days(job_json, within_days=21):
    try:
        posted_date_str = job_json.get("posted_date", "")
        posted_date = datetime.strptime(posted_date_str, "%d/%m/%Y").date()
        today = datetime.today().date()
        return (today - posted_date).days <= within_days
    except Exception as e:
        print("Date parsing error:", e)
        return None
    

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
    elif 2 <= delta <= 6:
        return f'{delta} days ago'
    else:
        return '7+ days ago'
    
def enrich_job_data(job_json, location_search, job_url, quick_apply_url, logo_link, posted_within):
    job_json["job_url"] = job_url
    job_json["quick_apply_url"] = quick_apply_url
    job_json["location_search"] = location_search
    job_json["logo_link"] = logo_link
    job_json["posted_within"] = posted_within
    return job_json


