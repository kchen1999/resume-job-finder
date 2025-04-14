const commonJobTitles = [
    "software engineer", "frontend developer", "backend developer",
    "full stack developer", "data scientist", "devops engineer",
    "project manager", "qa engineer", "product manager"
  ];
  
const extractJobTitle = (text) => {
    const lowerText = text.toLowerCase();
    return commonJobTitles.find(title => lowerText.includes(title.toLowerCase())) || "Unknown";
};
  
module.exports = extractJobTitle;
  
  