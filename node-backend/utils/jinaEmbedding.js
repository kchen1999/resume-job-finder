const path = require('path')
require('dotenv').config({ path: path.resolve(__dirname, '../.env') })

const generateJobEmbeddings = async (jobDataList) => {
  const inputs = jobDataList

  try {
    const response = await fetch('https://api.jina.ai/v1/embeddings', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.JINA_API_KEY}`,
      },
      body: JSON.stringify({
        model: 'jina-embeddings-v3',
        task: 'text-matching',
        dimensions: 768,
        input: inputs,
      }),
    })

    const data = await response.json()
    if (!data.data || !Array.isArray(data.data)) {
      console.error('No embedding returned:', data)
      return null
    }

    return data.data.map(item => item.embedding);
  } catch (err) {
      console.error('Error generating embedding:', err)
      return null
  }
}

module.exports = { generateJobEmbeddings }
