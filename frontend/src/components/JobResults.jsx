import { Box, Typography, Card, CardContent, Link } from "@mui/material";
  
const JobResults = ({ results }) => {
    if (!results || results.length === 0) {
        return null;
    }
    console.log("Results: ");
    console.log(results);
    return (
      <Box mt={6}>
        <Typography variant="h5" gutterBottom>
          Top Matching Jobs
        </Typography>
        {results.map((job, i) => (
          <Card key={i} variant="outlined" sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="h6">{job.title}</Typography>
              <Typography variant="body2" color="text.secondary">
                {job.company}
              </Typography>
              <Link href={job.job_url} target="_blank" rel="noopener">
                View Job
              </Link>
            </CardContent>
          </Card>
        ))}
      </Box>
    );
  };
  
export default JobResults;
  