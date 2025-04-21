const fs = require('fs');
const pdfParse = require('pdf-parse'); 

// Parses a PDF file and extract text
const parseResume = async (filePath) => {
  try {
    const dataBuffer = fs.readFileSync(filePath); 
    const data = await pdfParse(dataBuffer);  // Extract text from the PDF
    return data.text; 
  } catch (error) {
    console.error('Error parsing the PDF file:', error);
    throw new Error('Error parsing the resume');
  }
};

module.exports = parseResume;
