# Use official Python slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /usr/src/app

# Copy requirements.txt only for caching
COPY requirements.txt .

# Install production dependencies only
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source files
COPY . .

# Expose port 5000
EXPOSE 5000

# Run FastAPI with uvicorn, no reload in production
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]
