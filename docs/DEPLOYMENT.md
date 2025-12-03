# ZooLingo - Production Deployment Guide

## 📋 Table of Contents
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Local Development](#local-development)
- [Production Deployment](#production-deployment)
- [Monitoring & Maintenance](#monitoring--maintenance)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software
- **Docker** (v20.10+) & **Docker Compose** (v2.0+)
- **Git**
- **API Keys**:
  - Murf AI API Key (Required)
  - Deepgram API Key (Optional)

### System Requirements
- **CPU**: 2+ cores recommended
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 10GB free space
- **OS**: Linux, macOS, or Windows with WSL2

## Environment Setup

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/zoolingo.git
cd zoolingo
```

### 2. Configure Environment Variables

Create `backend/.env` from the template:
```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` with your actual values:
```env
# Required
MURF_API_KEY=your_actual_murf_api_key_here

# Optional
DEEPGRAM_API_KEY=your_deepgram_key_here

# Environment
ENVIRONMENT=production

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# CORS Origins (Update with your domain)
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Logging
LOG_LEVEL=INFO
```

### 3. Verify Configuration
```bash
# Check that .env file exists and has required keys
cat backend/.env | grep MURF_API_KEY
```

## Local Development

### Quick Start with Docker
```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode
docker-compose up --build -d

# View logs
docker-compose logs -f
```

### Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs (dev mode only)
- **Health Check**: http://localhost:8000/health

### Running Tests

#### Backend Tests
```bash
# Enter backend container
docker-compose exec backend bash

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=. --cov-report=html

# View coverage report
# Open htmlcov/index.html in browser
```

#### Manual Testing
```bash
# Test health endpoint
curl http://localhost:8000/health

# Test API config
curl http://localhost:8000/api/config
```

### Development Workflow
```bash
# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up --build

# View service status
docker-compose ps

# View resource usage
docker stats
```

## Production Deployment

### Option 1: Docker Compose (Simple)

#### 1. Update Production Settings
```bash
# Edit docker-compose.yml
# Update ALLOWED_ORIGINS in backend/.env
# Set ENVIRONMENT=production
```

#### 2. Deploy
```bash
# Pull latest code
git pull origin main

# Build and start in production mode
docker-compose -f docker-compose.yml up --build -d

# Verify health
curl http://localhost:8000/health
curl http://localhost:3000
```

#### 3. Enable HTTPS (Recommended)
Use a reverse proxy like Nginx or Traefik:

```nginx
# /etc/nginx/sites-available/zoolingo
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Option 2: Cloud Deployment

#### AWS ECS/Fargate
```bash
# 1. Build and push images to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

docker tag zoolingo-backend:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/zoolingo-backend:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/zoolingo-backend:latest

docker tag zoolingo-frontend:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/zoolingo-frontend:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/zoolingo-frontend:latest

# 2. Create ECS task definitions and services
# 3. Configure Application Load Balancer
# 4. Set up environment variables in ECS
```

#### Google Cloud Run
```bash
# Build and deploy backend
gcloud builds submit --tag gcr.io/PROJECT_ID/zoolingo-backend ./backend
gcloud run deploy zoolingo-backend \
  --image gcr.io/PROJECT_ID/zoolingo-backend \
  --platform managed \
  --region us-central1 \
  --set-env-vars MURF_API_KEY=your_key

# Build and deploy frontend
gcloud builds submit --tag gcr.io/PROJECT_ID/zoolingo-frontend ./frontend
gcloud run deploy zoolingo-frontend \
  --image gcr.io/PROJECT_ID/zoolingo-frontend \
  --platform managed \
  --region us-central1
```

#### Azure Container Instances
```bash
# Create resource group
az group create --name zoolingo-rg --location eastus

# Deploy containers
az container create \
  --resource-group zoolingo-rg \
  --name zoolingo-backend \
  --image <registry>/zoolingo-backend:latest \
  --dns-name-label zoolingo-backend \
  --ports 8000 \
  --environment-variables MURF_API_KEY=your_key
```

### Option 3: Kubernetes

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: zoolingo-backend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: zoolingo-backend
  template:
    metadata:
      labels:
        app: zoolingo-backend
    spec:
      containers:
      - name: backend
        image: zoolingo-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: MURF_API_KEY
          valueFrom:
            secretKeyRef:
              name: zoolingo-secrets
              key: murf-api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 40
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
```

Deploy:
```bash
kubectl apply -f k8s/
```

## Monitoring & Maintenance

### Health Monitoring
```bash
# Check service health
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2025-11-24T12:00:00",
  "services": {
    "api": "operational",
    "murf_integration": "operational",
    "classifier": "operational",
    "ml_model": "loaded" or "using_fallback"
  }
}
```

### Logs
```bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f backend
docker-compose logs -f frontend

# View last 100 lines
docker-compose logs --tail=100 backend

# Export logs
docker-compose logs > zoolingo-logs.txt
```

### Performance Monitoring
```bash
# Monitor resource usage
docker stats

# Monitor specific container
docker stats zoolingo-backend

# Check disk usage
docker system df
```

### Backup & Recovery
```bash
# Backup uploaded files
tar -czf backup-$(date +%Y%m%d).tar.gz backend/temp_uploads/

# Backup models
tar -czf models-backup-$(date +%Y%m%d).tar.gz backend/models/

# Restore
tar -xzf backup-20251124.tar.gz -C backend/
```

### Updates & Maintenance
```bash
# Pull latest code
git pull origin main

# Rebuild and restart services
docker-compose down
docker-compose up --build -d

# Clean up old images
docker system prune -a

# Update dependencies
cd backend
pip install -r requirements.txt --upgrade
```

## Troubleshooting

### Common Issues

#### 1. Backend Won't Start
```bash
# Check logs
docker-compose logs backend

# Common causes:
# - Missing MURF_API_KEY in .env
# - Port 8000 already in use
# - Insufficient memory

# Solutions:
# Check .env file exists
ls -la backend/.env

# Check port availability
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Increase Docker memory limit (Docker Desktop)
```

#### 2. Frontend Can't Connect to Backend
```bash
# Check backend is running
curl http://localhost:8000/health

# Check CORS settings in backend/.env
# Ensure ALLOWED_ORIGINS includes frontend URL

# Check nginx.conf in frontend
cat frontend/nginx.conf
```

#### 3. Murf API Errors
```bash
# Check API key is set
docker-compose exec backend env | grep MURF

# Test API key manually
curl -X POST https://api.murf.ai/v1/speech/generate \
  -H "api-key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"text":"test","voiceId":"en-US-1"}'

# Check logs for specific error
docker-compose logs backend | grep -i murf
```

#### 4. Out of Memory
```bash
# Check memory usage
docker stats

# Increase limits in docker-compose.yml
# Or reduce workers in backend Dockerfile
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

#### 5. Audio Processing Fails
```bash
# Check librosa installation
docker-compose exec backend python -c "import librosa; print(librosa.__version__)"

# Check ffmpeg
docker-compose exec backend ffmpeg -version

# Verify audio file format
file your-audio.wav
```

### Getting Help

- **GitHub Issues**: https://github.com/yourusername/zoolingo/issues
- **Documentation**: See `/docs` folder
- **Logs**: Always include logs when reporting issues

### Security Checklist

- [ ] API keys stored in `.env` (not committed to git)
- [ ] `.env` added to `.gitignore`
- [ ] CORS origins restricted in production
- [ ] HTTPS enabled for production
- [ ] Regular security updates applied
- [ ] Secrets managed via environment variables
- [ ] Non-root user in Docker containers
- [ ] Resource limits configured
- [ ] Health checks enabled
- [ ] Logging configured

## Performance Optimization

### Backend
- Adjust `--workers` in Dockerfile based on CPU cores
- Use Redis for caching (future enhancement)
- Implement request rate limiting
- Optimize model loading

### Frontend
- Enable gzip compression in nginx
- Implement CDN for static assets
- Add caching headers
- Optimize bundle size

### Database (Future)
- Add PostgreSQL for persistent storage
- Implement connection pooling
- Regular backups

## Scaling

### Horizontal Scaling
```bash
# Scale backend replicas
docker-compose up --scale backend=3

# Use load balancer (nginx, HAProxy, or cloud LB)
```

### Vertical Scaling
```yaml
# Increase resources in docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 4G
```

---

**Last Updated**: 2025-11-24
**Version**: 1.0.0
