import { Box, Typography, Button, CircularProgress} from "@mui/material";
import { useDropzone } from "react-dropzone";
  
const ResumeDropzone = ({ file, setFile, loading }) => {
  const onDrop = (acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
    }
  };
  
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
      accept: { "application/pdf": [".pdf"] },
      multiple: false,
    });
  
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
        {isDragActive ? (
          <Typography>Drop the file here...</Typography>
        ) : file ? (
          <Typography color="success.main">{file.name}</Typography>
        ) : (
          <Typography>Drag & drop resume (PDF)</Typography>
        )}
        <Button variant="contained" sx={{ textTransform: "none", backgroundColor: '#3B82F6' }} disabled={loading}>
          {loading ? <CircularProgress size={24} /> : "Click to browse"}
        </Button>
      </Box>
    );
  };
  
  export default ResumeDropzone;
  