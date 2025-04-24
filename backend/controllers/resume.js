const router = require('express').Router()
const multerValidation = require('../middleware/multerValidation')
const jobMatchingService = require('../services/jobMatchingService')
const { Job } = require('../models');

// Route + Controller in one file
router.post('/upload', multerValidation.single('resume'), async (req, res) => {
  const filePath = req.file.path

  try {
    const allJobs = await Job.findAll();
    const matchedJobs = await jobMatchingService.matchResumeToJobs(filePath, allJobs, "software engineer");

    res.json({ matchedJobs })
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

module.exports = router

