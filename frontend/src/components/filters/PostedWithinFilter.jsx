import React from 'react';
import { Grid, FormControl, Select, MenuItem, InputAdornment, OutlinedInput } from '@mui/material';

const PostedWithinFilter = ({ filters, handleChange, getPostedLabel }) => {
  return (
    <Grid sx={{ width: '32%' }}>
      <FormControl fullWidth>
        <Select
          value={filters.posted || ''}
          displayEmpty
          onChange={handleChange('posted')}
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
                            className="icon icon-tabler icons-tabler-outline icon-tabler-calendar"
                        >
                        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                        <path d="M4 7a2 2 0 0 1 2 -2h12a2 2 0 0 1 2 2v12a2 2 0 0 1 -2 2h-12a2 2 0 0 1 -2 -2v-12z" />
                        <path d="M16 3v4" />
                        <path d="M8 3v4" />
                        <path d="M4 11h16" />
                        <path d="M11 15h1" />
                        <path d="M12 15v3" />
                        </svg>
                    </InputAdornment>
                }
            />
          }
          renderValue={(selected) => {
            if (!selected) {
              return <span style={{ color: '#999' }}>Posted Within</span>;
            }
            return getPostedLabel(selected);
          }}
          sx={{ height: '40px' }}
        >
          <MenuItem value="1">1 day ago</MenuItem>
          <MenuItem value="3">3 days ago</MenuItem>
          <MenuItem value="7">7 days ago</MenuItem>
        </Select>
      </FormControl>
    </Grid>
  )
}

export default PostedWithinFilter
