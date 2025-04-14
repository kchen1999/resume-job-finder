const fs = require('fs');
const pdfParse = require('pdf-parse'); // You can use the pdf-parse library to extract text from PDFs

// Function to parse a PDF file and extract text
const parseResume = async (filePath) => {
  try {
    const dataBuffer = fs.readFileSync(filePath);  // Read the PDF file
    const data = await pdfParse(dataBuffer);  // Extract text from the PDF
    return data.text;  // Return the extracted text
  } catch (error) {
    console.error('Error parsing the PDF file:', error);
    throw new Error('Error parsing the resume');
  }
};

module.exports = parseResume;
