const { Model, DataTypes } = require('sequelize');
const { sequelize } = require('../util/db'); // adjust the path to your Sequelize instance

class Job extends Model {}

Job.init({
  id: {
    type: DataTypes.INTEGER,
    primaryKey: true,
    autoIncrement: true
  },
  title: {
    type: DataTypes.STRING,
    allowNull: false
  },
  company: {
    type: DataTypes.STRING,
    allowNull: true
  },
  description: {
    type: DataTypes.TEXT,
    allowNull: true
  },
  responsibilities: {
    type: DataTypes.TEXT,
    allowNull: true
  },
  requirements: {
    type: DataTypes.TEXT,
    allowNull: true
  },
  location: {
    type: DataTypes.STRING,
    allowNull: true
  },
  experience_level: {
    type: DataTypes.STRING, // e.g., 'entry', 'mid', 'senior'
    allowNull: true
  },
  salary_min: {
    type: DataTypes.INTEGER,
    allowNull: true
  },
  salary_max: {
    type: DataTypes.INTEGER,
    allowNull: true
  },
  submission_date: {
    type: DataTypes.DATE,
    allowNull: true,
    defaultValue: DataTypes.NOW
  },
  expiration_date: {
    type: DataTypes.DATE,
    allowNull: true
  },
  embedding: {
    type: DataTypes.JSONB,
    allowNull: true // Will store embedding array (vector)
  },
  apply_url: {
    type: DataTypes.STRING,
    allowNull: true // This will store the job application link
  }
}, {
  sequelize,
  modelName: 'job',
  underscored: true,
  timestamps: false
});

module.exports = Job;
