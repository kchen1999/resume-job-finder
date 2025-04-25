import React, { useState, useEffect } from 'react';
import { Box, Typography, Skeleton } from '@mui/material';
import JobDetailsPanel from './JobDetailsPanel';
import JobListPanel from './JobListPanel';

const JobResults = ({ results }) => {
  const [selectedJob, setSelectedJob] = useState(results[0])

  useEffect(() => {
    if (results && results.length > 0) {
      setSelectedJob(results[0]);
    }
  }, [results])


  const handleJobClick = (job) => {
    setSelectedJob(job);
  }

  if (results === undefined) {
    // While loading: show skeleton
    return (
      <Box sx={{ p: 2 }}>
        <Skeleton variant="text" width={200} height={30} />
        <Skeleton variant="rectangular" width="100%" height={120} sx={{ my: 2 }} />
        <Skeleton variant="rectangular" width="100%" height={120} />
      </Box>
    )
  }

  if (results.length === 0) {
    // Empty state
    return (
      <Box sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h6" color="text.secondary">
          No jobs found for filters applied.
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Try adjusting your filters or check back later.
        </Typography>
      </Box>
    )
  }

  return (
    <Box sx={{ display: 'flex', gap: 2 }}>
      <JobListPanel results={results} onJobClick={handleJobClick}/>
      {selectedJob && <JobDetailsPanel job={selectedJob} />}
    </Box>
  )
  
}

export default JobResults


  