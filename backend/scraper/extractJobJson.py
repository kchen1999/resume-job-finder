from datetime import date
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(
    api_key=os.environ.get("GROQ_API_KEY")
)

async def extract_fields_from_job_link_with_groq(markdown):
    try:
        current_date = date.today().strftime("%d/%m/%Y")
        prompt = (
            "You are a strict JSON data extraction tool. Extract structured job posting data from the text below.\n\n"
            "- 'description': a short summary of the role. Prefer text under 'About the Role', 'The Role', or similar. If no section exists, return only a concise paragraph that explains what the role is about. Return an empty string if not found.\n"
            "- 'responsibilities': actual tasks/duties. Do not include headers or unrelated content.\n"
            "- 'requirements': include all technical skills, technologies, years of experience, cloud platforms, front-end/back-end stacks,"
            " architecture knowledge, tools, frameworks, databases, testing tools/methodologies, and certifications" 
            "— even if mentioned outside the 'requirements' section. Use original wording. Do not include section headers.\n"
            " - 'salary': Extract only the actual salary range or rate (e.g., $500 per day, $80k–$100k per year). Do not return suggestions, or advice. If a salary is not explicitly mentioned in the text, return an empty string."
            "- 'experience_level': infer based primarily on the job title. Choose one of: intern, junior, mid, senior, lead+.\n"
            " If job title includes 'Lead', 'Manager', 'Head' or similar leadership terms, classify as 'lead+'\n"
            "- 'work_type': Identify the job type. Choose one of: 'Full time', 'Part time', 'Casual/Vacation', 'Contract/Temp' (exact formatting). If unclear, return an empty string.\n"
            "- 'work_model': Identify the job model. Choose one of: 'Hybrid', 'On-site', or 'Remote' (exact formatting). Treat 'flexible' or 'WFH' as 'Hybrid' unless it's clearly full-time remote. If unclear, return 'On-site'\n"
            "- 'other': include any extra job-relevant details not captured above. Must be bullet points. Do not include tools, tech, or experience level here.\n\n"
            "Notes:\n"
            "- 'responsibilities', 'requirements', and 'other' must be arrays of strings.\n"
            f"- 'posted_date': Return a string strictly in DD/MM/YYYY format. If the job posting mentions 'X minutes ago' or 'X hours ago', then treat it as posted today and return: {current_date}."
            f"Only if the posting mentions 'X days ago;, subtract that number from today’s date ({current_date}) and return the result."
            "Do not return the posted_date in any other format like YYYY-MM-DD"
            "Return a single JSON object with the following fields:\n\n"
            "- title\n- company\n- description\n- responsibilities\n- requirements\n"
            "- location\n- experience_level\n- work_type\n- salary\n- work_model\n- other\n- posted_date\n\n"
            "Only return **raw, minified** JSON without explanations or markdown formatting. The JSON must be directly parsable.\n\n"
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
