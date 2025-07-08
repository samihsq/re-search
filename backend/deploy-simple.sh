#!/bin/bash

# Stanford Research Opportunities API - Simple SAM Deployment
# Uses SAM guided deployment (automatically handles S3 buckets)

set -e

echo "🚀 Stanford Research Opportunities API - Simple SAM Deployment"
echo "=============================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if SAM CLI is installed
if ! command -v sam &> /dev/null; then
    print_error "SAM CLI is not installed. Please install SAM CLI."
    print_status "Install with: pip install aws-sam-cli"
    exit 1
fi

# Check AWS credentials
print_status "Checking AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured. Please run 'aws configure' first."
    exit 1
fi

# Load environment variables from .env if it exists
if [ -f .env ]; then
    print_status "Loading environment variables from .env file..."
    export $(cat .env | grep -v '^#' | grep -v '^$' | xargs)
fi

# Validate required environment variables
print_status "Validating environment variables..."
required_vars=("DATABASE_URL" "SECRET_KEY")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    print_error "Missing required environment variables:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    print_status "Please set these variables in your .env file."
    exit 1
fi

print_success "All required environment variables are set."

# Build the SAM application
print_status "Building SAM application..."
sam build

if [ $? -ne 0 ]; then
    print_error "SAM build failed. Check the error messages above."
    exit 1
fi

print_success "SAM build completed successfully!"

# Deploy with guided setup (SAM handles S3 automatically)
print_status "Starting guided deployment..."
print_status "SAM will automatically create and manage S3 buckets for deployment artifacts."

sam deploy --guided \
    --parameter-overrides \
        DatabaseUrl="$DATABASE_URL" \
        SecretKey="$SECRET_KEY" \
        GeminiApiKey="${GEMINI_API_KEY:-}" \
        ScrapingApiKey="${SCRAPING_API_KEY:-}" \
        AllowedOrigins="${ALLOWED_ORIGINS:-https://samihsq.github.io}"

if [ $? -eq 0 ]; then
    print_success "🎉 Deployment completed successfully!"
    print_status "Your API endpoints will be displayed above in the SAM output."
    
    print_status "💡 Next time, you can deploy with just:"
    echo "  sam deploy"
    
    print_status "🧪 To test your API:"
    echo "  python test_api.py https://your-api-url"
    
    print_status "📊 To view logs:"
    echo "  sam logs -n FlaskApiFunction --tail"
    
else
    print_error "Deployment failed. Check the error messages above."
    exit 1
fi 