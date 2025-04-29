// scripts/seedJobsFromScraper.js
require('dotenv').config()
const { Job, JobEmbedding } = require('../models')
const { sequelize } = require('../util/db')
const { scrapeJobJsonDataList } = require('../services/scraperService')
const { generateJobEmbedding } = require('../utils/jina')

/* Scrapes job data from the web (using the scraper python service),
   generates embeddings for each job, and inserts them into the database. 
   All DB operations are wrapped in a transaction to ensure atomicity.
*/

const insertJobsFromScraper = async (job_title, location) => {
  let transaction

  try {
    const jobDataResponse = await scrapeJobJsonDataList(job_title, location)
    const jobDataList = jobDataResponse.result

    const bulkInsertData = []
    const bulkEmbeddingData = []

    for (const jobData of jobDataList) {
      const embedding = await generateJobEmbedding(jobData)
      if (!embedding) {
        console.warn('Skipping job due to embedding failure:', jobData.title)
        continue
      }

      if (!jobData.title) {
        console.warn('Missing job title, skipping:', jobData)
        continue
      }

      const [day, month, year] = jobData['posted_date'].split('/')
      jobData.posted_date = `${year}-${month}-${day}`
      jobData.quick_apply_url = jobData['quick_apply_url'] || null

      bulkInsertData.push(jobData)
      bulkEmbeddingData.push({
        job_id: null, // will be assigned later
        embedding
      })
      console.log(`Prepared job: ${jobData.title}`)
    }

    if (bulkInsertData.length === 0) {
      console.warn('No jobs prepared for insertion. Exiting early.')
      return
    }

    // Ensure DB connection is established before any DB operations
    await sequelize.authenticate()
    console.log('DB connection established.')

    // Start a transaction
    transaction = await sequelize.transaction()


    // Perform the first bulk insert for jobs
    const insertedJobs = await Job.bulkCreate(bulkInsertData, { returning: true, transaction })
    console.log('All jobs inserted successfully.')


    // Update bulkEmbeddingData with correct job IDs after insert
    insertedJobs.forEach((job, index) => {
      bulkEmbeddingData[index].job_id = job.id
    })

    // Perform the second bulk insert for embeddings
    await JobEmbedding.bulkCreate(bulkEmbeddingData, { transaction })
    console.log('All embeddings inserted successfully.')

    // Commit the transaction if everything succeeds
    await transaction.commit()
    console.log('Transaction committed successfully.')
  } catch (err) {
    console.error('Seeding error:', err)
    // Rollback if transaction was started
    if (transaction) {
      try {
        await transaction.rollback()
        console.log('Transaction rolled back due to error.')
      } catch (rollbackError) {
        console.error('Error during transaction rollback:', rollbackError)
      }
    }
  } finally {
    try {
      await sequelize.close()
      console.log('DB connection closed.')
    } catch (closeError) {
      console.error('Error closing DB connection:', closeError)
    }
  }
}

// Run directly if this file is called with node
if (require.main === module) {
  (async () => {
    const [,, job_title, location] = process.argv
    if (!job_title || !location) {
      console.error('Usage: node scripts/insertJobsFromScraper.js "<job_title>" "<location>"')
      process.exit(1)
    }

    try {
      console.log(`Starting insert for job title "${job_title}" in location "${location}"`)
      await insertJobsFromScraper(job_title, location)
      console.log('Seeding completed.')
      process.exit(0)
    } catch (err) {
      console.error('Fatal error during script execution:', err)
      process.exit(1)
    }
  })()
}
