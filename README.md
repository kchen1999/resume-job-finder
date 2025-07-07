# 🧠 AI Resume Job Matcher

A resume matching platform that helps users find jobs based on experiences extracted from their uploaded resume using AI and vector similarity search. 

## 🧩 Tech Stack

| Layer        | Tech                                                         |
|--------------|--------------------------------------------------------------|
| Frontend     | React + Vite + Material UI                                   |
| Backend      | Node.js (Express), Sequelize, PostgreSQL + pgvector          |
| AI & Parsing | Python (FastAPI), Playwright, Groq API (LLM), Jina Embeddings|
| Infrastructure | Docker Compose, Fly.io, Aiven (PostgreSQL), Nginx, GitHub Actions|

## 🔧 Features

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

Include environment variables for all services in a single .env file like:

```ini
GROQ_API_KEY=your_groq_key
JINA_API_KEY=your_jina_key
SENTRY_DSN=your_sentry_dsn

DATABASE_URL=your_postgres_url
NODE_BACKEND_URL=http://node-backend:3000/api
SCRAPER_BEARER_TOKEN=supersecrettoken
```

### 3. Start the app using Docker Compose

```bash
docker compose -f docker-compose.dev.yml -p dev up --build
```
Open the app at: http://localhost:8081

### 4. 📤 Resume Upload Workflow

- Drag-and-drop a PDF resume into the UI
- LLM extracts structured experiences from the resume
- Each experience is embedded
- Resume is matched to scraped jobs based on vector similarity

The first extracted experience is used for matching by default. You can select others and filter by extracted experiences.

---
## Production Deployment

This project is deployed to Fly.io for: 
- Python backend: https://python-backend-cold-feather-2329.fly.dev
- Node.js backend: https://node-backend-proud-wildflower-5990.fly.dev

Each service is deployed independently via its own `fly.toml`. See individual folders for deployment details.

### 🔁 Daily Cron Job

Job scraping from Seek.com.au runs daily via GitHub Actions. 

### 🔒 Security

- The /cron-daily-scrape endpoint is protected via bearer token
- Uploaded resume files are automatically deleted after parsing



