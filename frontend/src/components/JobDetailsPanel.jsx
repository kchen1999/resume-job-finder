import React from 'react';
import { Avatar, Box, Typography, Chip, Button } from '@mui/material';
import CircleIcon from '@mui/icons-material/Circle';

const JobDetailsPanel = ({ job }) => {
  if (!job) {
    return (
      <Box sx={{ width: '100%', backgroundColor: '#f5f5f5', p: 2, boxShadow: 3}}>
        <Typography variant="body2" color="text.secondary">No jobs available.</Typography>
      </Box>
    )
  }

  return (
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
        {!job.logo_link && (
          <Avatar 
            alt="Company Logo" 
            src={job.logo_link || undefined} 
            sx={{ 
              width: 59, 
              height: 59, 
              bgcolor: !job.logo_link ? '#f7c6b2' : undefined,
              img: {
                objectFit: 'contain',
                width: '96%',
                height: '96%',
            }}} // Circular logo
          >
          {!job.logo_link && job.company?.[0]?.toUpperCase()}
          </Avatar>     
        )}

        {/* Title and Company */}
        <Typography variant="h5" fontWeight={600}>{job.title}</Typography>
        <Typography variant="subtitle1" color="text.secondary" mb={2}>{job.company}</Typography>

        {/* Tags */}
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
          {job.salary 
            ? <Chip 
                label={job.salary} 
                color="default" 
                sx={ { borderRadius: 2} }
                icon={
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    width="18"
                    height="18"
                    strokeWidth="2"
                  >
                    <path d="M12 12m-3 0a3 3 0 1 0 6 0a3 3 0 1 0 -6 0"></path>
                    <path d="M3 6m0 2a2 2 0 0 1 2 -2h14a2 2 0 0 1 2 2v8a2 2 0 0 1 -2 2h-14a2 2 0 0 1 -2 -2z"></path>
                    <path d="M18 12l.01 0"></path>
                    <path d="M6 12l.01 0"></path>
                  </svg>
                }
              />
            : <Chip 
                label="No salary specified"
                color="default" 
                sx={ { borderRadius: 2} }
                icon={
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    width="18"
                    height="18"
                    strokeWidth="2"
                  >
                    <path d="M12 12m-3 0a3 3 0 1 0 6 0a3 3 0 1 0 -6 0"></path>
                    <path d="M3 6m0 2a2 2 0 0 1 2 -2h14a2 2 0 0 1 2 2v8a2 2 0 0 1 -2 2h-14a2 2 0 0 1 -2 -2z"></path>
                    <path d="M18 12l.01 0"></path>
                    <path d="M6 12l.01 0"></path>
                  </svg>
                }
              />
            } 
          {job.posted_within && 
            <Chip 
              label={job.posted_within} 
              sx={ { borderRadius: 2} }
              icon={
                <svg 
                  xmlns="http://www.w3.org/2000/svg" 
                  viewBox="0 0 24 24" 
                  fill="none" 
                  stroke="currentColor" 
                  stroke-linecap="round" 
                  stroke-linejoin="round" 
                  width="18" 
                  height="18" 
                  stroke-width="2"
                >
                  <path d="M11.795 21h-6.795a2 2 0 0 1 -2 -2v-12a2 2 0 0 1 2 -2h12a2 2 0 0 1 2 2v4"></path>
                  <path d="M18 18m-4 0a4 4 0 1 0 8 0a4 4 0 1 0 -8 0"></path>
                  <path d="M15 3v4"></path>
                  <path d="M7 3v4"></path>
                  <path d="M3 11h16"></path>
                  <path d="M18 16.496v1.504l1 1"></path>
                </svg>
              }
            />
          }
          {job.location && 
            <Chip 
              label={job.location} 
              sx={ { borderRadius: 2} }
              icon={
                <svg 
                  xmlns="http://www.w3.org/2000/svg" 
                  viewBox="0 0 24 24" 
                  fill="none" 
                  stroke="currentColor" 
                  stroke-linecap="round" 
                  stroke-linejoin="round" 
                  width="18" 
                  height="18" 
                  stroke-width="2"
                >
                  <path d="M9 11a3 3 0 1 0 6 0a3 3 0 0 0 -6 0"></path>
                  <path d="M17.657 16.657l-4.243 4.243a2 2 0 0 1 -2.827 0l-4.244 -4.243a8 8 0 1 1 11.314 0z"></path>
                </svg>
              }
            />
          }
        </Box>
        <Box>
        {job.classification &&
          <Chip 
            sx={{
              height: 'auto', // allow Chip to grow in height
              '& .MuiChip-label': {
                display: 'block', // make label block so it wraps
                whiteSpace: 'normal', // allow normal wrapping
                wordBreak: 'break-word', 
                overflowWrap: 'break-word',
                paddingTop: '8px', // optional nicer padding
                paddingBottom: '8px',
                borderRadius: 2,
              }
            }}
            label={job.classification}
            icon={
              <svg 
                xmlns="http://www.w3.org/2000/svg" 
                viewBox="0 0 24 24" 
                fill="none" 
                stroke="currentColor" 
                stroke-linecap="round" 
                stroke-linejoin="round" 
                width="18" 
                height="18" 
                stroke-width="2"
              > 
                <path d="M3 21l18 0"></path> 
                <path d="M9 8l1 0"></path> 
                <path d="M9 12l1 0"></path> 
                <path d="M9 16l1 0"></path>
                <path d="M14 8l1 0"></path> 
                <path d="M14 12l1 0"></path> 
                <path d="M14 16l1 0"></path> 
                <path d="M5 21v-16a2 2 0 0 1 2 -2h10a2 2 0 0 1 2 2v16">
                </path> 
              </svg> 
            }
          />
        }
        </Box>
        
        {/* Job Button */}
        {job.job_url && (
          <Box sx={{ display: 'flex', mb: 3, mt: 2, gap: 1 }}>
            <Button
              variant="contained"
              href={job.quick_apply_url}
              target="_blank"
              rel="noopener"
              sx={{ 
                textTransform: 'none' ,
                px: 1.5, // horizontal padding
                py: 0.4, // vertical padding
                backgroundColor: '#b85c8e',
                fontWeight: 'bold',
                color: 'white'
              }}
            >
              Apply Now
            </Button>
            <Button
              variant="contained"
              href={job.job_url}
              target="_blank"
              rel="noopener"
              sx={{ 
                textTransform: 'none' ,
                px: 1.5, // horizontal padding
                py: 0.4, // vertical padding
                backgroundColor: 'transparent',
                border: '1px solid #D1D5DB',
                fontWeight: 'bold',
                color: '#374151'
              }}
            >
              See Job
            </Button>
          </Box>
        )}

        {/* Description */}
        {job.description && (
          <Box sx={{ mb: 3}}>
            <Typography variant="body1">{job.description}</Typography>
          </Box>
        )}

        {/* Requirements */}
        {job.requirements?.length > 0 && (
          <Box sx={{ mb: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 'bold' }} gutterBottom>Requirements</Typography>
            <ul>
              {job.requirements.map((item, index) => (
                <li key={index} style={{ display: 'flex', alignItems: 'start', gap: 8 }}>
                  <CircleIcon sx={{ fontSize: 8, mt: '6px', color: '#bbb' }} />
                  <Typography variant="body1" sx={{ mb: 1}}>{item}</Typography>
                </li>
              ))}
            </ul>
          </Box>
        )}

        {/* Responsibilities */}
        {job.responsibilities?.length > 0 && (
          <Box sx={{ mb: 3 }}>
            <Typography variant="h6" gutterBottom sx={{ mt: 2, fontWeight: 'bold' }}>Responsibilities</Typography>
            <ul>
              {job.responsibilities.map((item, index) => (
                <li key={index} style={{ display: 'flex', alignItems: 'start', gap: 8 }}>
                  <CircleIcon sx={{ fontSize: 8, mt: '6px', color: '#bbb' }} />
                  <Typography variant="body1" sx={{ mb: 1 }}>{item}</Typography>
                </li>
              ))}
            </ul>
          </Box>
        )}

        {/* Other */}
        {job.other?.length > 0 && (
          <Box sx={{ mb: 3 }}>
            <Typography variant="h6" gutterBottom sx={{ mt: 2, fontWeight: 'bold' }}>Other</Typography>
            <ul>
              {job.other.map((item, index) => (
                <li key={index} style={{ display: 'flex', alignItems: 'start', gap: 8 }}>
                  <CircleIcon sx={{ fontSize: 8, mt: '6px', color: '#bbb' }} />
                  <Typography variant="body1" sx={{ mb: 1 }}>{item}</Typography>
                </li>
              ))}
            </ul>
          </Box>
        )}
      </Box>
    </Box>
  )
}

export default JobDetailsPanel;


