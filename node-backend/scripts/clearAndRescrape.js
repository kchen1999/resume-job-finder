import { sequelize } from '../models/index.js'; // adjust path if needed
import { Job } from '../models'; // your Sequelize models

const clearAndRescrape = async() => {
  try {
    console.log('Starting daily job refresh...');

    await Job.destroy({ where: {} });
    await sequelize.query('ALTER SEQUENCE jobs_id_seq RESTART WITH 1');
    await sequelize.query('ALTER SEQUENCE jobs_embeddings_id_seq RESTART WITH 1');

    console.log('Cleared jobs and embeddings');

    const response = await axios.post('http://localhost:8000/start-scraping', {
      job_title: 'software engineer',
      location: 'sydney',
    });

    console.log('Scraper response status:', response.status);
    console.log('Scraper response:', response.data);

  } catch (err) {
    console.error('Error during job refresh:', err);
  } finally {
    await sequelize.close();
  }
}

clearAndRescrape();
