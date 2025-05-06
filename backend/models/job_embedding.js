const { Model, DataTypes } = require('sequelize')
const { sequelize } = require('../util/db')
const Job = require('./job')

class JobEmbedding extends Model {}

JobEmbedding.init({
  job_id: {
    type: DataTypes.INTEGER,
    references: {
      model: Job, 
      key: 'id'
    },
    primaryKey: true,
    onDelete: 'CASCADE',
  },
  embedding: {
    type: DataTypes.VECTOR(768),
    allowNull: false
  }
}, {
  sequelize,
  modelName: 'job_embedding',
  underscored: true,
  timestamps: false
})

module.exports = JobEmbedding
