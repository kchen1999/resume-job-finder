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
    type: DataTypes.STRING, 
    allowNull: true
  },
  original_text: { // full resume text
    type: DataTypes.TEXT,
    allowNull: false 
  },
  relevant_text: { // LLM-extracted relevant sections
    type: DataTypes.TEXT,
    allowNull: true 
  }
}, {
  sequelize,
  modelName: 'resume',
  underscored: true,
  timestamps: false
})

module.exports = Resume
