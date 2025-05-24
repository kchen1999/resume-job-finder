const { DataTypes } = require('sequelize');

module.exports = {
  up: async ({ context: queryInterface }) => {
    await queryInterface.sequelize.query(`CREATE EXTENSION IF NOT EXISTS vector`);
    await queryInterface.createTable('job_embeddings', {
      id: {
        type: DataTypes.INTEGER,
        primaryKey: true,
        autoIncrement: true,
      },
      job_id: {
        type: DataTypes.INTEGER,
        allowNull: false,
        references: {
          model: 'jobs', // references the jobs table
          key: 'id'
        },
        onDelete: 'CASCADE',
      },
      embedding: {
        type: 'VECTOR(768)',
        allowNull: false
      }
    });
  },

  down: async ({ context: queryInterface }) => {
    await queryInterface.dropTable('job_embeddings');
  }
};
