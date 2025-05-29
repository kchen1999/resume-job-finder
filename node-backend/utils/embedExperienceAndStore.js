const path = require('path')
const { Experience } = require('../models')

if (!process.env.FLY_REGION) {
  require('dotenv').config({ path: path.resolve(__dirname, '../.env') })
}

const getJinaAPIKey = () => {
  const apiKey = process.env.JINA_API_KEY
  if (!apiKey) {
    throw new Error('JINA_API_KEY is not defined in the environment.')
  }
  return apiKey
}

const embedExperienceAndStore = async (experience, resumeId) => {
    try {
      // Format the text for the experience
      const text = `${experience.title} at ${experience.organization || 'Unknown'} (${experience.type}): ${experience.description || ''}`;
  
      // Use fetch to call the Jina API to generate the experience embedding
      const response = await fetch('https://api.jina.ai/v1/embeddings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getJinaAPIKey()}`,
        },
        body: JSON.stringify({
          model: 'jina-embeddings-v3', 
          task: 'text-matching',      
          dimensions: 768,
          input: [text],              
        }),
      })
  
      const data = await response.json()
  
      // Check if the embedding is returned and handle failure
      if (!data.data || !data.data[0]?.embedding) {
        console.error('No embedding returned for experience:', text);
        return
      }
  
      // Extract embedding from the response
      const embedding = data.data[0].embedding
  
      // Store the experience data and embedding into the database
      const stored = await Experience.create({
        title: experience.title,
        organization: experience.organization,
        type: experience.type,
        description: experience.description,
        skills: experience.skills || [],  
        embedding: embedding, 
        resume_id: resumeId,             
      })
      
      return { id: stored.id, title: stored.title }
    } catch (error) {
      console.error('Error embedding and storing experience:', error)
      return { id: null }
    }
  }
  
  module.exports = embedExperienceAndStore
  