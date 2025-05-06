const parseResume = require("../utils/parser");
const extractResumeSections = require("../utils/extractResumeSections");
const embedExperienceAndStore = require("../utils/embedExperienceAndStore");

const { Resume, Experience } = require("../models");
const { sequelize } = require("../util/db");
const { QueryTypes } = require("sequelize");
const { jsonrepair } = require('jsonrepair');

const matchResumeToJobs = async (filePath, jobTitle) => {
  try {
    // Step 1: Parse full resume text
    const fullText = await parseResume(filePath);

    // Step 2: Extract relevant sections (structured JSON)
    const relevantResumeSections = await extractResumeSections(fullText, jobTitle);
    const repaired = jsonrepair(relevantResumeSections);
    const parsedSections = JSON.parse(repaired);
    console.log("Parsed sections:");
    console.log(parsedSections);

    // Step 3: Store resume
    const resume = await Resume.create({
      original_text: fullText,
      relevant_text: relevantResumeSections,
    });

    // Step 4: Store experiences
    const storedExperiences = [];
    for (const experience of parsedSections) {
      const stored = await embedExperienceAndStore(experience, resume.id);
      storedExperiences.push({
        id: stored.id,
        title: stored.title || "No title specified",
      });
    }

    // Step 5: Use only the first experience embedding
    if (storedExperiences.length === 0) {
      return {
        jobMatches: [],
        experiences: []
      };
    }

    const firstExperience = await Experience.findOne({
      where: { id: storedExperiences[0].id },
      attributes: ['embedding']
    });

    if (!firstExperience || !Array.isArray(firstExperience.embedding) || firstExperience.embedding.length === 0) {
      return {
        jobMatches: [],
        experiences: storedExperiences
      };
    }
    console.log("firstExperience embedding:")
    console.log(firstExperience.embedding)
    console.log(typeof(firstExperience.embedding))

    // Step 6: Retrieve matching jobs using first embedding
    const jobMatches = await sequelize.query(
      `
      SELECT jobs.*, job_embeddings.embedding <#> CAST(:embedding AS vector) AS score
      FROM jobs
      JOIN job_embeddings ON jobs.id = job_embeddings.job_id
      WHERE job_embeddings.embedding IS NOT NULL
      ORDER BY job_embeddings.embedding <#> CAST(:embedding AS vector) ASC
      `,
      {
        replacements: { embedding: `[${firstExperience.embedding.join(',')}]` },
        type: QueryTypes.SELECT
      }
    );

    return {
      jobMatches,
      experiences: storedExperiences
    }

  } catch (error) {
    console.error("Error in matchResumeToJobs:", error);
    return {
      jobMatches: [],
      experiences: []
    }
  }
}

module.exports = { matchResumeToJobs };




