import React from 'react';
import { Box, Typography, Divider, Link, Chip, Button } from '@mui/material';

const JobDetail = ({ job }) => {
  if (!job) {
    return (
      <Box
        sx={{
          width: '100%',
          backgroundColor: '#f5f5f5',
          p: 2,
          borderRadius: 2,
          boxShadow: 3,
        }}
      >
        <Typography variant="body2" color="text.secondary">
          Select a job from the list to view details.
        </Typography>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        width: '100%',
        boxSizing: 'border-box',
        backgroundColor: '#ffffff',
        p: 3,
        borderRadius: 3,
        boxShadow: 3,
        wordBreak: 'break-word',
        overflowWrap: 'break-word',
      }}
    >
      {/* Logo */}
      {job.logo_link && (
        <Box sx={{ mb: 2 }}>
          <Box
            component="img"
            src={job.logo_link}
            alt=""
            sx={{
              height: 50,
              objectFit: 'contain',
              maxWidth: '100%',
            }}
          />
        </Box>
      )}

      {/* Title and Company */}
      <Typography variant="h5" fontWeight={600}>
        {job.title}
      </Typography>
      <Typography variant="subtitle1" color="text.secondary" mb={2}>
        {job.company}
      </Typography>

      {/* Tags */}
      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
        {job.salary && <Chip label={job.salary} color="success" />}
        {job.posted_date && <Chip label={job.posted_within} />}
        {job.location && <Chip label={job.location} />}
      </Box>

      {/* See Job Button */}
      {job.job_url && (
        <Box sx={{ mb: 3 }}>
          <Button
            variant="contained"
            color="primary"
            href={job.job_url}
            target="_blank"
            rel="noopener"
            sx={{ 
              textTransform: 'none' ,
              px: 1.5, // horizontal padding
              py: 0.4, // vertical padding
            }}
          >
            See Job
          </Button>
        </Box>
      )}

      {/* Description */}
      {job.description && (
        <Box sx={{ mb: 3}}>
          <Typography variant="body1">
            {job.description}
          </Typography>
        </Box>
      )}

      {/* Requirements */}
      {job.requirements?.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Requirements
          </Typography>
          <ul>
            {job.requirements.map((item, index) => (
              <li key={index}>
                <Typography variant="body1" sx={{ mb: 1}}>{item}</Typography>
              </li>
            ))}
          </ul>
        </Box>
      )}

      {/* Responsibilities */}
      {job.responsibilities?.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
            Responsibilities
          </Typography>
          <ul>
            {job.responsibilities.map((item, index) => (
              <li key={index}>
                <Typography variant="body1" sx={{ mb: 1 }}>{item}</Typography>
              </li>
            ))}
          </ul>
        </Box>
      )}

      {/* Other */}
      {job.other?.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
            Other
          </Typography>
          <ul>
            {job.other.map((item, index) => (
              <li key={index}>
                <Typography variant="body1" sx={{ mb: 1 }}>{item}</Typography>
              </li>
            ))}
          </ul>
        </Box>
      )}
    </Box>
  );
};

export default JobDetail;


