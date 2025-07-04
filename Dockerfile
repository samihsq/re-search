# Multi-stage build for Railway deployment
FROM node:18-alpine as frontend-build

WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci --omit=dev
COPY frontend/ ./
RUN npm run build

# Backend stage
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    wget \
    gnupg \
    unzip \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome for Selenium
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY backend/ .

# Copy frontend build
COPY --from=frontend-build /frontend/build /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Create start script directly in the Dockerfile
RUN echo '#!/bin/bash\n\
# Start script for Railway deployment\n\
set -e\n\
\n\
echo "🚀 Starting Stanford Research Opportunities App..."\n\
\n\
# Start nginx in background (for frontend)\n\
nginx &\n\
\n\
# Wait a moment for nginx to start\n\
sleep 2\n\
\n\
# Start the FastAPI backend\n\
echo "🔧 Starting FastAPI backend..."\n\
exec uvicorn main:app --host 0.0.0.0 --port 8000' > /start.sh \
    && chmod +x /start.sh

USER app

CMD ["/start.sh"] 