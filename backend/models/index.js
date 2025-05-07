const Job = require('./job')
const JobEmbedding = require('./job_embedding')
const Resume = require('./resume')
const Experience = require('./experience')

Job.hasOne(JobEmbedding, { foreignKey: 'job_id', onDelete: 'CASCADE' })
JobEmbedding.belongsTo(Job, { foreignKey: 'job_id' })

Resume.hasMany(Experience, { foreignKey: 'resume_id' })
Experience.belongsTo(Resume, { foreignKey: 'resume_id' })

module.exports = {
  Job, JobEmbedding, Resume, Experience
}
