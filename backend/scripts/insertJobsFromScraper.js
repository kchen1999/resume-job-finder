// scripts/seedJobsFromScraper.js
require('dotenv').config()
const { Job } = require('../models')
const { sequelize } = require('../util/db')
const { scrapeJobJsonDataList } = require('../services/scraperService')
const { generateJobEmbedding } = require('../utils/jina')

/* Scrapes job data from the web (using the scraper python service), 
  generates embeddings for each job, and inserts them into the database. */

const insertJobsFromScraper = async (job_title, location) => {
  try {
    await sequelize.authenticate()
    console.log('DB connection established.')

    const jobDataResponse = await scrapeJobJsonDataList(job_title, location)
    const jobDataList = jobDataResponse.result

    for (const jobData of jobDataList) {
      const embedding = await generateJobEmbedding(jobData)
      if (!embedding) {
        console.warn('Skipping job due to embedding failure:', jobData.title)
        continue
      }
      const [day, month, year] = jobData['posted_date'].split('/');
      const formattedDate = `${year}-${month}-${day}`;
      await Job.create({ ...jobData, quick_apply_url: jobData['quick_apply_url'] || null, posted_date: formattedDate, embedding })
      console.log(`Inserted job: ${jobData.title}`)
    }

    console.log('All jobs seeded successfully.')
  } catch (err) {
    console.error('Seeding error:', err)
  } finally {
    await sequelize.close()
    console.log('DB connection closed.')
  }
}

// Run directly if this file is called with node
if (require.main === module) {
  const [,, job_title, location] = process.argv
  if (!job_title || !location) {
    console.error('Usage: node scripts/insertJobsFromScraper.js "<job_title>" "<location>"')
    process.exit(1)
  }

  insertJobsFromScraper(job_title, location)
}
