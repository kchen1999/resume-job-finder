const router = require('express').Router()
const { Job } = require('../models')
const { sequelize } = require("../util/db");
const { generateJobEmbeddings } = require('../utils/jinaEmbedding')

router.get('/', async (req, res) => {
  const jobs = await Job.findAll()
  res.json(jobs)
})

router.post('/scrape-summary', async (req, res) => {
  try {
    const { message, errors, invalid_jobs, terminated_early } = req.body

    console.log("Scrape summary received:")
    console.log("Message:", message)

    if (terminated_early) console.warn("Scrape terminated early!")
    if (errors) console.error("Errors:", errors)
    if (invalid_jobs?.length) {
      console.warn(`${invalid_jobs.length} invalid jobs received`)
      console.log("Invalid jobs list:", JSON.stringify(invalid_jobs, null, 2))
    } else {
      console.log("No invalid jobs received.")
    }
    return res.status(200).json({ received: true })
  } catch (err) {
    console.error("Failed to handle scrape summary:", err);
    return res.status(500).json({ error: "Failed to process summary" })
  }
})

router.post('/page-batch', async (req, res) => {
  const pageJobDataList = req.body.jobs

  if (!Array.isArray(pageJobDataList) || pageJobDataList.length === 0) {
    return res.status(400).json({ error: 'Empty or invalid job data batch.' })
  }

  const embeddingInputs = pageJobDataList.map(jobData => {
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

    const values = insertedJobs.map((job, index) => {
      const embeddingVector = '[' + embeddings[index].join(',') + ']'; // convert to '0.1,0.2,...'
      return `(${job.id}, '${embeddingVector}')`;
    }).join(', ');
    
    await sequelize.query(`
      INSERT INTO job_embeddings (job_id, embedding)
      VALUES ${values}
    `); 
    
    return res.status(200).json({ inserted: insertedJobs.length })
  } catch (err) {
    console.error('Error inserting job page:', err)
    return res.status(500).json({ error: 'Failed to insert job page' })
  }
})

module.exports = router
