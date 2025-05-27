import { useState, useEffect } from "react"
import axios from "axios"
import ResumeDropzone from "./ResumeDropzone"
import JobResults from "./JobResults"
import JobFilters from "./JobFilters"
import { Box } from '@mui/material'
const API_BASE_URL = import.meta.env.VITE_NODE_BACKEND_URL

const ResumeAnalyzer = () => {
  const [file, setFile] = useState(null)
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [userExperiences, setUserExperiences] = useState([]) // Store resume experiences
  const [filters, setFilters] = useState({
    experience: '',
    experienceIds: [],
    posted: '',
    domain: '',
    location: '',
  })

   // Fetch the jobs when the component mounts
   useEffect(() => {
    const fetchJobs = async () => {
      try {
        const res = await axios.get(`${API_BASE_URL}/jobs`);
        setResults(res.data); // Set the initial results (jobs from DB)
      } catch (err) {
        console.error("Failed to fetch jobs", err)
      }
    };

    fetchJobs()
  }, []) 

    // Re-match jobs whenever selected resume experienceIds change
  useEffect(() => {
    const rematch = async () => {
      if (filters.experienceIds.length === 0) return;
      try {
        const res = await axios.post(`${API_BASE_URL}/resume/rematch`, {
          experienceIds: filters.experienceIds,
        });
        setResults(res.data.matchedJobs)
      } catch (err) {
        console.error("Failed to re-match jobs", err)
      }
    }
      rematch()
    }, [filters.experienceIds])

  const handleSubmit = async (uploadedFile) => {
    const fileToUse = uploadedFile || file
    if (!fileToUse) {
        alert("Please upload a resume before submitting.")
        return
    }

    setLoading(true);
    const formData = new FormData();
    formData.append("resume", fileToUse);

    try {
        const res = await axios.post(`${API_BASE_URL}/resume/upload`, formData)
        if (res.data.matchedJobs.length > 0) {
          setResults(res.data.matchedJobs)
          console.log("matchedJobs:")
          console.log(res.data.matchedJobs)
          setUserExperiences(res.data.experiences);      // Set parsed resume experiences
          if (res.data.experiences.length > 0) {
            setFilters(prev => ({
              ...prev,
              experienceIds: [res.data.experiences[0].id] // Default selection
            }));
          }
        } else {
          console.log("matchedJobs empty:")
          console.log(res.data.matchedJobs)
          console.log("experiences:")
          console.log(res.data.experiences)
        }

    } catch (err) {
        alert("Something went wrong.")
        console.error(err)
    } finally {
        setLoading(false)
    }
  }

  const parseDDMMYYYY = (str) => {
    const [day, month, year] = str.split('/')
    return new Date(`${year}-${month}-${day}`)
  }

  const applyFilters = (jobs, filters) => {
    if (!Array.isArray(jobs)) {
      return []
    }
    return jobs.filter(job => {
      // Experience filter (if set and not empty)
      if (filters.experience && filters.experience.length > 0) {
        const normalizedExperience = filters.experience.map(level => level.toLowerCase().trim())
        const jobLevel = job.experience_level?.toLowerCase().trim()

        if (!jobLevel) return false
        // If user selected "Mid / Senior", treat it as matching "mid_or_senior"
        if (normalizedExperience.includes("mid / senior") && jobLevel === "mid_or_senior"
        ) {
          // Match
        } else if (!normalizedExperience.includes(jobLevel)) {
          return false
        }
      }
  
      // Location filter
      if (filters.location && filters.location !== '') {
        if (filters.location.length > 0) {
          if (!filters.location.includes(job.location_search)) return false
        }
      }
  
      // Posted Within filter (e.g. "7" for 7 days ago)
      if (filters.posted && filters.posted !== '') {
        const daysAgo = parseInt(filters.posted, 10)
        const postedCutoff = new Date()
        postedCutoff.setDate(postedCutoff.getDate() - daysAgo)
  
        const jobPostedDate = parseDDMMYYYY(job.posted_date)
        if (jobPostedDate < postedCutoff) return false
      }
  
      return true
    })
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, alignItems: 'center', justifyContent: 'center' }}>
        <form onSubmit={handleSubmit}>
          <ResumeDropzone
              file={file}
              setFile={(newFile) => {
                setFile(newFile)
                if (newFile) {
                  handleSubmit(newFile)
                }
              }}
              loading={loading}
          />
        </form>
      </Box>
      <JobFilters filters={filters} setFilters={setFilters} userExperiences={userExperiences}/>
      <JobResults results={applyFilters(results, filters)} />
    </Box>
  )
}

export default ResumeAnalyzer

