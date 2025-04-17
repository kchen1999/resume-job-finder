import os
import re
import json
from datetime import datetime
from models import Job
from database import db
from groq import Groq
from crawl import scrape_job

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def handle_missing_fields(job):
    job.setdefault("responsibilities", "N/A")
    job.setdefault("requirements", "N/A")
    job.setdefault("location", "N/A")
    job.setdefault("experience_level", "N/A")
    job.setdefault("salary_min", 0)
    job.setdefault("salary_max", 0)
    job.setdefault("apply_url", "N/A")
    return job

def extract_json_from_response(response):
    try:
        if isinstance(response, dict) or isinstance(response, list):
            return response
        start = response.find('{')
        end = response.rfind('}') + 1
        return json.loads(response[start:end])
    except Exception as e:
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

async def extract_fields_from_page_with_groq(data):
    try:
        prompt = (
            "You are a helpful assistant. Extract structured job posting data from the text below. "
            "Infer the experience level using the following categories - intern, junior/new grad, mid, senior, lead"
            "Return a single JSON object with the following fields:\n\n"
            "- title\n- company\n- description\n- responsibilities\n- requirements\n"
            "- location\n- experience_level\n- salary_min\n- salary_max\n"
            "- submission_date\n- expiration_date\n- apply_url\n\n"
            "Only return valid JSON. Do not include explanations or markdown formatting.\n\n"
            f"Data:\n{json.dumps(data)}"
        )

        chat_completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {
                    "role": "system",
                    "content": "You extract structured job data from messy text."
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
                salary_min=job.get("salary_min"),
                salary_max=job.get("salary_max"),
                submission_date=datetime.fromisoformat(job.get("submission_date")) if job.get("submission_date") else None,
                expiration_date=datetime.fromisoformat(job.get("expiration_date")) if job.get("expiration_date") else None,
                apply_url=job.get("apply_url"),
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
