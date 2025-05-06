import React from 'react';
import {
  Grid,
  FormControl,
  Select,
  MenuItem,
  Checkbox,
  ListItemText,
  OutlinedInput,
  InputAdornment,
} from '@mui/material';

const ResumeExperienceFilter = ({ experiences, selected, onChange }) => {
  return (
    <Grid sx={{ width: '32%' }}>
      <FormControl fullWidth>
        <Select
          value={selected}
          multiple
          displayEmpty
          onChange={onChange}
          input={
            <OutlinedInput
              startAdornment={
                <InputAdornment position="start">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    width="18"
                    height="18"
                  >
                    <path d="M16 21v-2a4 4 0 0 0-3-3.87"></path>
                    <path d="M7 9a4 4 0 1 0 4-4"></path>
                    <circle cx="12" cy="7" r="4" />
                    <path d="M6 21v-2a4 4 0 0 1 3-3.87" />
                  </svg>
                </InputAdornment>
              }
            />
          }
          renderValue={(selectedIds) => {
            if (selectedIds.length === 0) {
              return <span style={{ color: '#999' }}>Resume Experiences</span>;
            }
            return experiences
              .filter((exp) => selectedIds.includes(exp.id))
              .map((exp) => exp.title)
              .join(', ');
          }}
          sx={{ height: '40px' }}
        >
          {experiences.map((exp) => (
            <MenuItem key={exp.id} value={exp.id}>
              <Checkbox checked={selected.includes(exp.id)} />
              <ListItemText primary={exp.title} />
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    </Grid>
  );
};

export default ResumeExperienceFilter;
