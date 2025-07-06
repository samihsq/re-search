#!/bin/bash

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if AWS CLI is installed
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if CDK is installed
    if ! command -v cdk &> /dev/null; then
        log_error "AWS CDK is not installed. Please install it first."
        log_info "Run: npm install -g aws-cdk"
        exit 1
    fi
    
    # Check if Python is available
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Setup environment
setup_environment() {
    log_info "Setting up deployment environment..."
    
    # Set deployment stage
    export STAGE=${STAGE:-"prod"}
    log_info "Deployment stage: $STAGE"
    
    # Check for required environment variables
    if [ -f ".env" ]; then
        log_info "Loading environment variables from .env file"
        source .env
    else
        log_warning "No .env file found. Make sure DATABASE_URL and other secrets are set."
    fi
    
    # Verify AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Run 'aws configure' first."
        exit 1
    fi
    
    AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
    AWS_REGION=${AWS_DEFAULT_REGION:-"us-west-2"}
    
    export CDK_DEFAULT_ACCOUNT=$AWS_ACCOUNT
    export CDK_DEFAULT_REGION=$AWS_REGION
    
    log_success "Using AWS Account: $AWS_ACCOUNT"
    log_success "Using AWS Region: $AWS_REGION"
}

# Install dependencies
install_dependencies() {
    log_info "Installing CDK dependencies..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "cdk_venv" ]; then
        python3 -m venv cdk_venv
        log_success "Created CDK virtual environment"
    fi
    
    # Activate virtual environment
    source cdk_venv/bin/activate
    
    # Install dependencies
    pip install --upgrade pip
    pip install -r cdk_requirements.txt
    
    log_success "CDK dependencies installed"
}

# Prepare Lambda package
prepare_lambda_package() {
    log_info "Preparing Lambda deployment package..."
    
    # Remove old package if exists
    if [ -d "lambda_package" ]; then
        rm -rf lambda_package
    fi
    
    # Create new package directory
    mkdir -p lambda_package
    
    # Copy backend application
    cp -r backend/ lambda_package/
    
    # Copy lambda handler
    cp lambda_handler.py lambda_package/
    
    # Copy requirements
    cp lambda_requirements.txt lambda_package/
    
    log_success "Lambda package prepared"
}

# Bootstrap CDK (if needed)
bootstrap_cdk() {
    log_info "Checking CDK bootstrap status..."
    
    # Check if already bootstrapped
    if aws cloudformation describe-stacks --stack-name CDKToolkit --region $AWS_REGION &> /dev/null; then
        log_success "CDK already bootstrapped in $AWS_REGION"
    else
        log_info "Bootstrapping CDK in $AWS_REGION..."
        cdk bootstrap aws://$AWS_ACCOUNT/$AWS_REGION
        log_success "CDK bootstrapped successfully"
    fi
}

# Deploy stack
deploy_stack() {
    log_info "Deploying Stanford Research API stack..."
    
    # Synthesize the stack first
    log_info "Synthesizing CDK app..."
    cdk synth
    
    # Deploy with automatic approval
    log_info "Deploying to AWS..."
    cdk deploy --require-approval never --outputs-file cdk-outputs.json
    
    log_success "Stack deployed successfully!"
}

# Display deployment results
show_results() {
    log_info "Deployment Results:"
    echo "===================="
    
    if [ -f "cdk-outputs.json" ]; then
        # Extract key outputs
        API_URL=$(python3 -c "
import json
with open('cdk-outputs.json') as f:
    outputs = json.load(f)
    for stack in outputs.values():
        if 'ApiUrl' in stack:
            print(stack['ApiUrl'])
            break
" 2>/dev/null || echo "")
        
        if [ ! -z "$API_URL" ]; then
            echo ""
            log_success "🌐 API URL: $API_URL"
            log_success "🏥 Health Check: ${API_URL}health"
            log_success "📊 Opportunities API: ${API_URL}api/opportunities"
            echo ""
            log_info "Test your API:"
            echo "  curl -v ${API_URL}health"
            echo ""
        fi
        
        log_info "Full outputs saved to: cdk-outputs.json"
    else
        log_warning "CDK outputs file not found"
    fi
}

# Cleanup function
cleanup() {
    if [ -d "lambda_package" ]; then
        rm -rf lambda_package
        log_info "Cleaned up temporary files"
    fi
}

# Main deployment function
main() {
    echo ""
    log_info "🚀 Stanford Research Opportunities API - CDK Deployment"
    echo "======================================================"
    echo ""
    
    # Set trap for cleanup
    trap cleanup EXIT
    
    # Run deployment steps
    check_prerequisites
    setup_environment
    install_dependencies
    prepare_lambda_package
    bootstrap_cdk
    deploy_stack
    show_results
    
    echo ""
    log_success "🎉 Deployment completed successfully!"
    echo ""
}

# Parse command line arguments
case "${1:-}" in
    "destroy")
        log_warning "Destroying stack..."
        source cdk_venv/bin/activate 2>/dev/null || true
        cdk destroy --force
        log_success "Stack destroyed"
        ;;
    "diff")
        log_info "Showing stack diff..."
        source cdk_venv/bin/activate 2>/dev/null || true
        cdk diff
        ;;
    "synth")
        log_info "Synthesizing stack..."
        source cdk_venv/bin/activate 2>/dev/null || true
        cdk synth
        ;;
    *)
        main
        ;;
esac
