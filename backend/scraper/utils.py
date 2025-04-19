import os
import re
import json
from datetime import datetime, date
from models import Job
from database import db
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def handle_missing_fields(job):
    job.setdefault("responsibilities", "N/A")
    job.setdefault("requirements", "N/A")
    job.setdefault("location", "N/A")
    job.setdefault("experience_level", "N/A")
    job.setdefault("salary", "N/A")
    job.setdefault("job_url", "N/A")
    return job

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

async def extract_fields_from_job_link_with_groq(markdown):
    try:
        current_date = date.today().strftime("%d/%m/%Y")
        prompt = (
            "You are a helpful assistant. Extract structured job posting data from the text below. "
            "Description should be an overview of the role otherwise put empty string if not provided"
            "Responsibilities should include actual responsibilities not any headers"
            "Requirements must also include technical skills/experience if provided - include word for word as per the job posting data (remove any headings)"
            "Salary should include range and/or rate i.e. per day/year otherwise put empty string if not provided"
            "Infer the experience level using the following categories - intern, junior, mid, senior, lead"
            "Logo link is the company logo link otherwise put empty string if not provided"
            "Other is all other job-related information provided in the job posting that hasn't been included in any other field in dot point form."
            f"Extract 'posted_date' as DD/MM/YYYY by subtracting the number of days in phrases like 'X days ago' from the current date ({current_date})."
            "Return a single JSON object with the following fields:\n\n"
            "- title\n- company\nlogo-link\n- description\n- responsibilities\n- requirements\n"
            "-location\n- experience_level\n- salary\n-other\n"
            "-posted_date\n-quick_apply_url\n- job_url\n\n"
            "Only return valid JSON. Do not include explanations or markdown formatting.\n\n"
            f"Data:\n{markdown}"
        )

        chat_completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {
                    "role": "system",
                    "content": "You extract structured job data from markdown."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        response_text = chat_completion.choices[0].message.content
        return extract_json_from_response(response_text)

    except Exception as e:
        print("Error calling Groq API (refine_data):", e)
        return None

async def save_jobs_to_db(jobs):
    try:
        for job in jobs:
            job = handle_missing_fields(job)
            db_job = Job(
                title=job.get("title"),
                company=job.get("company"),
                description=job.get("description"),
                responsibilities=job.get("responsibilities"),
                requirements=job.get("requirements"),
                location=job.get("location"),
                experience_level=job.get("experience_level"),
                salary_min=job.get("salary"),
                submission_date=datetime.fromisoformat(job.get("submission_date")) if job.get("submission_date") else None,
                expiration_date=datetime.fromisoformat(job.get("expiration_date")) if job.get("expiration_date") else None,
                job_url=job.get("job_url"),
            )
            db.session.add(db_job)

        await db.session.commit()
        print("Jobs saved successfully")
    except Exception as e:
        await db.session.rollback()
        print("Error saving jobs to DB:", e)

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
