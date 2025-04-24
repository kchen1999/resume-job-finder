import os
import re
import json
from datetime import date, datetime
from groq import Groq
from dotenv import load_dotenv
from json_repair import repair_json

load_dotenv()
client = Groq(
    api_key=os.environ.get("GROQ_API_KEY")
)

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

async def extract_fields_from_job_link_with_groq(markdown):
    try:
        current_date = date.today().strftime("%d/%m/%Y")
        prompt = (
            "You are a strict JSON data extraction tool. Extract structured job posting data from the text below.\n\n"
            "- 'description': a short summary of the role. Return an empty string if not found.\n"
            "- 'responsibilities': actual tasks/duties. Do not include headers or unrelated content.\n"
            "- 'requirements': include all technical skills, technologies, years of experience, cloud platforms, front-end/back-end stacks,"
            " architecture knowledge, tools, frameworks, databases, testing tools/methodologies, and certifications" 
            "— even if mentioned outside the 'requirements' section. Use original wording. Do not include section headers.\n"
            " - 'salary': Extract only the actual salary range or rate (e.g., $500 per day, $80k–$100k per year). Do not return suggestions, or advice. If a salary is not explicitly mentioned in the text, return an empty string.\n}"
            "- 'experience_level': infer based on the content. Choose one of: intern, junior, mid, senior, lead.\n"
            "- 'work_type': Identify the job type. Choose one of: 'Full time', 'Part time', 'Casual/Vacation', 'Contract/temp'. If unclear, return an empty string.\n"
            "- 'other': include any extra job-relevant details not captured above. Must be bullet points. Do not include tools, tech, or experience level here.\n\n"
            "Notes:\n"
            "- 'responsibilities', 'requirements', and 'other' must be arrays of strings.\n"
            f"- 'posted_date': Return a string strictly in DD/MM/YYYY format. If the job posting mentions 'X minutes ago' or 'X hours ago', then treat it as posted today and return: {current_date}."
            f"Only if the posting mentions 'X days ago;, subtract that number from today’s date ({current_date}) and return the result."
            "Do not return the posted_date in any other format like YYYY-MM-DD"
            f"- 'posted_within': Based strictly on the 'posted_date' field. Return one of the following strings based on how far the date is from today ({current_date}):\n"
            "    • If the job was posted today, return 'Today'.\n"
            "    • If the job was posted 1 day ago, return '1 day ago'.\n"
            "    • If the job was posted 2 to 6 days ago, return 'X days ago' where X is the number of days.\n"
            "    • If the job was posted more than 6 days ago, return '7+ days ago'.\n"
            "Return a single JSON object with the following fields:\n\n"
            "- title\n- company\n- description\n- responsibilities\n- requirements\n"
            "-location\n- experience_level\n-work_type\n- salary\n-other\n-posted_date\n-posted_within\n\n"
            "Only return valid JSON. Do not include explanations or markdown formatting.\n\n"
            f"Job Posting Text:\n{markdown}"
        )

        chat_completion = client.chat.completions.create(
            messages= [
                {
                    "role": "system",
                    "content": "You extract structured job data from markdown."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="llama-3.1-8b-instant",
        )

        response_text = chat_completion.choices[0].message.content
        return extract_json_from_response(response_text)

    except Exception as e:
        print("Error calling Groq API (refine_data):", e)
        return None

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
    raw_result = await extract_fields_from_job_link_with_groq(job_md)
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
    
def enrich_job_data(job_json, location_search, job_url, quick_apply_url, logo_link):
    job_json["job_url"] = job_url
    job_json["quick_apply_url"] = quick_apply_url
    job_json["location_search"] = location_search
    job_json["logo_link"] = logo_link
    return job_json


