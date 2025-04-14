const parseResume = require("../utils/parser")
const extractSkills = require("../utils/extractSkills")
const extractJobTitle = require("../utils/extractJobTitle")
const jobData = require("../data/sampleJobs.json")

const matchResumeToJobs = async (filePath) => {
  const text = await parseResume(filePath)

  const extractedSkills = extractSkills(text)
  const jobTitle = extractJobTitle(text)

  const matches = jobData.filter((job) => {
    const titleMatch = job.title.toLowerCase() === jobTitle;
    const skillMatch = job.skills.some((s) =>
      extractedSkills.includes(s.toLowerCase())
    )
    return titleMatch || skillMatch
  })

  return matches
}


module.exports = { matchResumeToJobs }

