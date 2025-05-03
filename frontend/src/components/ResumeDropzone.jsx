import { Box, Button, CircularProgress, Typography } from "@mui/material"
import { useDropzone } from "react-dropzone"
  
const ResumeDropzone = ({ file, setFile, loading }) => {
  const onDrop = (acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0])
    }
  }
  
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
      accept: { "application/pdf": [".pdf"] },
      multiple: false,
    })
  
  return (
    <Box
      {...getRootProps()}
      sx={{
        border: "2px dashed #ccc",
        borderRadius: 2,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 1.5,
        padding: 4,
        cursor: "pointer",
        backgroundColor: isDragActive ? "#f0f0f0" : "transparent",
        width: "100%",
        minWidth: '270px',
        mt: 3,
      }}
    >
      <input {...getInputProps()} />
        <Box
          sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'white',
          height: '100%', // ensure vertical centering
          }}
        >
        <svg xmlns="http://www.w3.org/2000/svg" 
          viewBox="0 0 24 24" 
          fill="none" 
          stroke="currentColor" 
          strokeLinecap="round" 
          strokeLinejoin="round" 
          width="33" 
          height="33" 
          strokeWidth="2"
        >
          <path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2 -2v-2"></path>
          <path d="M7 9l5 -5l5 5"></path>
          <path d="M12 4l0 12"></path>
        </svg>
        </Box>
        {isDragActive ? (
          <Typography>Drop the file here...</Typography>
        ) : file ? (
          <Typography>{file.name}</Typography>
        ) : (
          <Typography>Drag & drop resume (PDF)</Typography>
        )}
        <Button variant="contained" sx={{ textTransform: "none", backgroundColor: '#1976d2' }} disabled={loading}>
          {loading ? <CircularProgress size={24} /> : "Click to browse"}
        </Button>
      </Box>
    )
  }
  
  export default ResumeDropzone
  