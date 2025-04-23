import { Box, FormControl, InputLabel, MenuItem, Select, Checkbox, ListItemText } from '@mui/material';
import Grid from '@mui/material/Grid';

const JobFilters = ({ filters, setFilters }) => {
  const handleChange = (field) => (event) => {
    setFilters((prev) => ({
      ...prev,
      [field]: event.target.value,
    }));
  };

  const getPostedLabel = (val) => {
    switch (val) {
      case '1': return '1 day ago';
      case '3': return '3 days ago';
      case '7': return '7 days ago';
      case '14': return '14 days ago';
      case '21': return '21 days ago';
      default: return '';
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column'}}>
        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'space-between', width: '100%'}}>
        {/* Experience Level Section */}
        <Grid sx={{ width: '32%' }}>
            <FormControl fullWidth>
            <Select
                value={filters.experience || []}  // Use an array to store multiple selected values
                displayEmpty
                onChange={handleChange('experience')}
                multiple // Enable multiple selections
                renderValue={(selected) => {
                    if (selected.length === 0) {
                      return <span style={{ color: '#999' }}>Experience Level</span>;
                    }
                    return selected.join(', ');
                  }}
                sx={{ height: '40px' }}
            >
            <MenuItem value="Intern">
                <Checkbox checked={filters.experience.includes('Intern')} />
                <ListItemText primary="Intern" />
            </MenuItem>
            <MenuItem value="Junior">
                <Checkbox checked={filters.experience.includes('Junior')} />
                <ListItemText primary="Junior" />
            </MenuItem>
            <MenuItem value="Mid">
                <Checkbox checked={filters.experience.includes('Mid')} />
                <ListItemText primary="Mid" />
            </MenuItem>
            <MenuItem value="Senior">
                <Checkbox checked={filters.experience.includes('Senior')} />
                <ListItemText primary="Senior" />
            </MenuItem>
            <MenuItem value="Lead">
                <Checkbox checked={filters.experience.includes('Lead')} />
                <ListItemText primary="Lead" />
            </MenuItem>
            </Select>
            </FormControl>
        </Grid>
    
        {/* Posted Within Section */}
        <Grid sx={{ width: '32%' }}>
        <FormControl fullWidth>
            <Select
            value={filters.posted || ''}
            displayEmpty
            onChange={handleChange('posted')}
            renderValue={(selected) => {
                if (!selected) {
                return <span style={{ color: '#999' }}>Posted Within</span>;
                }
                return getPostedLabel(selected);  // Helper for cleaner labels
            }}
            sx={{ height: '40px' }}
            >
            <MenuItem value="1">1 day ago</MenuItem>
            <MenuItem value="3">3 days ago</MenuItem>
            <MenuItem value="7">7 days ago</MenuItem>
            <MenuItem value="14">14 days ago</MenuItem>
            <MenuItem value="21">21 days ago</MenuItem>
            </Select>
        </FormControl>
        </Grid>
    
        {/* Domain Section */}
        <Grid sx={{ width: '32%' }}>
            <FormControl fullWidth>
                <Select
                    value={filters.domain || []}  // Use an array to store multiple selections (if needed)
                    displayEmpty
                    onChange={handleChange('domain')}
                    multiple
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
        </Box>
        <Box sx={{ mt: 1.5, mb: 3, display: 'flex', justifyContent: 'space-between' }}>
            {/* Location Section */}
            <Grid sx={{ width: '32%' }}>
                <FormControl fullWidth>
                    <Select
                        value={filters.location || []}  // Use an array to store multiple selected values (even though there’s only one for now)
                        displayEmpty
                        onChange={handleChange('location')}
                        multiple  // Enable multiple selections (though only one option for now)
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
        </Box>  
    </Box>
   
  );
};

export default JobFilters;

