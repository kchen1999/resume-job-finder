require('dotenv').config()
const { Job } = require('../models/index')
//const { sequelize } = require('../util/db')

const job = {
  title: 'Software Engineer (Frontend)',
  company: 'Tech Innovators Inc.',
  description: 'We are looking for a talented frontend developer to join our team.',
  responsibilities: 'Build and maintain UI components, work closely with backend developers, ensure cross-browser compatibility, optimize applications for speed and scalability.',
  requirements: '3+ years of experience with React, knowledge of JavaScript, HTML, CSS, and modern front-end tools like Webpack. Familiarity with version control systems like Git.',
  location: 'San Francisco, CA',
  experience_level: 'Mid-level',
  salary_min: 90000,
  salary_max: 120000,
  submission_date: new Date(),
  expiration_date: new Date('2025-05-01'),
  apply_url: 'https://techinnovators.com/careers/software-engineer-frontend',
}

async function generateEmbedding(jobData) {
  const input = [
    jobData.title,
    jobData.description,
    jobData.responsibilities,
    jobData.requirements,
  ].filter(Boolean).join('\n')

  try {
    const response = await fetch('https://api.jina.ai/v1/embeddings', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.JINA_API_KEY}`,
      },
      body: JSON.stringify({
        model: 'jina-embeddings-v3',
        task: 'text-matching',
        input: [input],
      }),
    })

    const data = await response.json()

    if (!data.data || !data.data[0]?.embedding) {
      console.error('No embedding returned:', data);
      return null
    }
    
    return data.data[0].embedding;
  } catch (err) {
    console.error('Error generating embedding:', err);
    return null
  }
}

async function run() {
  try {
    //await sequelize.authenticate()
    console.log('DB connection established.')

    const embedding = await generateEmbedding(job)
    if (!embedding) throw new Error('Failed to generate embedding.')

    //await Job.create({ ...job, embedding })
    console.log('Job successfully seeded!')
  } catch (err) {
    console.error('Seeding error:', err)
  } finally {
    //await sequelize.close()
    console.log('DB connection closed.')
  }
}

run()
