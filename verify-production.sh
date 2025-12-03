#!/bin/bash

# Production Readiness Verification Script
# This script checks if the ZooLingo application is ready for production deployment

set -e

echo "🔍 ZooLingo Production Readiness Check"
echo "======================================"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

# Function to print success
success() {
    echo -e "${GREEN}✓${NC} $1"
}

# Function to print error
error() {
    echo -e "${RED}✗${NC} $1"
    ((ERRORS++))
}

# Function to print warning
warning() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

# Check 1: Environment file exists
echo "📋 Checking Configuration..."
if [ -f "backend/.env" ]; then
    success "Environment file exists"
    
    # Check for required variables
    if grep -q "MURF_API_KEY=" backend/.env && ! grep -q "MURF_API_KEY=your" backend/.env; then
        success "MURF_API_KEY is configured"
    else
        error "MURF_API_KEY is not properly configured"
    fi
    
    if grep -q "ENVIRONMENT=" backend/.env; then
        success "ENVIRONMENT variable is set"
    else
        warning "ENVIRONMENT variable not set (will default to development)"
    fi
else
    error "backend/.env file not found"
fi
echo ""

# Check 2: Docker is installed
echo "🐳 Checking Docker..."
if command -v docker &> /dev/null; then
    success "Docker is installed ($(docker --version))"
else
    error "Docker is not installed"
fi

if command -v docker-compose &> /dev/null; then
    success "Docker Compose is installed ($(docker-compose --version))"
else
    error "Docker Compose is not installed"
fi
echo ""

# Check 3: Required files exist
echo "📁 Checking Project Structure..."
required_files=(
    "backend/app.py"
    "backend/config.py"
    "backend/requirements.txt"
    "backend/Dockerfile"
    "frontend/package.json"
    "frontend/Dockerfile"
    "docker-compose.yml"
    "README.md"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        success "$file exists"
    else
        error "$file is missing"
    fi
done
echo ""

# Check 4: Test files exist
echo "🧪 Checking Tests..."
if [ -f "backend/tests/test_api.py" ]; then
    success "API tests exist"
else
    warning "API tests not found"
fi

if [ -f "backend/tests/test_services.py" ]; then
    success "Service tests exist"
else
    warning "Service tests not found"
fi
echo ""

# Check 5: Documentation exists
echo "📚 Checking Documentation..."
if [ -f "docs/DEPLOYMENT.md" ]; then
    success "Deployment guide exists"
else
    warning "Deployment guide not found"
fi

if [ -f "docs/PRODUCTION_CHECKLIST.md" ]; then
    success "Production checklist exists"
else
    warning "Production checklist not found"
fi
echo ""

# Check 6: Git repository
echo "🔧 Checking Git..."
if [ -d ".git" ]; then
    success "Git repository initialized"
    
    # Check for .gitignore
    if [ -f ".gitignore" ]; then
        success ".gitignore exists"
        
        # Check if .env is in .gitignore
        if grep -q ".env" .gitignore; then
            success ".env is in .gitignore"
        else
            error ".env is NOT in .gitignore (security risk!)"
        fi
    else
        warning ".gitignore not found"
    fi
else
    warning "Not a git repository"
fi
echo ""

# Check 7: Try to build Docker images (optional, can be slow)
echo "🏗️  Docker Build Check..."
if [ "$1" == "--build" ]; then
    echo "Building Docker images..."
    if docker-compose build --quiet; then
        success "Docker images build successfully"
    else
        error "Docker build failed"
    fi
else
    warning "Skipping Docker build (use --build to test)"
fi
echo ""

# Check 8: Security checks
echo "🔒 Security Checks..."
if grep -r "api_key.*=.*['\"].*['\"]" backend/ --include="*.py" | grep -v ".env" | grep -v "your_" | grep -v "test_"; then
    error "Hardcoded API keys found in code!"
else
    success "No hardcoded API keys detected"
fi

if [ -f "backend/.env" ] && [ "$(stat -c %a backend/.env 2>/dev/null || stat -f %A backend/.env 2>/dev/null)" != "600" ]; then
    warning "backend/.env permissions are not restrictive (should be 600)"
else
    success "Environment file permissions OK"
fi
echo ""

# Summary
echo "======================================"
echo "📊 Summary"
echo "======================================"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! Your application is production-ready.${NC}"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  $WARNINGS warning(s) found. Review recommended but not critical.${NC}"
    exit 0
else
    echo -e "${RED}❌ $ERRORS error(s) and $WARNINGS warning(s) found.${NC}"
    echo -e "${RED}Please fix the errors before deploying to production.${NC}"
    exit 1
fi
