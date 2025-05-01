const router = require('express').Router()
const { Job, JobEmbedding } = require('../models')
const { generateJobEmbeddings } = require('../utils/jina')

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

  // Format embedding input and normalize job data
  const embeddingInputs = pageJobDataList.map(jobData => {
    const [day, month, year] = jobData['posted_date'].split('/')
    jobData.posted_date = `${year}-${month}-${day}`
    jobData.quick_apply_url = jobData['quick_apply_url'] || null

    return [
      jobData.title,
      jobData.responsibilities,
      jobData.requirements,
    ].filter(Boolean).join('\n')
  })

  try {
    const embeddings = await generateJobEmbeddings(embeddingInputs)

    if (!embeddings || embeddings.length !== pageJobDataList.length) {
      return res.status(500).json({ error: 'Embedding count mismatch.' })
    }

    const insertedJobs = await Job.bulkCreate(pageJobDataList, { returning: true })

    const bulkEmbeddingData = insertedJobs.map((job, index) => ({
      job_id: job.id,
      embedding: embeddings[index],
    }))

    await JobEmbedding.bulkCreate(bulkEmbeddingData)

    return res.status(200).json({ inserted: insertedJobs.length })
  } catch (err) {
    console.error('Error inserting job page:', err)
    return res.status(500).json({ error: 'Failed to insert job page' })
  }
})


module.exports = router
