#!/bin/bash

# Start script for Railway deployment
set -e

echo "🚀 Starting Stanford Research Opportunities App..."

# Start nginx in background (for frontend)
nginx &

# Wait a moment for nginx to start
sleep 2

# Start the FastAPI backend
echo "🔧 Starting FastAPI backend..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 