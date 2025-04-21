const router = require('express').Router()
const multerValidation = require('../middleware/multerValidation')
const jobMatchingService = require('../services/jobMatchingService')

// Route + Controller in one file
router.post('/upload', multerValidation.single('resume'), async (req, res) => {
  if (!req.file) {
    return res.status(400).json({ error: 'No file uploaded.' })
  }
  const filePath = req.file.path

  try {
    const matchedJobs = await jobMatchingService.matchResumeToJobs(filePath, "software engineer");
    res.json({ matchedJobs })
  } catch (error) {
    res.status(500).json({ error: error.message })
  }
})

module.exports = router

