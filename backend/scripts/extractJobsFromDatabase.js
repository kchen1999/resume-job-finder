// scripts/extractJobsFromDatabase.js
const { Job } = require('../models')  // Assuming Job model is properly defined
const { sequelize } = require('../util/db')

/* 
    Queries the Job model in the database and returns a list of job data
*/
const extractJobsFromDatabase = async (criteria = {}) => {
  try {
      await sequelize.authenticate()
      console.log('DB connection established.')

      // Fetch jobs based on the provided criteria
      // If criteria is empty, it will fetch all jobs
      const jobDataList = await Job.findAll({
        where: criteria, // Apply criteria for filtering
        attributes: ['id', 'title', 'company', 'logo_link', 'location', 'location_search', 'experience_level', 
          'salary', 'description', 'responsibilities', 'requirements', 'other', 'posted_date', 
          'posted_within', 'work_type', 'quick_apply_url', 'job_url', 'embedding'],
        raw: true
      })
      console.log(`Found ${jobDataList.length} job(s) in the database.`)
    
    // Return the job data list
      console.log(jobDataList)
      return jobDataList
  } catch (err) {
      console.error('Error fetching jobs:', err)
      return []
  } 
}

module.exports = { extractJobsFromDatabase }
