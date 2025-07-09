const { Model, DataTypes } = require('sequelize')
const { sequelize } = require('../util/db')

class Job extends Model {}

Job.init({
  id: {
    type: DataTypes.INTEGER,
    primaryKey: true,
    autoIncrement: true
  },
  logo_link: {
    type: DataTypes.STRING,
    allowNull: true,
  },
  title: {
    type: DataTypes.STRING,
    allowNull: false
  },
  company: {
    type: DataTypes.STRING,
    allowNull: false
  },
  classification: {
    type: DataTypes.STRING,
    allowNull: false
  },
  description: {
    type: DataTypes.TEXT,
    allowNull: true
  },
  responsibilities: {
    type: DataTypes.ARRAY(DataTypes.STRING),
    allowNull: true
  },
  requirements: {
    type: DataTypes.ARRAY(DataTypes.STRING),
    allowNull: true
  },
  location: {
    type: DataTypes.STRING,
    allowNull: true
  },
  location_search: {
    type: DataTypes.STRING,
    allowNull: true
  },
  experience_level: {
    type: DataTypes.STRING, 
    allowNull: true,
    validate: {
      isIn: {
        args: [['intern', 'junior', 'mid_or_senior', 'lead']],
        msg: 'Experience level must be one of: intern, junior, mid_or_senior, lead'
      }
    }
  },
  salary: {
    type: DataTypes.TEXT,
    allowNull: true
  },
  other: {
    type: DataTypes.ARRAY(DataTypes.STRING),
    allowNull: true
  },
  posted_date: {
    type: DataTypes.TEXT,
    allowNull: false,
  },
  posted_within: {
    type: DataTypes.TEXT,
    allowNull: false,
  },
  work_type: {
    type: DataTypes.TEXT,
    allowNull: false,
  },
  work_model: {
    type: DataTypes.TEXT,
    allowNull: false,
  },
  quick_apply_url: {
    type: DataTypes.STRING,
    allowNull: true, 
    validate: {
      isUrl: {
        msg: 'Must be a valid URL.'
      }
    }
  }, 
  job_url: {
    type: DataTypes.STRING,
    allowNull: true,
    validate: {
      isUrl: {
        msg: 'Must be a valid URL.'
      }
    }
  }
}, {
  sequelize,
  modelName: 'job',
  underscored: true,
  timestamps: false
})

module.exports = Job
