import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(
    api_key=os.environ.get("GROQ_API_KEY")
)

async def extract_fields_from_job_link_with_groq(markdown):
    try:
        prompt = (
            "You are a strict JSON data extraction tool. Extract job posting data into a valid JSON object, strictly following these rules.\n\n"
            "- 'description': a short summary of what the role is about. Prefer text under 'About the Role', or similar. Return an empty string if not found.\n"
            "- 'responsibilities': actual tasks/duties. Do not include headers or unrelated content.\n"
            "- 'requirements': include all technical skills, technologies, years of experience, cloud platforms, front-end/back-end stacks,"
            " architecture knowledge, tools, frameworks, databases, testing tools/methodologies, and certifications" 
            "— even if mentioned outside the 'requirements' section. Use original wording. Do not include section headers.\n"
            "- 'experience_level': infer based on the job title. Choose one of: intern, junior, mid, senior, lead+.\n"
            " If job title includes 'Lead', 'Manager', 'Principal', 'Head' or similar leadership terms, classify as 'lead+'\n"
            "- 'work_model': Identify the job model. Choose one of: 'Hybrid', 'On-site', or 'Remote' (exact formatting). Treat 'flexible' or 'WFH' as 'Hybrid'. If unclear, return 'On-site'\n"
            "- 'other': list of extra job-relevant details not captured above. Must be bullet points. No tech/tools/experience level here. Each array element must be a simple double-quoted string.\n\n"
            "Return a single JSON object with the following fields:\n\n"
            "- description\n- responsibilities\n- requirements\n"
            "- experience_level\n- work_model\n- other\n\n"
            "**Rules:**\n"
            "- Always return a single valid JSON object.\n"
            "- All property names MUST be enclosed in double quotes.\n"
            "- 'responsibilities', 'requirements', and 'other' must be arrays of strings.\n"
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
            model="llama-3.1-8b-instant",
        )
        return chat_completion.choices[0].message.content
        
    except Exception as e:
        print("Error calling Groq API (refine_data):", e)
        return None
