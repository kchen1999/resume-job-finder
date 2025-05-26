import os
from groq import Groq
from dotenv import load_dotenv
from constants import ALLOWED_WORK_MODEL_VALUES, ALLOWED_EXPERIENCE_LEVEL_VALUES

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
client = Groq(
    api_key=os.environ.get("GROQ_API_KEY")
)

async def parse_job_posting(markdown, count):
    try:
        model = (
            "llama-3.1-8b-instant" if count % 3 == 0 else
            "llama3-70b-8192" if count % 3 == 1 else
            "llama3-8b-8192"
        )
        prompt = (
            "You are a strict JSON data extraction tool. Extract job posting data into a valid JSON object, strictly following these rules.\n"
            
            "- 'description': Extract up to 3 full sentences from the job posting that clearly describe the **role’s mission, purpose, or high-level objectives**. Return them as a **single string** (not a list). These sentences must explain **why the role exists** and how it **contributes to the company’s goals, impact, or innovation**.\n"
            "Include only sentences that meet **all** of the following criteria:\n"
            "  - Must be **verbatim** from the job posting (no paraphrasing or summarising).\n"
            "  - Must describe **what the role enables, delivers, improves**, or its **business purpose**, not general company background or a list of tasks\n"
            "  - Must appear in one of these places: the **first 3 paragraphs**, or under headings like 'About the Role', 'Role Overview', or similar (prioritize these first).\n"
            "  - Can include hiring intent if tied to business purpose, e.g., 'We are proud to be working with...', 'We are seeking X to help...'.\n"
            "Do **not** include:\n"
            "  - Bullet points or technical task lists or list of specific responsibilities (that is left for the 'responsibilities' field).\n"
            "  - Company background, culture, benefits, perks, eligibility criteria, diversity encouragements or unrelated HR information unless they directly explain the role's purpose.\n"
            "  - Generic filler phrases like 'great opportunity', 'fast-paced environment', or unrelated fluff.\n"
            "  - Content under headings like 'Responsibilities' or 'Requirements'"
            "If multiple candidate sentences qualify, select those that appear **earliest**. If no qualifying sentence exists, return an **empty string**.\n\n"
        
            "- 'responsibilities': Extract all content that describes what the candidate will do in the role. Include every task-related bullet point or action-oriented sentence that outlines responsibilities, duties, or deliverables. Only include actions, not skills, qualifications, experience levels, or technologies unless they are part of an action. Return full sentences exactly as written in the original text. Do not include section headings, requirement-related content, or summaries\n"

            "- 'requirements': Extract all technical skills, technologies, years of experience, cloud platforms, frontend/backend stacks, architecture knowledge, tools, frameworks, databases, testing tools/methodologies, and certifications — even if mentioned outside the 'Requirements' section. Return exact phrasing as in the text, not keywords or tags. Return these an array of strings (one per distinct requirement) and **no extra quotation marks** inside the strings.\n"

            "- 'experience_level': Choose one of: 'intern', 'junior', 'mid_or_senior', or 'lead+'. Infer from the job title first; if unclear, infer from level of responsibility and the depth/breadth of required experience."
            "Return 'junior' if the role requires less than 2 years of experience and appears entry-level. Return 'mid_or_senior' if the role is technical and requires significant experience but no clear indication of leadership. Return 'lead+' only if the role clearly involves leadership, strategic ownership, or team management. Always return one of the four exact strings. Never return None.\n"

            "- 'work_model': You must classify the `work_model` field strictly as one of: 'Remote', 'Hybrid', or 'On-site'.\n"
            "- Return 'Remote' ONLY if the job post explicitly states that remote work is allowed, using exact phrases like: 'remote', 'work remotely', 'fully remote', or 'can work from anywhere'. These words **must be clearly stated** and **refer to the job itself**, not company culture or benefits."
            "- Return 'Hybrid' ONLY if the job post clearly mentions a split between home and office, using exact phrases like: 'work from home part of the week', 'hybrid', 'X days in office', 'flexible work arrangement', or 'WFH'."
            "- Otherwise, default to 'On-site', even if flexibility or modern culture is implied."
            "- Do NOT assume remote or hybrid based on flexibility, benefits, perks, company culture, or modern tech stack."
            "- Be strict. If the post is ambiguous or does not directly mention remote/hybrid, choose 'On-site'."
            "- Never return None.\n"  

            "- 'other': Include a list of additional job-relevant details not already captured above. This must be a **list of bullet points**, each as a **string** and **no extra quotation marks** inside the strings. Do not include technologies, tools, or experience level here.\n\n"

            "Return a single JSON object with exactly the following six keys and no others in this exact order:\n"
            "- description\n- responsibilities\n- requirements\n- experience_level\n- work_model\n- other\n\n"

            "**Rules:**\n"
            "- Always return a single valid **JSON object** — not a string.\n"
            "- 'responsibilities', 'requirements', and 'other' must be arrays of strings. (Remove bullet point formatting)\n"
            "- All keys MUST be in lower case and double-quoted (strictly one set of double quotes), as per strict JSON format.\n"
            "- Do NOT wrap the entire output in quotes. Do NOT stringify the JSON.\n"
            "- All string values (including those inside lists) MUST be properly closed with quotes and strictly one set of quotes (not two sets of quotes).\n"
            "- The first key must be 'description'.\n"
            "- Arrays must use square brackets [] with double-quoted string values.\n"
            "- Do not include markdown, backticks, or code blocks.\n"
            "- No newline (`\\n`) or backslash (`\\`) characters in keys or values.\n"
            "- No explanations, comments, or extra text — only the raw minified JSON output.\n\n"

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

async def infer_work_model(job_text):
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
        return inferred_work_model if inferred_work_model in ALLOWED_WORK_MODEL_VALUES else None
        
    except Exception as e:
        print("Error calling Groq API: (work_model)", e)
        return None  
    
async def infer_experience_level(job_title, job_text):
    try:
        model = "llama-3.3-70b-versatile"
        prompt = (
            "You are a strict classification model. Your task is to determine the 'experience_level' for a job posting.\n\n"
            "Allowed values:\n"
            "- 'intern'\n"
            "- 'junior'\n"
            "- 'mid_or_senior'\n"
            "- 'lead+'\n\n"

            "Rules:\n"
            "- Do not rely on the job title alone. Instead, infer experience level from the full job description, responsibilities, and years of experience required.\n"
            "- Return:\n"
            "  - 'intern' if the role is clearly an internship or student placement.\n"
            "  - 'junior' if the job is entry-level or requires less than 2 years of experience.\n"
            "  - 'mid_or_senior' if the job is technical and expects substantial experience (but not leadership).\n"
            "  - 'lead+' only if the job clearly involves managing others, leading teams, or setting strategy.\n"
            "- Only return **one** of the four allowed strings.\n"
            "- Do not explain your answer. Do not return anything else.\n\n"

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
        return inferred_experience if inferred_experience in ALLOWED_EXPERIENCE_LEVEL_VALUES else None

    except Exception as e:
        print("Error calling Groq API (experience_level):", e)
        return None
