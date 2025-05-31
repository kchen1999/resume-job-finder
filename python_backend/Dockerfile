# Use the official Playwright base image with Python 3.11 and all browsers pre-installed
FROM mcr.microsoft.com/playwright/python:v1.51.0-jammy

# Set working directory
WORKDIR /usr/src/app

# Install curl
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install production dependencies only
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source files
COPY . .

# Expose port 5000
EXPOSE 5000

# Run FastAPI with uvicorn, no reload in production
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]
