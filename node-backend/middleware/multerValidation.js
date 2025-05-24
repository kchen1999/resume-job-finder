// src/middleware/multerValidation.js
const multer = require('multer')
const path = require('path')

// Configure multer storage
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, 'uploads/'); // Store in 'uploads' folder
  },
  filename: (req, file, cb) => {
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1e9)
    cb(null, uniqueSuffix + path.extname(file.originalname));
  },
})

// File validation: only accept PDFs
const fileFilter = (req, file, cb) => {
  if (file.mimetype !== 'application/pdf') {
    return cb(new Error('Invalid file type. Only PDFs are allowed.'), false);
  }
  cb(null, true);
}

const upload = multer({ storage, fileFilter })

module.exports = upload
