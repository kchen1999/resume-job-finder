import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(
    api_key=os.environ.get("GROQ_API_KEY")
)

async def extract_fields_from_job_link_with_groq(markdown, count):
    try:
        model = (
            "llama-3.1-8b-instant" if count % 3 == 0 else
            "llama3-70b-8192" if count % 3 == 1 else
            "llama3-8b-8192"
        )
        prompt = (
            "You are a strict JSON data extraction tool. Extract job posting data into a valid JSON object, strictly following these rules.\n\n"
            "- 'description': Extract a short summary (1–3 sentences) of what the role is about. Focus on the mission, purpose, or scope of the role."
            "Prefer content under headers like 'About the Role', 'The Role', 'See yourself in our team', or similar. If no such content exists, return an empty string.n"
            "- 'responsibilities': extract all task-related content from the job posting. Include every responsibility-related bullet point and any action-oriented sentence describing what the candidate will do."
            " Preserve the full phrasing as it appears — do not summarize, shorten, or extract keywords. Do not include headers or unrelated content.\n"
            "- 'requirements': include all technical skills, technologies, years of experience, cloud platforms, front-end/back-end stacks,"
            " architecture knowledge, tools, frameworks, databases, testing tools/methodologies, and certifications" 
            "— even if mentioned outside the 'requirements' section. Extract full phrases or sentences as written in the job text, not just keywords. Preserve the original phrasing and context. Do not summarize or convert into tags.\n"
            "- 'experience_level': Choose one of: 'intern', 'junior', 'mid_or_senior' or 'lead+'. Infer from the job title first, then responsibilities/years of experience if unclear. Never return None."
            "- 'work_model': Choose one of: 'Hybrid', 'On-site', or 'Remote'. Use 'Remote' only if clearly stated. Use 'Hybrid' if terms like 'WFH', 'flexible', or 'work from home' appear. If no clear mention of remote or hybrid, return 'On-site' as default (never return None)."
            "- 'other': list of extra job-relevant details not captured above. Must be bullet points. No tech/tools/experience level here. Each array element must be a simple double-quoted string.\n\n"
            "Return a single JSON object with the following fields:\n\n"
            "- description\n- responsibilities\n- requirements\n"
            "- experience_level\n- work_model\n- other\n\n"
            "**Rules:**\n"
            "- Always return a single valid **JSON object**, not a string.\n"
            "- All keys MUST be double-quoted, as per strict JSON format.\n"
            "- Do NOT wrap the entire output in quotes. Do NOT stringify the JSON.\n"
            "- All string values (including those inside lists) MUST be properly closed with quotes.\n"
            "- The first key must be \"description\".\n"
            "- 'responsibilities', 'requirements', and 'other' must be returned as arrays of strings not as a string.\n"
            "- Arrays must use square brackets [] with double-quoted string values.\n"
            "- Do not include markdown, backticks, or code blocks.\n"
            "- No \n or backslash (\) characters inside keys or values\n"
            "- No explanations, comments, or extra text — only raw minified JSON output.\n"
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
            model=model,
        )
        return chat_completion.choices[0].message.content
        
    except Exception as e:
        print("Error calling Groq API (refine_data):", e)
        return None

async def extract_missing_work_model_with_groq(job_text):
    try:
        model = "llama-3.3-70b-versatile"
        prompt = (
            "You are tasked with determining the 'work_model' (Hybrid, On-site, Remote) for a job posting. "
            "The 'work_model' should be inferred from the information in the job description, responsibilities, "
            "and any mention of work environment, flexibility, or location. Please return only the 'work_model' as a string, "
            "either 'Hybrid', 'On-site', or 'Remote'.\n\n"
            "Job Posting Text:\n{job_text}"
        )
        chat_completion = client.chat.completions.create(
            messages= [
                {
                    "role": "system",
                    "content": "You are an assistant that determines the 'work_model' of a job posting."
                },
                {
                    "role": "user",
                    "content": prompt.format(job_text=job_text)
                }
            ],
            model=model,
        )
        inferred_work_model = chat_completion.choices[0].message.content.strip()
        return inferred_work_model
        
    except Exception as e:
        print("Error calling Groq API:", e)
        return None  # In case of error, return None so the fallback logic can apply
    
async def extract_missing_experience_level_with_groq(job_title, job_text):
    try:
        model = "llama-3.3-70b-versatile"
        prompt = (
            "Determine the 'experience_level' for a job posting based on the job title and content. "
            "Allowed values: 'intern', 'junior', 'mid_or_senior', 'lead+'.\n\n"
            "**Rules:**\n"
            "- If the title includes 'Intern', classify as 'intern'.\n"
            "- If the title includes 'Junior', classify as 'junior'.\n"
            "- If the title includes 'Lead', 'Manager', 'Principal', or 'Head', classify as 'lead+'.\n"
            "- If the title includes 'Senior' but not a leadership title (e.g. 'Senior Software Engineer'), classify as 'mid_or_senior'.\n"
            "- If the title doesn't help, infer from responsibilities and required years of experience.\n"
            "- Return only one of: 'intern', 'junior', 'mid_or_senior', 'lead+' and nothing else — no explanation..\n\n"
            "Job Title: {job_title}\n\n"
            "Job Posting Text:\n{job_text}"
        )
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are an assistant that classifies experience level for a job posting."
                },
                {
                    "role": "user",
                    "content": prompt.format(job_title=job_title, job_text=job_text)
                }
            ],
            model=model,
        )
        inferred_experience = chat_completion.choices[0].message.content.strip().lower()
        print(f"Raw model output: {repr(inferred_experience)}")
        allowed_levels = {"intern", "junior", "mid_or_senior", "lead+"}
        return inferred_experience if inferred_experience in allowed_levels else None

    except Exception as e:
        print("Error calling Groq API (experience_level):", e)
        return None
