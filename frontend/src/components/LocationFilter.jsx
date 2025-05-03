import React from 'react';
import { Grid, FormControl, Select, MenuItem, Checkbox, ListItemText, OutlinedInput, InputAdornment } from '@mui/material';

const LocationFilter = ({ filters, handleChange }) => {
  return (
    <Grid sx={{ width: '32%' }}>
      <FormControl fullWidth>
        <Select
          value={filters.location || []}
          displayEmpty
          onChange={handleChange('location')}
          multiple
          input={
            <OutlinedInput
                startAdornment={
                    <InputAdornment position="start">
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
                    </InputAdornment>
                }
            />
          }
          renderValue={(selected) => {
            if (selected.length === 0) {
              return <span style={{ color: '#999' }}>Location</span>;
            }
            return selected.join(', ');
          }}
          sx={{ height: '40px' }}
        >
          <MenuItem value="Sydney">
            <Checkbox checked={filters.location.includes('Sydney')} />
            <ListItemText primary="Sydney" />
          </MenuItem>
        </Select>
      </FormControl>
    </Grid>
  );
};

export default LocationFilter;
