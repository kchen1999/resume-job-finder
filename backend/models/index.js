const Job = require('./job')
const JobEmbedding = require('./job_embedding')

Job.sync()
JobEmbedding.sync()

module.exports = {
  Job, JobEmbedding
}
