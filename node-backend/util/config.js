const path = require('path')

if (!process.env.FLY_REGION) {
  require('dotenv').config({ path: path.resolve(__dirname, '../.env') })
}

const getDatabaseUrl = () => {
  const url = process.env.DATABASE_URL
  if (!url) {
    throw new Error('DATABASE_URL is not defined in the environment.')
  }
  return url
}

module.exports = {
  getDatabaseUrl,
  PORT : process.env.PORT || 3000
}
