# Multi-stage build for Railway deployment
FROM node:18-alpine as frontend-build

WORKDIR /frontend
COPY frontend/package*.json ./
# Install all dependencies including dev dependencies (react-scripts is in devDependencies)
RUN npm ci
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
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Try to install Chrome (continue if it fails)
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - || true \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable || echo "Chrome installation failed, continuing without it" \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY backend/ .

# Copy frontend build
COPY --from=frontend-build /frontend/build /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Create nginx directories and set permissions
RUN mkdir -p /var/lib/nginx/body \
    && mkdir -p /var/lib/nginx/fastcgi \
    && mkdir -p /var/lib/nginx/proxy \
    && mkdir -p /var/lib/nginx/scgi \
    && mkdir -p /var/lib/nginx/uwsgi \
    && mkdir -p /var/cache/nginx \
    && mkdir -p /var/log/nginx \
    && mkdir -p /run \
    && touch /var/run/nginx.pid

# Create non-root user and set permissions
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app \
    && chown -R app:app /var/lib/nginx \
    && chown -R app:app /var/cache/nginx \
    && chown -R app:app /var/log/nginx \
    && chown -R app:app /usr/share/nginx/html \
    && chown app:app /var/run/nginx.pid \
    && chown app:app /run

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
# Check if Chrome is available\n\
if command -v google-chrome >/dev/null 2>&1; then\n\
    echo "✅ Chrome is available for JavaScript-heavy sites"\n\
else\n\
    echo "⚠️  Chrome not available - will use requests-only scraping"\n\
    export DISABLE_SELENIUM=true\n\
fi\n\
\n\
# Start the FastAPI backend on port 8001 in background\n\
echo "🔧 Starting FastAPI backend on port 8001..."\n\
uvicorn main:app --host 0.0.0.0 --port 8001 --log-level info &\n\
\n\
# Wait for backend to start\n\
sleep 5\n\
\n\
# Start nginx on port 8000 (serves frontend and proxies API)\n\
echo "🌐 Starting nginx on port 8000..."\n\
echo "📍 App will be available at http://localhost:8000"\n\
echo "📍 API will be proxied to backend at http://localhost:8001"\n\
exec nginx -g "daemon off;"' > /start.sh \
    && chmod +x /start.sh

USER app

CMD ["/start.sh"] 