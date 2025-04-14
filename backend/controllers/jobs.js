const router = require('express').Router()

const { Job } = require('../models')

router.get('/', async (req, res) => {
  const notes = await Job.findAll()
  res.json(notes)
})

router.post('/', async (req, res) => {
  try {
    const job = await Job.create(req.body)
    res.json(job)
  } catch(error) {
    return res.status(400).json({ error })
  }
})

const jobFinder = async (req, res, next) => {
    req.job = await Job.findByPk(req.params.id)
    next();
}

router.get('/:id', jobFinder, async (req, res) => {
  if (req.job) {
    res.json(req.job)
  } else {
    res.status(404).end()
  }
})

router.delete('/:id', jobFinder,  async (req, res) => {
  if (req.job) {
    await req.job.destroy()
  }
  res.status(204).end()
})

router.put('/:id', jobFinder,  async (req, res) => {
  if (req.job) {
    await req.job.save()
    res.json(req.job)
  } else {
    res.status(404).end()
  }
})

module.exports = router
