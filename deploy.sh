#!/bin/bash

# Stanford Research Opportunities - Railway Deployment Script
# This script helps you deploy your app to Railway

set -e

echo "🚀 Stanford Research Opportunities - Railway Deployment"
echo "=================================================="

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI is not installed."
    echo "Please install it first: npm install -g @railway/cli"
    echo "Then run: railway login"
    exit 1
fi

# Check if user is logged in to Railway
if ! railway whoami &> /dev/null; then
    echo "❌ You are not logged in to Railway."
    echo "Please run: railway login"
    exit 1
fi

echo "✅ Railway CLI is ready"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Running environment setup..."
    if [ -f setup-env.sh ]; then
        ./setup-env.sh
        echo ""
        echo "📝 Please edit the .env file and add your GEMINI_API_KEY, then run this script again."
        echo "You can also update REACT_APP_API_URL after getting your Railway URL."
        exit 1
    else
        echo "❌ setup-env.sh not found. Please create .env file manually."
        exit 1
    fi
fi

echo "✅ Environment variables found"

# Check if essential variables are set
if grep -q "your_gemini_api_key_here" .env; then
    echo "⚠️  Please update GEMINI_API_KEY in .env file before deploying"
    echo "You can get a Gemini API key from: https://makersuite.google.com/app/apikey"
fi

# Deploy to Railway
echo "🚀 Deploying to Railway..."
railway up

echo "✅ Deployment completed!"
echo ""
echo "📋 Next steps:"
echo "1. Go to your Railway dashboard to get your app URL"
echo "2. Update REACT_APP_API_URL in your .env file with the actual URL"
echo "3. Redeploy with: railway up"
echo "4. Add the following secrets to your GitHub repository:"
echo "   - RAILWAY_URL: Your Railway app URL"
echo "   - SCRAPING_API_KEY: The value from your .env file"
echo "5. Test the GitHub Actions workflow manually"
echo ""
echo "🔗 Useful links:"
echo "- Railway Dashboard: https://railway.app/dashboard"
echo "- GitHub Actions: https://github.com/your-username/your-repo/actions"
echo ""
echo "🎉 Your app should now be live!" 