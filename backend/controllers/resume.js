const router = require('express').Router()
const multerValidation = require('../middleware/multerValidation')
const jobMatchingService = require('../services/jobMatchingService')
const { Experience } = require('../models');
const { sequelize } = require("../util/db");
const { QueryTypes } = require('sequelize');

// Route + Controller in one file
router.post('/upload', multerValidation.single('resume'), async (req, res) => {
  const filePath = req.file.path

  try {
    const { jobMatches: matchedJobs, experiences } = await jobMatchingService.matchResumeToJobs(filePath, "software engineer");
    console.log("experiences:")
    console.log(experiences)
    res.json({ matchedJobs, experiences });
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

// POST /api/resume/rematch
router.post('/rematch', async (req, res) => {
  const { experienceIds } = req.body;

  if (!Array.isArray(experienceIds) || experienceIds.length === 0) {
    return res.status(400).json({ error: 'experienceIds must be a non-empty array' });
  }

  try {
    // 1. Fetch embeddings for given experienceIds
    const selectedExperiences = await Experience.findAll({
      where: { id: experienceIds },
      attributes: ['embedding']
    });

    const validEmbeddings = selectedExperiences
      .map(e => e.embedding)
      .filter(e => Array.isArray(e) && e.length > 0);

    if (validEmbeddings.length === 0) {
      return res.status(404).json({ error: 'No valid embeddings found' });
    }

    // 2. Average the embeddings
    const dim = validEmbeddings[0].length;
    const sum = Array(dim).fill(0);
    for (const emb of validEmbeddings) {
      for (let i = 0; i < dim; i++) {
        sum[i] += emb[i];
      }
    }
    const averagedEmbedding = sum.map(x => x / validEmbeddings.length);
    console.log("Average embedding: ")
    console.log(averagedEmbedding)

    // 3. Query jobs using pgvector cosine distance
    const results = await sequelize.query(
      `
      SELECT jobs.*, job_embeddings.embedding <#> CAST(:embedding AS vector) AS score
      FROM jobs
      JOIN job_embeddings ON jobs.id = job_embeddings.job_id
      WHERE job_embeddings.embedding IS NOT NULL
      ORDER BY job_embeddings.embedding <#> CAST(:embedding AS vector) ASC
      `,
      {
        replacements: { embedding: `[${averagedEmbedding.join(',')}]` },
        type: QueryTypes.SELECT
      }
    );

    res.json({ matchedJobs: results });
  } catch (err) {
    console.error('Error in /rematch:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

module.exports = router

