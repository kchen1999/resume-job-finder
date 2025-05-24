const { Model, DataTypes } = require('sequelize')
const { sequelize } = require('../util/db')

class Resume extends Model {}

Resume.init({
  id: {
    type: DataTypes.INTEGER,
    primaryKey: true,
    autoIncrement: true
  },
  name: {
    type: DataTypes.STRING, // optional label like filename
    allowNull: true
  },
  original_text: {
    type: DataTypes.TEXT,
    allowNull: false // full resume text
  },
  relevant_text: {
    type: DataTypes.TEXT,
    allowNull: true // LLM-extracted relevant sections
  }
}, {
  sequelize,
  modelName: 'resume',
  underscored: true,
  timestamps: false
})

module.exports = Resume
