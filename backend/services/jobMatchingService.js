const computeCosineSimilarity = require('compute-cosine-similarity');
const parseResume = require("../utils/parser")
const extractResumeSections = require("../utils/extractResumeSections")

const { generateResumeEmbedding } = require("../utils/jina");
const { extractJobsFromDatabase } = require("../scripts/extractJobsFromDatabase")

const matchResumeToJobs = async (filePath, jobTitle) => {
  const text = await parseResume(filePath)
  const relevantResumeSections = await extractResumeSections(text, jobTitle)
  const resumeEmbedding = await generateResumeEmbedding(relevantResumeSections);

  if (!resumeEmbedding) {
    console.error("Failed to generate resume embedding.")
    return []
  }

  const jobDataList = await extractJobsFromDatabase()
  // Create an array of jobs with their cosine similarity to the resume
  const jobSimilarities = jobDataList.map((job) => {
    const jobEmbedding = job.embedding  // Assuming the job embedding is already stored
    if (!jobEmbedding) {
      return { job, similarity: -1 }
    }
    const similarity = computeCosineSimilarity(resumeEmbedding, jobEmbedding)
    return { job, similarity }
  })
  // Sort the jobs by similarity (highest to lowest)
  const sortedJobs = jobSimilarities.sort((a, b) => b.similarity - a.similarity)
  // Return the sorted list of jobs
  return sortedJobs.map(item => item.job)  
  
}

module.exports = { matchResumeToJobs }

