const express = require('express')
const app = express()

const { PORT } = require('./util/config')
const { connectToDatabase } = require('./util/db')
const cors = require('cors')

const resumeRouter = require('./controllers/resume')
const jobsRouter = require('./controllers/jobs')
const pingRouter = require('./controllers/ping')

app.use(express.json())
app.use(cors())

app.get('/', (req, res) => {
  res.json({ message: 'Welcome to the backend' });
})

app.use('/api/resume', resumeRouter)
app.use('/api/jobs', jobsRouter)
app.use('/api/ping', pingRouter)

const start = async () => {
  try {
    await connectToDatabase()
    console.log('Connected to DB')
    app.listen(PORT, '0.0.0.0', () => {
      console.log(`Server running on port ${PORT}`)
    })
  } catch (err) {
    console.error('Startup failed:', err)
  }
}

start()

