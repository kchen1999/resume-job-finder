const { DataTypes } = require('sequelize');

module.exports = {
  up: async ({ context: queryInterface }) => {
    await queryInterface.createTable('job_embeddings', {
      job_id: {
        type: DataTypes.INTEGER,
        allowNull: false,
        primaryKey: true,
        references: {
          model: 'jobs', // references the jobs table
          key: 'id'
        },
        onDelete: 'CASCADE',
      },
      embedding: {
        type: DataTypes.JSONB,
        allowNull: true
      }
    });
  },

  down: async ({ context: queryInterface }) => {
    await queryInterface.dropTable('job_embeddings');
  }
};
