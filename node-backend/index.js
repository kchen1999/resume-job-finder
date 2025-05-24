const express = require('express');
const app = express();

const { PORT } = require('./util/config')
const { connectToDatabase } = require('./util/db')
const cors = require('cors');

const resumeRouter = require('./controllers/resume');
const jobsRouter = require('./controllers/jobs');

app.use(express.json());
app.use(cors());

app.use('/api/resume', resumeRouter);
app.use('/api/jobs', jobsRouter);

// Optionally serve uploaded files statically
//app.use('/uploads', express.static('uploads'));

const start = async () => {
  await connectToDatabase()
  app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`)
  })
}

start()

