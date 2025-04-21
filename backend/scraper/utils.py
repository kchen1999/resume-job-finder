import os
import re
import json
from datetime import date
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
        return None

def extract_job_links(markdown):
    job_links = []
    for item in markdown:
        links = re.findall(
            r"https://www\.seek\.com\.au/job/\d+\?[^)\s]*origin=cardTitle", item
        )
    job_links.extend(links)
    return job_links 

async def extract_fields_from_job_link_with_groq(markdown, job_url, quick_apply_url):
    try:
        current_date = date.today().strftime("%d/%m/%Y")
        prompt = (
            "You are a strict JSON data extraction tool. Extract structured job posting data from the text below.\n\n"
            "- 'description': a short summary of the role. Return an empty string if not found.\n"
            "- 'responsibilities': actual tasks/duties. Do not include headers or unrelated content.\n"
            "- 'requirements': include all technical skills, technologies, years of experience, cloud platforms, front-end/back-end stacks,"
            "architecture knowledge, tools, frameworks, databases, testing tools/methodologies, and certifications" 
            "— even if mentioned outside the 'requirements' section. Use original wording. Do not include section headers.\n"
            "- 'salary': return the full range and/or rate (e.g., per day, per year). Return empty string if not mentioned.\n"
            "- 'experience_level': infer based on the content. Choose one of: intern, junior, mid, senior, lead.\n"
            "- 'logo_link': return any image URL that appears to be a company logo, else empty string. It must start with https://image-service-cdn.seek.com.au"
            " or https://bx-branding-gateway.cloud.seek.com.au or https://cpp-prod-seek-company-image-uploads.s3.ap-southeast-2.amazonaws.com\n"
            "- 'other': include any extra job-relevant details not captured above. Must be bullet points. Do not include tools, tech, or experience level here.\n\n"
            "Notes:\n"
            "- 'responsibilities', 'requirements', and 'other' must be arrays of strings.\n"
            f"- 'posted_date': return as a string in DD/MM/YYYY format by subtracting the number of days in phrases like 'X days ago' from the current date({current_date}).\n\n"
            f"- job_url: {job_url}\n"
            f"- quick_apply_url: {quick_apply_url}\n\n"
            "Return a single JSON object with the following fields:\n\n"
            "- title\n- company\nlogo-link\n- description\n- responsibilities\n- requirements\n"
            "-location\n- experience_level\n- salary\n-other\n"
            "-posted_date\n-quick_apply_url\n- job_url\n\n"
            "Only return valid JSON. Do not include explanations or markdown formatting.\n\n"
            "Respond with nothing else — no backticks, no extra sentences, no formatting. Just a single JSON object."
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

async def extract_job_data(job_md, job_url, quick_apply_url):
    # Run the job extraction logic
    raw_result = await extract_fields_from_job_link_with_groq(job_md, job_url, quick_apply_url)
    print(f"Type of raw_result: {type(raw_result)}")

     # If it's already a dict (parsed JSON), no need to decode
    if isinstance(raw_result, dict):
        return raw_result
    
    # Clean the extracted JSON using json_repair (if needed)
    try:
        job_json = json.loads(raw_result)
    except json.JSONDecodeError:
        try:
            repaired = repair_json(raw_result)  # Raw string goes here
            print("repairing json...")
            job_json = json.loads(repaired)
        except Exception as e:
            return {'error': f'JSON repair failed: {str(e)}'}

    return job_json
