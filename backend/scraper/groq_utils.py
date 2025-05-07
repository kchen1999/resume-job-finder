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
            "- 'description': Extract a short summary (1–3 sentences) of what the role is about (purpose, mission or scope). Prefer text under headers like 'About the Role', 'The Role', or similar. "
            "Return an empty string only for description if no such content exists.\n"
            "- 'responsibilities': actual tasks/duties. Do not include headers or unrelated content.\n"
            "- 'requirements': include all technical skills, technologies, years of experience, cloud platforms, front-end/back-end stacks,"
            " architecture knowledge, tools, frameworks, databases, testing tools/methodologies, and certifications" 
            "— even if mentioned outside the 'requirements' section. Use original wording. Do not include section headers.\n"
            "- 'experience_level': Infer from job title first, then responsibilities/years of experience if unclear. Use one of: 'intern', 'junior', 'mid', 'senior', 'lead+' "
            "If the job title includes 'Lead', (e.g. 'Engineering Lead', 'Lead Developer') classify as 'lead+'. "
            "If the job title includes 'Manager', 'Principal', 'Head', or similar leadership terms classify as 'lead+'. "
            "If the job title includes 'Senior' and is not part of a leadership title then classify as 'senior' (e.g. 'Senior Software Engineer' is 'senior', but 'Senior Manager' is 'lead+')."
            "If the job title includes 'Intern', classify as 'intern' and if job title includes 'Junior', classify as 'junior'."
            "If none of the above, infer from responsibilities and years of experience.\n"
            "- 'work_model': Identify the job model. Choose one of: 'Hybrid', 'On-site', or 'Remote' (exact formatting). Treat 'flexible' or 'WFH' as 'Hybrid'. If unclear, default to 'On-site'.\n"
            "- 'other': list of extra job-relevant details not captured above. Must be bullet points. No tech/tools/experience level here. Each array element must be a simple double-quoted string.\n\n"
            "Return a single JSON object with the following fields:\n\n"
            "- description\n- responsibilities\n- requirements\n"
            "- experience_level\n- work_model\n- other\n\n"
            "**Rules:**\n"
            "- Always return a single valid JSON object.\n"
            "- All property names MUST be enclosed in double quotes.\n"
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
        # Adjust the prompt to focus only on inferring the 'work_model' as a string.
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
        
        # Extract the inferred work model (should be a string)
        inferred_work_model = chat_completion.choices[0].message.content.strip()
        
        # Return the inferred work model as a string
        return inferred_work_model
        
    except Exception as e:
        print("Error calling Groq API:", e)
        return None  # In case of error, return None so the fallback logic can apply
    
async def extract_missing_experience_level_with_groq(job_title, job_text):
    try:
        model = "llama-3.3-70b-versatile"
        prompt = (
            "Determine the 'experience_level' for a job posting based on the job title and content. "
            "Allowed values: 'intern', 'junior', 'mid', 'senior', 'lead+'.\n\n"
            "**Rules:**\n"
            "- If the title includes 'Intern', classify as 'intern'.\n"
            "- If the title includes 'Junior', classify as 'junior'.\n"
            "- If the title includes 'Lead', 'Manager', 'Principal', or 'Head', classify as 'lead+'.\n"
            "- If the title includes 'Senior' but not a leadership title (e.g. 'Senior Software Engineer'), classify as 'senior'.\n"
            "- If the title doesn't help, infer from responsibilities and required years of experience.\n"
            "- Return only one of: 'intern', 'junior', 'mid', 'senior', 'lead+'.\n\n"
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
        allowed_levels = {"intern", "junior", "mid", "senior", "lead+"}
        return inferred_experience if inferred_experience in allowed_levels else None

    except Exception as e:
        print("Error calling Groq API (experience_level):", e)
        return None
