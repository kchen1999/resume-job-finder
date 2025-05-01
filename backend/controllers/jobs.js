const router = require('express').Router()
const { Job, JobEmbedding } = require('../models')
const { generateJobEmbedding } = require('../utils/jina')

// Existing GET /jobs endpoint
router.get('/', async (req, res) => {
  const jobs = await Job.findAll()
  res.json(jobs)
})

// New POST /jobs/page-batch endpoint
router.post('/page-batch', async (req, res) => {
  const pageJobDataList = req.body.jobs

  if (!Array.isArray(pageJobDataList) || pageJobDataList.length === 0) {
    return res.status(400).json({ error: 'Empty or invalid job data batch.' })
  }

  const bulkInsertData = []
  const bulkEmbeddingData = []

  for (const jobData of pageJobDataList) {
    try {
      const embedding = await generateJobEmbedding(jobData)
      if (!embedding || !jobData.title) {
        console.warn('Skipping invalid job:', jobData.title)
        continue
      }

      const [day, month, year] = jobData['posted_date'].split('/')
      jobData.posted_date = `${year}-${month}-${day}`
      jobData.quick_apply_url = jobData['quick_apply_url'] || null

      bulkInsertData.push(jobData)
      bulkEmbeddingData.push({
        job_id: null,
        embedding,
      })
    } catch (err) {
      console.error('Error processing jobData:', err)
    }
  }

  if (bulkInsertData.length === 0) {
    return res.status(200).json({ message: 'No valid jobs to insert.' })
  }

  try {
    const insertedJobs = await Job.bulkCreate(bulkInsertData, { returning: true })
    insertedJobs.forEach((job, index) => {
      bulkEmbeddingData[index].job_id = job.id
    })
    await JobEmbedding.bulkCreate(bulkEmbeddingData)
    return res.status(200).json({ inserted: insertedJobs.length })
  } catch (err) {
    console.error('Error inserting job page:', err)
    return res.status(500).json({ error: 'Failed to insert job page' })
  }
})

module.exports = router
