require('dotenv').config()

const generateJobEmbedding = async (jobData) => {
  const input = [
    jobData.title,
    jobData.company,
    jobData.location,
    jobData.experience_level,
    jobData.salary,
    jobData.description,
    jobData.responsibilities,
    jobData.requirements,
    jobData.other,
  ].filter(Boolean).join('\n')

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
        input: [input],
      }),
    })

    const data = await response.json()
    if (!data.data || !data.data[0]?.embedding) {
      console.error('No embedding returned:', data)
      return null
    }

    return data.data[0].embedding
  } catch (err) {
    console.error('Error generating embedding:', err)
    return null
  }
}

module.exports = { generateJobEmbedding }
