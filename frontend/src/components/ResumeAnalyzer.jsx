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

  const parseDDMMYYYY = (str) => {
    const [day, month, year] = str.split('/');
    return new Date(`${year}-${month}-${day}`); // converts safely to YYYY-MM-DD
  };

  const applyFilters = (jobs, filters) => {
    return jobs.filter(job => {
      // Experience filter (if set and not empty)
      if (filters.experience && filters.experience.length > 0) {
        const normalizedExperience = filters.experience.map(level => level.toLowerCase().trim());
        if (!normalizedExperience.includes(job.experience_level.toLowerCase().trim())) return false;
      }
  
      // Location filter
      if (filters.location && filters.location !== '') {
        console.log("b")
        console.log(filters.location)
        console.log(job.location)
        if (filters.location.length > 0) {
          if (!filters.location.includes(job.location)) return false;
        }
      }
  
      // Posted Within filter (e.g. "7" for 7 days ago)
      if (filters.posted && filters.posted !== '') {
        console.log("c")
        const daysAgo = parseInt(filters.posted, 10);
        const postedCutoff = new Date();
        postedCutoff.setDate(postedCutoff.getDate() - daysAgo);
  
        const jobPostedDate = parseDDMMYYYY(job.posted_date);
  
        if (jobPostedDate < postedCutoff) return false;
      }
  
      return true;
    });
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
      <JobResults results={applyFilters(results, filters)} />
    </Box>
  );
};

export default ResumeAnalyzer;

