import React from 'react'
import { Grid, FormControl, Select, MenuItem, Checkbox, ListItemText, InputAdornment, OutlinedInput  } from '@mui/material'

const ExperienceLevelFilter = ({ filters, handleChange }) => {
  return (
    <Grid sx={{ width: '32%' }}>
      <FormControl fullWidth>
        <Select
          value={filters.experience || []}
          displayEmpty
          onChange={handleChange('experience')}
          multiple
          input={
            <OutlinedInput
              startAdornment={
                <InputAdornment position="start">
                  <svg  
                    xmlns="http://www.w3.org/2000/svg"  
                    width="18"  
                    height="18"  
                    viewBox="0 0 24 24"  
                    fill="none"  
                    stroke="currentColor"  
                    strokeWidth="2"  
                    strokeLinecap="round"  
                    strokeLinejoin="round"  
                    className="icon icon-tabler icons-tabler-outline icon-tabler-military-rank"
                  >
                    <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                    <path d="M18 7v12a2 2 0 0 1 -2 2h-8a2 2 0 0 1 -2 -2v-12l6 -4z" />
                    <path d="M10 13l2 -1l2 1" />
                    <path d="M10 17l2 -1l2 1" />
                    <path d="M10 9l2 -1l2 1" />
                  </svg>
                </InputAdornment>
              }
            />
          }
          renderValue={(selected) => {
            if (selected.length === 0) {
              return <span style={{ color: '#999' }}>Experience Level</span>;
            }
            return selected.join(', ');
          }}
          sx={{ height: '40px' }}
        >
          {['Intern', 'Junior', 'Mid / Senior', 'Lead+'].map((level) => (
            <MenuItem key={level} value={level}>
              <Checkbox checked={filters.experience.includes(level)} />
              <ListItemText primary={level} />
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    </Grid>
  )
}

export default ExperienceLevelFilter
