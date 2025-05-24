const { Model, DataTypes } = require('sequelize')
const { sequelize } = require('../util/db')
const Job = require('./job')

class JobEmbedding extends Model {}

JobEmbedding.init({
  id: {
    type: DataTypes.INTEGER,
    autoIncrement: true,
    primaryKey: true
  },
  job_id: {
    type: DataTypes.INTEGER,
    allowNull: false,
    references: {
      model: Job,
      key: 'id'
    },
    onDelete: 'CASCADE'
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
