# Use official Python slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /usr/src/app

# Install system dependencies needed by Playwright browsers and playwright CLI
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libxss1 \
    libxcomposite1 \
    libxdamage1 \
    libgbm1 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libxcb1 \
    libx11-xcb1 \
    libxcb-dri3-0 \
    libxcb-dri2-0 \
    libdrm2 \
    libxrandr2 \
    libasound2 \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install production dependencies only
RUN pip install --no-cache-dir -r requirements.txt

# Install the Playwright browsers and dependencies
RUN playwright install --with-deps

# Copy all source files
COPY . .

# Expose port 5000
EXPOSE 5000

# Run FastAPI with uvicorn, no reload in production
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]
