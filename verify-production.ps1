# Production Readiness Verification Script for Windows
# Run with: powershell -ExecutionPolicy Bypass -File verify-production.ps1

Write-Host "🔍 ZooLingo Production Readiness Check" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

$errors = 0
$warnings = 0

function Write-Success {
    param($message)
    Write-Host "✓ $message" -ForegroundColor Green
}

function Write-Error-Custom {
    param($message)
    Write-Host "✗ $message" -ForegroundColor Red
    $script:errors++
}

function Write-Warning-Custom {
    param($message)
    Write-Host "⚠ $message" -ForegroundColor Yellow
    $script:warnings++
}

# Check 1: Environment file
Write-Host "📋 Checking Configuration..." -ForegroundColor Cyan
if (Test-Path "backend\.env") {
    Write-Success "Environment file exists"
    
    $envContent = Get-Content "backend\.env" -Raw
    if ($envContent -match "MURF_API_KEY=" -and $envContent -notmatch "MURF_API_KEY=your") {
        Write-Success "MURF_API_KEY is configured"
    } else {
        Write-Error-Custom "MURF_API_KEY is not properly configured"
    }
    
    if ($envContent -match "ENVIRONMENT=") {
        Write-Success "ENVIRONMENT variable is set"
    } else {
        Write-Warning-Custom "ENVIRONMENT variable not set"
    }
} else {
    Write-Error-Custom "backend\.env file not found"
}
Write-Host ""

# Check 2: Docker
Write-Host "🐳 Checking Docker..." -ForegroundColor Cyan
try {
    $dockerVersion = docker --version
    Write-Success "Docker is installed ($dockerVersion)"
} catch {
    Write-Error-Custom "Docker is not installed"
}

try {
    $composeVersion = docker-compose --version
    Write-Success "Docker Compose is installed ($composeVersion)"
} catch {
    Write-Error-Custom "Docker Compose is not installed"
}
Write-Host ""

# Check 3: Required files
Write-Host "📁 Checking Project Structure..." -ForegroundColor Cyan
$requiredFiles = @(
    "backend\app.py",
    "backend\config.py",
    "backend\requirements.txt",
    "backend\Dockerfile",
    "frontend\package.json",
    "frontend\Dockerfile",
    "docker-compose.yml",
    "README.md"
)

foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Success "$file exists"
    } else {
        Write-Error-Custom "$file is missing"
    }
}
Write-Host ""

# Check 4: Tests
Write-Host "🧪 Checking Tests..." -ForegroundColor Cyan
if (Test-Path "backend\tests\test_api.py") {
    Write-Success "API tests exist"
} else {
    Write-Warning-Custom "API tests not found"
}

if (Test-Path "backend\tests\test_services.py") {
    Write-Success "Service tests exist"
} else {
    Write-Warning-Custom "Service tests not found"
}
Write-Host ""

# Check 5: Documentation
Write-Host "📚 Checking Documentation..." -ForegroundColor Cyan
if (Test-Path "docs\DEPLOYMENT.md") {
    Write-Success "Deployment guide exists"
} else {
    Write-Warning-Custom "Deployment guide not found"
}

if (Test-Path "docs\PRODUCTION_CHECKLIST.md") {
    Write-Success "Production checklist exists"
} else {
    Write-Warning-Custom "Production checklist not found"
}
Write-Host ""

# Check 6: Git
Write-Host "🔧 Checking Git..." -ForegroundColor Cyan
if (Test-Path ".git") {
    Write-Success "Git repository initialized"
    
    if (Test-Path ".gitignore") {
        Write-Success ".gitignore exists"
        
        $gitignoreContent = Get-Content ".gitignore" -Raw
        if ($gitignoreContent -match "\.env") {
            Write-Success ".env is in .gitignore"
        } else {
            Write-Error-Custom ".env is NOT in .gitignore (security risk!)"
        }
    } else {
        Write-Warning-Custom ".gitignore not found"
    }
} else {
    Write-Warning-Custom "Not a git repository"
}
Write-Host ""

# Check 7: Security
Write-Host "🔒 Security Checks..." -ForegroundColor Cyan
$hardcodedKeys = Get-ChildItem -Path "backend" -Filter "*.py" -Recurse | 
    Select-String -Pattern "api_key.*=.*['\`"].*['\`"]" | 
    Where-Object { $_.Line -notmatch "\.env" -and $_.Line -notmatch "your_" -and $_.Line -notmatch "test_" }

if ($hardcodedKeys) {
    Write-Error-Custom "Hardcoded API keys found in code!"
} else {
    Write-Success "No hardcoded API keys detected"
}
Write-Host ""

# Summary
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "📊 Summary" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

if ($errors -eq 0 -and $warnings -eq 0) {
    Write-Host "✅ All checks passed! Your application is production-ready." -ForegroundColor Green
    exit 0
} elseif ($errors -eq 0) {
    Write-Host "⚠️  $warnings warning(s) found. Review recommended but not critical." -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "❌ $errors error(s) and $warnings warning(s) found." -ForegroundColor Red
    Write-Host "Please fix the errors before deploying to production." -ForegroundColor Red
    exit 1
}
