import { Box } from '@mui/material'
import ExperienceLevelFilter from './ExperienceLevelFilter'
import PostedWithinFilter from './PostedWithinFilter'
import DomainFilter from './DomainFilter'
import LocationFilter from './LocationFilter'

const JobFilters = ({ filters, setFilters }) => {
  const handleChange = (field) => (event) => {
    setFilters((prev) => ({
      ...prev,
      [field]: event.target.value,
    }))
  }

  const getPostedLabel = (val) => {
    switch (val) {
      case '1': return '1 day ago'
      case '3': return '3 days ago'
      case '7': return '7 days ago'
      default: return ''
    }
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column'}}>
      <Box sx={{ mt: 3, display: 'flex', justifyContent: 'space-between', width: '100%'}}>
        <ExperienceLevelFilter filters={filters} handleChange={handleChange} />
        <PostedWithinFilter filters={filters} handleChange={handleChange} getPostedLabel={getPostedLabel} />
        <DomainFilter filters={filters} handleChange={handleChange} />
      </Box>
      <Box sx={{ mt: 1.5, mb: 3, display: 'flex', justifyContent: 'space-between' }}>
        <LocationFilter filters={filters} handleChange={handleChange} />
      </Box>  
    </Box>
  )
}

export default JobFilters

