// JobListPanel.jsx
import React from 'react';
import { Box, Card, CardContent, Chip, Typography } from '@mui/material';

const JobListPanel = ({ results, onJobClick }) => {
  return (
    <Box sx={{ width: '36%' }}>
      {results.map((job) => (
        <Card
          key={job.id}
          variant="outlined"
          sx={{ mb: 2, cursor: 'pointer' }}
          onClick={() => onJobClick(job)}
        >
          <CardContent>
            <Typography variant="h6" sx={{ fontWeight: 'bold'}}>{job.title}</Typography>
            <Typography variant="body2" gutterBottom>{job.company}</Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>{job.location}</Typography>
            <Box sx={{ display: 'flex', gap: 0.5 }}>
                {job.work_type && 
                <Chip 
                    label={job.work_type} 
                    icon={
                        <svg 
                        xmlns="http://www.w3.org/2000/svg" 
                        viewBox="0 0 24 24" 
                        fill="none" 
                        stroke="currentColor" 
                        strokeLinecap="round" 
                        strokeLinejoin="round" 
                        width="14" 
                        height="14" 
                        strokeWidth="2"
                        >
                        <path d="M5 13a7 7 0 1 0 14 0a7 7 0 0 0 -14 0z"></path>
                        <path d="M14.5 10.5l-2.5 2.5"></path>
                        <path d="M17 8l1 -1"></path>
                        <path d="M14 3h-4"></path>
                        </svg>
                    }
                />
                }
                {job.work_model &&
                <Chip 
                    label={job.work_model} 
                />
                }
            </Box>
          </CardContent>
        </Card>
      ))}
    </Box>
  );
};

export default JobListPanel;
