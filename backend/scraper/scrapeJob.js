const axios = require('axios');

const scrapeJobMarkdown = async (job_title, location) => {
  try {
    const response = await axios.post('http://localhost:5000/scrape', {
      job_title,
      location,
    });

    const markdown = response.data.results;
    console.log('Scraped markdown:', markdown);
    return markdown;
  } catch (error) {
    console.error('Scraping failed:', error.response?.data || error.message);
    return null;
  }
};

const testDbConnection = async (job_title, location) => {
  try {
    const response = await axios.post('http://localhost:5000/test-db', {
      job_title,
      location,
    });
    console.log('Database test response:', response.data);
  } catch (error) {
    console.error('Database test failed:', error.response?.data || error.message);
  }
};

//scrapeJobMarkdown('software engineer', 'sydney');
testDbConnection('software engineer', 'sydney');
