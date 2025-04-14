import { useState } from "react";
import axios from "axios";
import ResumeDropzone from "./ResumeDropzone";
import JobResults from "./JobResults";

const ResumeAnalyzer = () => {
  const [file, setFile] = useState(null);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (uploadedFile) => {
    const fileToUse = uploadedFile || file;
    if (!fileToUse) {
        alert("Please upload a resume before submitting.");
        return; 
    };

    setLoading(true);
    const formData = new FormData();
    formData.append("resume", fileToUse);

    try {
      const res = await axios.post("http://localhost:5000/api/resume/upload", formData);
      setResults(res.data.matchedJobs);
    } catch (err) {
      alert("Something went wrong.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <form onSubmit={handleSubmit}>
        <ResumeDropzone file={file} setFile={(newFile) => {
            setFile(newFile);
            if (newFile) {
                handleSubmit(newFile); // trigger upload when file is selected
            }}} loading={loading} />
      </form>
      <JobResults results={results} />
    </>
  );
};

export default ResumeAnalyzer;
