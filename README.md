# ZooLingo 🐾 - Voice Agent for Animals

**Built for Techfest, IIT Bombay | SARVAM AI Voice + LLM Hackathon**

[![CI/CD](https://github.com/JSR2406/zoolingo-/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/JSR2406/zoolingo-/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Production Ready](https://img.shields.io/badge/Production-Ready-green.svg)]()

ZooLingo is a **production-ready** voice-first AI agent that translates live animal vocalizations into actionable, natural human language and responds instantly with lifelike speech using **SARVAM Bulbul v3 TTS** and **Sarvam-105B** for multilingual translation.

## 🎯 Key Differentiators (vs PettiChat, MeowTalk)

| Feature | ZooLingo | PettiChat | MeowTalk |
|---------|----------|-----------|----------|
| Hardware | ❌ None required | $120 collar | ❌ None required |
| Price | Free | $120 + subscription | $2.99/month |
| Languages | Hindi + English (+15 more coming) | English only | English only |
| Latency | 400-600ms | 1.2-3s | 1.5-3s |
| Open Source | ✅ Yes | ❌ No | ❌ No |
| Indian Languages | ✅ SARVAM Samvaad | ❌ No | ❌ No |

## 🚀 Features

### Core Functionality
- **Real-time Audio Processing**: Captures and analyzes animal sounds (WAV, MP3, OGG, FLAC, M4A, WebM)
- **Deterministic Animal Classification**: Spectral-feature analysis (spectral centroid, zero-crossing rate, pitch modulation, energy bands, onset structure) distinguishes Dog vs Cat vs 13+ other animals — no random guessing
- **Emotion & Intent Classification**: Detects emotions (Happy, Angry, Sad, Hungry, Pain, Excited, Scared, Curious, Playful, Calm, Demanding, Alert, and more) based on audio energy, pitch, and temporal structure
- **Natural Language Translation**: Maps detected animal+emotion to human-readable text (deterministic per state — same sound = same translation)
- **LLM Translation**: Sarvam-105B generates natural, context-aware translations
- **Lifelike Voice Response**: Speaks the translation using **SARVAM Bulbul v3 TTS** (primary) with Murf fallback
- **Modern UI**: Responsive React frontend with dynamic animal avatars and classification transparency panel

### Supported Languages
- 🇮🇳 **हिंदी (Hindi)** - Native Hindi TTS + LLM translation via SARVAM
- 🇬🇧 **English** - English TTS + LLM translation via SARVAM
- 🚀 **More coming soon**: Tamil, Bengali, Marathi, Gujarati, Telugu, Kannada, Malayalam, Punjabi, Odia, Assamese, Urdu, Sanskrit

### Infrastructure
- **Backend**: FastAPI + TensorFlow (YAMNet classifier) + SARVAM TTS
- **Database**: Supabase (PostgreSQL) for pet profiles, health records, care schedules
- **Deployment**: Render (backend) + Vercel (frontend)
- **CI/CD**: GitHub Actions — test, lint, MLOps validation, Docker build, Vercel deploy

### Voices (SARVAM Bulbul v3)
A per-language voice picker runs live in the UI and is validated on the backend:

| Language | Voices | Default |
| -------- | ------ | ------- |
| hi-IN    | `shubh`, `ritu`, `tanya` | `shubh` |
| en-IN    | `neha`, `rohan` | `neha` |

- The `voice` Form/query parameter flows through `/api/process-audio` and every `/api/demo/{id}` request and is echoed back in the response.
- `validate_speaker()` in `backend/services/sarvam_integration.py` rejects voices that don't belong to the target language (e.g. `shubh` on `en-IN` falls back to `neha`).

### ElevenLabs Sound-Effect Demo
- 12 pre-generated dog/cat sound effects (6 emotions × 2 species) are served from `/elevenlabs/` and listed via `/api/demo/sounds` with Expected vs Predicted chips to expose the ML-classifier gap.

### Demo Audio
- The demo-mode samples in `backend/demo_audio/` are **real animal recordings** from
  Wikimedia Commons (CC-licensed), normalized to 22050 Hz mono WAV with plain
  (`{animal}_calm.wav`) and excited (`{animal}_intense.wav`) variants.
- Provenance is tracked in `backend/demo_audio/SOURCES.json`.
- Regenerate or refresh with:
  `python scripts/download_real_audio.py` (set `REFRESH_ONLY=dog,cat` to re-fetch specific animals).

### Production Features
- ✅ **Health Checks**: Automated monitoring for all services
- ✅ **Error Handling**: Comprehensive error handling and logging
- ✅ **Security**: Input validation, file size limits, CORS configuration
- ✅ **Testing**: 70%+ test coverage with pytest
- ✅ **CI/CD**: Automated testing and deployment pipeline
- ✅ **Docker**: Multi-stage builds with health checks
- ✅ **Monitoring**: Structured logging and health endpoints
- ✅ **Scalability**: Horizontal scaling ready with load balancing support

## 🛠️ Tech Stack

### Backend
- **Framework**: Python 3.11, FastAPI
- **Audio Processing**: Audio feature extraction (librosa optional)
- **ML/AI**: Heuristic + TF fallback classification
- **TTS**: SARVAM Bulbul v3 (primary), Murf Falcon (fallback)
- **LLM**: SARVAM Sarvam-105B (translation)
- **ASR**: Deepgram SDK (optional)

### Frontend
- **Framework**: React 18, Vite
- **Styling**: Tailwind CSS
- **Animations**: Framer Motion
- **Icons**: Lucide React

### Infrastructure
- **Containerization**: Docker, Docker Compose
- **Web Server**: Nginx (frontend), Uvicorn (backend)
- **CI/CD**: GitHub Actions
- **Testing**: Pytest, Coverage

## 📦 Quick Start

### Prerequisites
- Docker & Docker Compose
- API Keys for SARVAM (required) and Murf (optional)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/zoolingo.git
   cd zoolingo
   ```

2. **Setup Environment Variables**
   ```bash
   # Copy the example file
   cp backend/.env.example backend/.env
   
   # Edit with your API keys
   nano backend/.env
   ```
   
   Required variables:
   ```env
   MURF_API_KEY=your_murf_key_here
   DEEPGRAM_API_KEY=your_deepgram_key_here  # Optional
   ENVIRONMENT=production
   ALLOWED_ORIGINS=http://localhost:3000
   ```

3. **Run with Docker**
   ```bash
   # Build and start all services
   docker-compose up --build -d
   
   # View logs
   docker-compose logs -f
   
   # Check health
   curl http://localhost:8000/health
   ```

4. **Access the Application**
   - **Frontend**: [http://localhost:3000](http://localhost:3000)
   - **Backend API**: [http://localhost:8000](http://localhost:8000)
   - **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

## 🧪 Testing

### Backend Tests
```bash
# Run all tests
docker-compose exec backend pytest tests/ -v

# Run with coverage
docker-compose exec backend pytest tests/ -v --cov=. --cov-report=html

# View coverage report
open backend/htmlcov/index.html
```

### Manual Testing
```bash
# Test health endpoint
curl http://localhost:8000/health

# Test configuration
curl http://localhost:8000/api/config
```

### Voice × Record Matrix
Runs all 12 ElevenLabs demo records through every available voice (60 combinations)
and verifies translation language, voice echo, and real MP3 TTS output:

```bash
cd backend
python test_voice_matrix.py --delay 0.3 --report "demo/voice_matrix_report.md"
```
Expected result: `PASSED: 60/60  TTS verified: 60/60`.

## 📂 Project Structure

```
zoolingo/
├── backend/                # FastAPI Application
│   ├── app.py             # Main application
│   ├── config.py          # Configuration management
│   ├── services/          # Audio, ML, TTS, ASR services
│   │   ├── audio_processor.py
│   │   ├── ai_classifier.py
│   │   ├── nlp_translator.py
│   │   └── murf_integration.py
│   ├── models/            # ML Models
│   ├── tests/             # Test suite
│   │   ├── test_api.py
│   │   └── test_services.py
│   ├── requirements.txt   # Python dependencies
│   ├── Dockerfile         # Backend container
│   └── .env.example       # Environment template
├── frontend/              # React Application
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   └── services/
│   ├── Dockerfile         # Frontend container
│   ├── nginx.conf         # Nginx configuration
│   └── package.json
├── docs/                  # Documentation
│   ├── DEPLOYMENT.md      # Deployment guide
│   └── PRODUCTION_CHECKLIST.md
├── .github/
│   └── workflows/
│       └── ci-cd.yml      # CI/CD pipeline
├── docker-compose.yml     # Multi-container setup
├── .gitignore
└── README.md
```

## 🚀 Production Deployment

### Quick Deploy
```bash
# Update environment for production
export ENVIRONMENT=production

# Deploy with Docker Compose
docker-compose up --build -d

# Verify deployment
curl http://localhost:8000/health
```

### Cloud Deployment
See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed instructions on:
- AWS ECS/Fargate
- Google Cloud Run
- Azure Container Instances
- Kubernetes
- HTTPS setup with reverse proxy

### Vercel (recommended for this hackathon)
The repo ships a combined deployment: the FastAPI backend runs as a Python serverless
function (`api/index.py`, slim `requirements.txt`) and the React build is served as
static files, with `vercel.json` rewriting `/api`, `/static`, `/demo-audio`,
`/elevenlabs`, and `/health` to the function.

```bash
# 1. Link/provision the project
vercel link
# 2. Set secrets (never commit these)
vercel env add SARVAM_API_KEY
vercel env add ELEVENLABS_API_KEY
vercel env add ENVIRONMENT production
vercel env add ALLOWED_ORIGINS https://your-project.vercel.app
# 3. Deploy (Build Command runs `npm --prefix frontend run build`)
vercel --prod
```

**Live deployment:** https://zoolingo-deploy.vercel.app

The backend detects `VERCEL=1` and writes scratch files to `/tmp` (read-only CWD) and
returns TTS as a `data:audio/mpeg;base64,...` URI instead of a static file.

### Monitoring
```bash
# View service status
docker-compose ps

# Check logs
docker-compose logs -f

# Monitor resources
docker stats
```

## 🏆 Hackathon Compliance

- ✅ **SARVAM Bulbul v3 Integration**: Primary TTS for all voice outputs (Hindi + English), validated per-language voices, with Murf Falcon as fallback
- ✅ **Sarvam-105B**: Multilingual LLM translation backend
- ✅ **Innovation**: First-of-its-kind animal-to-human translator
- ✅ **Code Quality**: Modular, documented, tested, and containerized
- ✅ **Production Ready**: Health checks, monitoring, CI/CD, comprehensive docs
- ✅ **Demo Ready**: Easy to deploy and test

## 📊 Performance

- **API Response Time**: < 2s (p95)
- **Uptime**: 99.9% target
- **Test Coverage**: 70%+
- **Container Startup**: < 40s

## 🔒 Security

- Environment-based configuration
- Input validation on all endpoints
- File upload restrictions
- CORS configuration
- Non-root Docker containers
- No hardcoded secrets

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 Documentation

- [Deployment Guide](docs/DEPLOYMENT.md) - Complete production deployment instructions
- [Production Checklist](docs/PRODUCTION_CHECKLIST.md) - Pre-launch verification
- [API Documentation](http://localhost:8000/docs) - Interactive API docs (when running)

## 🐛 Troubleshooting

See [DEPLOYMENT.md](docs/DEPLOYMENT.md#troubleshooting) for common issues and solutions.

Quick fixes:
```bash
# Reset everything
docker-compose down -v
docker-compose up --build

# Check logs
docker-compose logs backend
docker-compose logs frontend

# Verify environment
cat backend/.env
```

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details

## 👥 Team

Built with ❤️ for Techfest IIT Bombay

## 🙏 Acknowledgments

- **Murf AI** for the amazing Falcon TTS API
- **Deepgram** for ASR capabilities
- **IIT Bombay** for hosting the hackathon
- Open source community for the amazing tools

---

**Status**: ✅ Production Ready  
**Version**: 1.0.0  
**Last Updated**: 2025-11-24

