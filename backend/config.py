import os
import logging
import tempfile
from pathlib import Path

# Anchor dotenv to this file's directory so CWD doesn't matter.
from dotenv import load_dotenv
_BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(_BACKEND_DIR / ".env")

# Serverless platforms (Vercel) run in a read-only CWD; /tmp is the only writable dir.
SERVERLESS = os.getenv("VERCEL") == "1"
_SCRATCH = os.path.join(tempfile.gettempdir(), "zoolingo") if SERVERLESS else None

class Config:
    """Application configuration with validation"""
    
    # Environment
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    
    # API Configuration
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    
    # API Keys
    MURF_API_KEY = os.getenv("MURF_API_KEY")
    DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
    SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
    USE_SARVAM = os.getenv("USE_SARVAM", "True").lower() in ("true", "1", "yes")
    SARVAM_LANGUAGE = os.getenv("SARVAM_LANGUAGE", "hi-IN")
    SARVAM_VOICE_ID = os.getenv("SARVAM_VOICE_ID", "shubh")
    USE_SARVAM_LLM = os.getenv("USE_SARVAM_LLM", "True").lower() in ("true", "1", "yes")

    # ElevenLabs - sound-effect generation for the dog/cat demo mode
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
    # Pre-generated demo/training sounds live under the repo-level data/ tree
    _REPO_ROOT = _BACKEND_DIR.parent
    ELEVENLABS_DEMO_DIR = os.getenv(
        "ELEVENLABS_DEMO_DIR",
        str(_REPO_ROOT / "data" / "test" / "elevenlabs"),
    )

    # English + Hindi MVP (more languages can be added later)
    SUPPORTED_LANGUAGES = ["hi-IN", "en-IN"]

    # Demo audio
    DEMO_AUDIO_DIR = os.getenv("DEMO_AUDIO_DIR", str(_BACKEND_DIR / "demo_audio"))
    
    # CORS
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # File Upload
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "temp_uploads" if not SERVERLESS else _SCRATCH)
    MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = {"wav", "mp3", "ogg", "flac", "m4a"}
    
    # Model Configuration
    MODEL_PATH = os.getenv("MODEL_PATH", "models/emotion_classifier.h5")
    
    @classmethod
    def validate(cls):
        """Validate critical configuration"""
        errors = []
        
        if not cls.MURF_API_KEY and not cls.SARVAM_API_KEY:
            errors.append("No TTS API key configured (MURF_API_KEY or SARVAM_API_KEY)")
        
        if cls.ENVIRONMENT == "production":
            if cls.ALLOWED_ORIGINS == ["*"]:
                errors.append("ALLOWED_ORIGINS should not be '*' in production")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        return True
    
    @classmethod
    def setup_logging(cls):
        """Setup application logging"""
        handlers = [logging.StreamHandler()]
        if not SERVERLESS:
            handlers.append(logging.FileHandler('app.log'))
        logging.basicConfig(
            level=getattr(logging, cls.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=handlers
        )

config = Config()
