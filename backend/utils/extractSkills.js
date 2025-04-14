const knownSkills = [
    "javascript", "node.js", "react", "express", "sql", "mongodb",
    "python", "java", "c++", "aws", "docker", "kubernetes",
    "communication", "teamwork", "leadership", "git"
  ];

const extractSkills = (text) => {
    const lowerText = text.toLowerCase();
    return knownSkills.filter(skill =>
      lowerText.includes(skill.toLowerCase())
    );
  };
  
  module.exports = extractSkills;
  