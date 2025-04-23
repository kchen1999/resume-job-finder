import { useState } from "react";
import axios from "axios";
import ResumeDropzone from "./ResumeDropzone";
import JobResults from "./JobResults";
import JobFilters from "./JobFilters";
import { Box } from '@mui/material';

const ResumeAnalyzer = () => {
  const [file, setFile] = useState(null);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    experience: '',
    posted: '',
    domain: '',
    location: '',
  });

  const handleSubmit = async (uploadedFile) => {
    const fileToUse = uploadedFile || file;
    if (!fileToUse) {
        alert("Please upload a resume before submitting.");
        return; 
    };

    setLoading(true);
    const formData = new FormData();
    formData.append("resume", fileToUse);

    try {
        const res = await axios.post("http://localhost:3000/api/resume/upload", formData);
        setResults(res.data.matchedJobs);
    } catch (err) {
        alert("Something went wrong.");
        console.error(err);
    } finally {
        setLoading(false);
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, alignItems: 'center', justifyContent: 'center' }}>
        <form onSubmit={handleSubmit}>
          <ResumeDropzone
              file={file}
              setFile={(newFile) => {
                setFile(newFile);
                if (newFile) {
                  handleSubmit(newFile);
                }
              }}
              loading={loading}
          />
        </form>
      </Box>
      <JobFilters filters={filters} setFilters={setFilters} />
      <JobResults results={results} />
    </Box>
  );
};

export default ResumeAnalyzer;

