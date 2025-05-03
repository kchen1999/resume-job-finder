import { Container, Typography } from "@mui/material";
import ResumeAnalyzer from "./components/ResumeAnalyzer";

function App() {
  return (
    <Container maxWidth="lg" sx={{ mt: 6 }}>
      <Typography variant="h4" align="center" gutterBottom>
        ResumeMatcher AI
      </Typography>
      <ResumeAnalyzer />
    </Container>
  );
}

export default App;

