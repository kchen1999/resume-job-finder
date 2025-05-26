import React from 'react';
import { Grid, FormControl, Select, MenuItem, Checkbox, ListItemText, OutlinedInput, InputAdornment } from '@mui/material';

const DomainFilter = ({ filters, handleChange }) => {
  return (
    <Grid sx={{ width: '32%' }}>
      <FormControl fullWidth>
        <Select
          value={filters.domain || []}
          displayEmpty
          onChange={handleChange('domain')}
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
                            className="icon icon-tabler icons-tabler-outline icon-tabler-briefcase-2"
                        >
                            <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                            <path d="M3 9a2 2 0 0 1 2 -2h14a2 2 0 0 1 2 2v9a2 2 0 0 1 -2 2h-14a2 2 0 0 1 -2 -2v-9z" />
                            <path d="M8 7v-2a2 2 0 0 1 2 -2h4a2 2 0 0 1 2 2v2" />
                        </svg>
                    </InputAdornment>
                }
            />
          }
          renderValue={(selected) => {
            if (selected.length === 0) {
              return <span style={{ color: '#999' }}>Domain</span>;
            }
            return selected.join(', ');
          }}
          sx={{ height: '40px' }}
        >
          <MenuItem value="Software Engineer">
            <Checkbox checked={filters.domain.includes('Software Engineer')} />
            <ListItemText primary="Software Engineer" />
          </MenuItem>
        </Select>
      </FormControl>
    </Grid>
  )
}

export default DomainFilter
