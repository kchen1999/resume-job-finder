const { Model, DataTypes } = require('sequelize')
const { sequelize } = require('../util/db')

class Experience extends Model {}

Experience.init({
  id: {
    type: DataTypes.INTEGER,
    primaryKey: true,
    autoIncrement: true
  },
  resume_id: {
    type: DataTypes.INTEGER,
    allowNull: false,
    references: {
      model: 'resumes',
      key: 'id'
    },
    onDelete: 'CASCADE'
  },
  title: {
    type: DataTypes.STRING,
    allowNull: false
  },
  organization: {
    type: DataTypes.STRING,
    allowNull: true
  },
  type: {
    type: DataTypes.ENUM('job', 'internship', 'project', 'open-source'),
    allowNull: false
  },
  description: {
    type: DataTypes.TEXT,
    allowNull: true
  },
  skills: {
    type: DataTypes.ARRAY(DataTypes.STRING),
    allowNull: true
  },
  embedding: {
    type: DataTypes.VECTOR(768),
    allowNull: true // Optional if you embed individual experiences
  }
}, {
  sequelize,
  modelName: 'experience',
  underscored: true,
  timestamps: false
})

module.exports = Experience
