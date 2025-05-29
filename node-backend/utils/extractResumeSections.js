const path = require('path')
const Groq = require("groq-sdk")

if (!process.env.FLY_REGION) {
  require('dotenv').config({ path: path.resolve(__dirname, '../.env') })
}

const getGroqAPIKey = () => {
  const apiKey = process.env.GROQ_API_KEY
  if (!apiKey) {
    throw new Error('GROQ_API_KEY is not defined in the environment.')
  }
  return apiKey
}

const groq = new Groq({ apiKey: getGroqAPIKey() })

// Extracts relevant resume sections using LLM 
const extractResumeSections = async (resumeText, jobTitle) => {
  const prompt = `
    You are a strict JSON extraction tool. Your task is to extract only relevant **work, internship, project, or open-source experiences** from the resume text below, specifically for the job title: "${jobTitle}".
    **Rules for output:**
    1. **Output format** must be a **valid, properly formatted JSON array**.
    2. Each object in the array must contain:
       - "title" (string): The job or project title.
       - "organization" (string): The company, university, or project name.
       - "type" (string): One of: "job", "internship", "project", or "open-source".
       - "description" (string): A 3–4 sentence description of what the candidate did, including goals, technologies used, and outcomes/responsibilities. Include as much detail as possible.
       - "skills" (array of strings): Each string should represent a skill e.g., "Java", "Python", "React", "JavaScript - Advanced".
    3. **Important JSON formatting instructions:**
       - Use double quotes for all keys and string values.
       - No trailing commas.
       - The "skills" field must always be an array of strings. Return an empty array if no skills directly attributable to the experience.
       - Avoid including any unnecessary characters, such as newline (\n), backslashes (\), or any extra text.
       - Do not include backticks, or code blocks.
       - Each object in the array needs to have five keys
    4. **Absolutely do not**:
       - Include markdown, comments, code blocks, or any text before/after the JSON.
       - Include extra objects or keys not listed above.
       - Leave any object unclosed or any key without a colon/value.
    5. If no relevant experiences to the job title exist, return an empty array.
    
    **Important:** Do not include any additional text or notes — just return the **raw JSON output**.

    Resume:
    ${resumeText}
  `
    const response = await groq.chat.completions.create({
      messages: [
        { 
            role: "system", 
            content: "You are an assistant for extracting key resume sections." 
        },
        { 
            role: "user", 
            content: prompt 
        }
      ],
        model: "llama3-70b-8192",
    })
    const extractedText = response.choices[0].message.content;
    console.log(extractedText)
    return extractedText; 
  }

module.exports = extractResumeSections
