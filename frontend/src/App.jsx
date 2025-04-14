import { Container, Typography } from "@mui/material";
import ResumeAnalyzer from "./components/ResumeAnalyzer";

function App() {
  return (
    <Container maxWidth="md" sx={{ mt: 6 }}>
      <Typography variant="h4" align="center" gutterBottom>
        Smart Resume Analyzer
      </Typography>
      <ResumeAnalyzer />
    </Container>
  );
}

export default App;

