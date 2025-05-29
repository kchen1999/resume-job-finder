  const Sequelize = require('sequelize')
  const fs = require('fs')
  const path = require('path')
  const pgvector = require('pgvector/sequelize')
  const { getDatabaseUrl } = require('./config')
  const { Umzug, SequelizeStorage } = require('umzug')

  let caCertificate = null
  try {
    caCertificate = fs.readFileSync(path.join(__dirname, '..', 'certs', 'ca.pem')).toString()
  } catch (err) {
    console.error('[ERROR] Failed to load CA cert:', err)
  }

  pgvector.registerType(Sequelize)

  const sequelize = new Sequelize(getDatabaseUrl(), {
    dialect: 'postgres',
    dialectOptions: {
      ssl: {
        require: true,
        rejectUnauthorized: true,
        ca: caCertificate,
      },
    },
  })

  const runMigrations = async () => {
    const migrator = new Umzug({
      migrations: {
          glob: 'migrations/*.js',
      },
      storage: new SequelizeStorage({ sequelize, tableName: 'migrations' }),
      context: sequelize.getQueryInterface(),
      logger: console,
      })
      
    const migrations = await migrator.up()
      console.log('Migrations up to date', {
        files: migrations.map((mig) => mig.name),
      })
  }

  const connectToDatabase = async () => {
    try {
      await sequelize.authenticate()
      await runMigrations()
      console.log('connected to the database')
    } catch (err) {
      console.log(err)
      console.log('failed to connect to the database')
      return process.exit(1)
    }

    return null
  }

  process.on('SIGINT', async () => {
    try {
      await sequelize.close();
      console.log('Sequelize pool closed successfully.');
      process.exit(0);
    } catch (err) {
      console.error('Error during shutdown:', err);
      process.exit(1);
    }
  });

  module.exports = { connectToDatabase, sequelize }
