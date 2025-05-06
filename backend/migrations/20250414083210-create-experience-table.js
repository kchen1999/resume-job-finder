const { DataTypes } = require('sequelize');

module.exports = {
  up: async ({ context: queryInterface }) => {
    await queryInterface.sequelize.query(`CREATE EXTENSION IF NOT EXISTS vector`);
    await queryInterface.createTable('experiences', {
      id: {
        type: DataTypes.INTEGER,
        primaryKey: true,
        autoIncrement: true,
      },
      resume_id: {
        type: DataTypes.INTEGER,
        allowNull: false,
        references: {
          model: 'resumes',
          key: 'id',
        },
        onDelete: 'CASCADE',
      },
      title: {
        type: DataTypes.STRING,
        allowNull: false,
      },
      organization: {
        type: DataTypes.STRING,
        allowNull: true,
      },
      type: {
        type: DataTypes.ENUM('job', 'internship', 'project', 'open-source'),
        allowNull: false,
      },
      description: {
        type: DataTypes.TEXT,
        allowNull: true,
      },
      skills: {
        type: DataTypes.ARRAY(DataTypes.STRING),
        allowNull: true,
      },
      embedding: {
        type: 'VECTOR(768)',
        allowNull: true,
      },
    });
  },

  down: async ({ context: queryInterface }) => {
    await queryInterface.dropTable('experiences');
    
  },
};
