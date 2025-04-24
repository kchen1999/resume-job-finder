import React, { useState } from 'react';
import { Box, Card, CardContent, Typography } from '@mui/material';
import JobDetail from './JobDetail';

const JobResults = ({ results }) => {
  const [selectedJob, setSelectedJob] = useState(results[0]);

  const handleJobClick = (job) => {
    setSelectedJob(job);
  };

  if (!results || results.length === 0) return null;

  return (
    <Box sx={{ display: 'flex', gap: 2 }}>
      {/* Job List - 40% */}
      <Box sx={{ width: '36%' }}>
        {results.map((job) => (
          <Card
            key={job.id}
            variant="outlined"
            sx={{ mb: 2, cursor: 'pointer' }}
            onClick={() => handleJobClick(job)}
          >
            <CardContent>
              {job.logo_link && (
                <Box
                  sx={{
                    display: 'flex',
                    justifyContent: 'flex-start',
                    alignItems: 'center',
                    px: 0.25,
                    py: 0.5,
                  }}
                >
                  <Box
                    component="img"
                    src={job.logo_link}
                    alt=""
                    sx={{ height: 36, maxWidth: '100%', objectFit: 'contain' }}
                  />
                </Box>
              )}
              <Typography variant="h6">{job.title}</Typography>
              <Typography variant="body2" gutterBottom>
                {job.company}
              </Typography>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                {job.location}
              </Typography>
  
              {job.work_type && (
                <Box
                  sx={{
                    display: 'inline-block',
                    backgroundColor: '#e0f2f1',
                    color: '#00695c',
                    px: 1.5,
                    py: 0.5,
                    borderRadius: 1,
                    fontSize: '0.75rem',
                    fontWeight: 500,
                    mb: 1,
                  }}
                >
                  {job.work_type}
                </Box>
              )}
            </CardContent>
          </Card>
        ))}
      </Box>
  
      {/* Job Detail - 60% */}
      <Box
        sx={{
          width: '64%',
          maxHeight: 'calc(100vh - 32px)',
          position: 'sticky',
          top: 16,
          overflowY: 'auto',
          overflowX: 'hidden',
          border: '1px solid #ddd',
          borderRadius: 2,
          backgroundColor: '#fff',
          boxShadow: 1,
        }}
      >
        <JobDetail job={selectedJob} />
      </Box>
    </Box>
  );
  
};

export default JobResults;


  