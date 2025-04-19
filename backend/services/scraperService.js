const axios = require('axios')

const scrapeJobJsonDataList = async (job_title, location) => {
  try {
    const response = await axios.post('http://localhost:5000/test-db', {
      job_title,
      location,
    });
    console.log('Received job data list:', response.data)
    return response.data
  } catch (error) {
    console.error('Failed to scrape jobs:', error.response?.data || error.message)
    return []
  }
}

module.exports = { scrapeJobJsonDataList }



