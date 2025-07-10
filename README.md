# AI Resume Job Matcher for Entry Level Tech Roles

A resume matching platform that helps users (primarily entry level/recent graduates) find jobs based on experiences extracted from their uploaded resume using AI and vector similarity search. 

Users have the ability to filter jobs based on their experience level (intern, junior, mid/senior, lead+), posted within period (1 day ago, 3 days ago, 7 days ago), domain (software engineer roles only at this stage), and location (Sydney only at this stage). 

## Tech Stack

| Layer        | Tech                                                         |
|--------------|--------------------------------------------------------------|
| Frontend     | React + Vite + Material UI                                   |
| Backend      | Node.js (Express), Sequelize, PostgreSQL + pgvector          |
| AI & Parsing | Python (FastAPI), Playwright, Groq API (LLM), Jina Embeddings|
| Infrastructure | Docker Compose, Fly.io, Aiven (PostgreSQL), Nginx, GitHub Actions|

## Features

- Upload a resume (PDF only)
- Extract experiences from resume using LLMs 
- Find and embed matching jobs scraped from Seek.com.au
- Rank jobs based on vector similarity to selected resume experiences
- Logging and monitoring via Sentry
- Daily scrape job scheduled with GitHub Actions

---
## Development Setup

Follow these steps to run the app locally with Docker Compose.

### 1. Clone the Repo

```bash
git clone https://github.com/kchen1999/resume-job-finder.git
cd resume-job-finder
```

### 2. Create a .env file in the project root

Include environment variables for all services in a single .env file like this:

```ini
GROQ_API_KEY=your_groq_key
SENTRY_DSN=your_sentry_dsn
DATABASE_URL=your_postgres_url
```

### 3. Create a .env file in the frontend directory

Include the following environment variable in a single .env file like this:

```ini
VITE_NODE_BACKEND_URL=https://node-backend-proud-wildflower-5990.fly.dev/api 
```

### 4. Start the app using Docker Compose

```bash
docker compose -f docker-compose.dev.yml -p dev up --build
```
Open the app at: http://localhost:8081

### 5. Resume Upload Workflow

- Drag-and-drop a PDF resume into the UI
- LLM extracts structured experiences from the resume
- Each experience is embedded
- Resume is matched to scraped jobs based on vector similarity

The first extracted experience is used for matching by default. You can select others and filter by extracted experiences.

## Testing

This project includes both unit and integration tests for the Python backend.

### Unit Tests
Located in: `python_backend/tests/unit`

Run all unit tests (182 in total) locally at once:
```bash
cd python_backend
pytest tests/unit
```

### Integration Tests (Scraper)
Located in: `python_backend/tests/integration/`

Run an individual test locally (example below)
```bash
cd python_backend/tests/integration
pytest pages/test_early_termination.py
```

## LLM Job Extraction Integration Test

This project also includes a rigorous integration test that verifies the **accuracy of job field extraction** from markdown using an LLM parser. It ensures that structured fields like `description`, `responsibilities`, `requirements`, etc., are correctly parsed and match expected values.

### What It Checks

- Description similarity (fuzzy + semantic)
- Responsibilities match
- Requirements match
- Experience level classification
- Work model inference (e.g., remote, onsite)

Run locally:
```bash
cd python_backend
pytest tests/integration/llm/test_llm_parser_main.py
```
### Output summary

After execution, the test writes a summary report (JSON) that includes average match scores and standard deviations across multiple test runs. Example (not actual format): 

```json
{
  "timestamp": "2025-07-08T21:48:00+10:00",
  "num_runs": 3,
  "total_tests_run": 30,
  "averages": {
    "avg_desc_score": 92.7,
    "avg_resp_score": 88.3,
    "avg_req_score": 90.1,
    "exp_match_rate": 96.7,
    "work_model_match_rate": 93.3
  }, 
  "stddevs": {
    "avg_desc_score": 0.84,
    "avg_resp_score": 3.5,
    "avg_req_score": 4.52,
    "exp_match_rate": 7.5434,
    "work_model_match_rate": 2.80
  },
}
```
---
## Production Deployment

This project is deployed to Fly.io with each service running independently:

### Frontend 
[https://frontend-falling-forest-6159.fly.dev](https://frontend-falling-forest-6159.fly.dev)  
Serves the UI where users can upload resumes and explore matched jobs.

### Python Backend 
[https://python-backend-cold-feather-2329.fly.dev](https://python-backend-cold-feather-2329.fly.dev)  
Handles resume parsing, scraping job data, and calling AI services.

### Node.js Backend 
[https://node-backend-proud-wildflower-5990.fly.dev](https://node-backend-proud-wildflower-5990.fly.dev)  
Stores and serves structured job listings, matches resumes to jobs, and exposes REST endpoints.

Each service is deployed independently using its own `fly.toml`.  
See the corresponding `frontend/`, `python_backend/`, and `node-backend/` folders for Dockerfiles and deployment configuration.  

### 🔁 Daily Cron Job

Job scraping from Seek.com.au runs daily at midnight via GitHub Actions

### 🔁 Daily Integration Test (one page)

A GitHub Actions workflow runs daily executing the full integration test of one jobs listing page (22 jobs) to ensure the scraping pipeline still functions before the daily job scraping at midnight. This helps detect:

- Broken DOM selectors  (e.g., site layout changes)
- LLM parsing errors resulting in incomplete or malformed job data
- Missing required metadata such as title, location, or company

### 🔒 Security

- The /cron-daily-scrape endpoint is protected via bearer token
- Uploaded resume files are automatically deleted after parsing



