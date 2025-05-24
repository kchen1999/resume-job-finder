const { DataTypes } = require('sequelize');

module.exports = {
  up: async ({ context: queryInterface }) => {
    await queryInterface.createTable('resumes', {
      id: {
        type: DataTypes.INTEGER,
        primaryKey: true,
        autoIncrement: true,
      },
      name: {
        type: DataTypes.STRING,
        allowNull: true,
      },
      original_text: {
        type: DataTypes.TEXT,
        allowNull: false,
      },
      relevant_text: {
        type: DataTypes.TEXT,
        allowNull: true,
      },
    });
  },

  down: async ({ context: queryInterface }) => {
    await queryInterface.dropTable('resumes');
  },
};
