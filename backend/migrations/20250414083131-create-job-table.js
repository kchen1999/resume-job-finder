const { DataTypes } = require('sequelize');

module.exports = {
  up: async ({ context: queryInterface }) => {
    await queryInterface.createTable('jobs', {
      id: {
        type: DataTypes.INTEGER,
        primaryKey: true,
        autoIncrement: true
      },
      logo_link: {
        type: DataTypes.STRING,
        allowNull: true
      },
      title: {
        type: DataTypes.STRING,
        allowNull: false
      },
      company: {
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
      experience_level: {
        type: DataTypes.STRING,
        allowNull: true
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
        type: DataTypes.DATE,
        allowNull: false,
        defaultValue: DataTypes.NOW
      },
      embedding: {
        type: DataTypes.JSONB,
        allowNull: true
      },
      quick_apply_url: {
        type: DataTypes.STRING,
        allowNull: true
      },
      job_url: {
        type: DataTypes.STRING,
        allowNull: true
      }
    });
  },

  down: async ({ context: queryInterface }) => {
    await queryInterface.dropTable('jobs');
  }
};

