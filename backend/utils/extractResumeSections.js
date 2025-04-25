const Groq = require("groq-sdk")
require('dotenv').config()

const groq = new Groq({ apiKey: process.env.GROQ_API_KEY })

// Extracts relevant resume sections using LLM 
const extractResumeSections = async (resumeText, jobTitle) => {
  const prompt = `
    You are an intelligent system that extracts structured experience data from resumes to match candidates to the job title: "${jobTitle}".

    Instructions:
      - Only include experience relevant to ${jobTitle}, even if it's from side projects or open-source work.
      - For each experience, return:
      - "title": job or project title
      - "organization": company or project name
      - "type": one of ["job", "internship", "project", "open-source"]
      - "description": short summary of what the candidate did
      - Include all relevant technical skills with proficiency if mentioned (e.g., "Python - Intermediate").
      - Include education details: degree, school, graduation year (if mentioned).
      - Ignore personal info, hobbies, or unrelated content.

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
