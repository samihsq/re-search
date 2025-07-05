#!/bin/bash

# Stanford Research Opportunities - Environment Setup Script
# This script helps you create a .env file with secure values

set -e

echo "🔧 Stanford Research Opportunities - Environment Setup"
echo "====================================================="

# Check if .env already exists
if [ -f .env ]; then
    echo "⚠️  .env file already exists. Backing up to .env.backup"
    cp .env .env.backup
fi

echo "Creating .env file with secure default values..."

# Generate secure random values
POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
SECRET_KEY=$(openssl rand -base64 64 | tr -d "=+/" | cut -c1-50)
SCRAPING_API_KEY=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

# Create .env file
cat > .env << EOF
# Database
POSTGRES_DB=stanford_opportunities
POSTGRES_USER=postgres
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/stanford_opportunities

# API Keys
GEMINI_API_KEY=your_gemini_api_key_here
SECRET_KEY=${SECRET_KEY}
SCRAPING_API_KEY=${SCRAPING_API_KEY}

# App Configuration
ENABLE_LLM_PARSING=true
DEBUG=false

# Frontend
REACT_APP_API_URL=https://your-app-name.railway.app

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
EOF

echo "✅ .env file created successfully!"
echo ""
echo "🔐 Generated secure values:"
echo "   - POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}"
echo "   - SECRET_KEY: ${SECRET_KEY}"
echo "   - SCRAPING_API_KEY: ${SCRAPING_API_KEY}"
echo ""
echo "📝 Next steps:"
echo "1. Edit .env file and add your GEMINI_API_KEY"
echo "2. Update REACT_APP_API_URL with your Railway URL after deployment"
echo "3. Add RAILWAY_URL and SCRAPING_API_KEY to your GitHub repository secrets" 