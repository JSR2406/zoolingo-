import os
from dotenv import load_dotenv
import logging

load_dotenv()

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
    
    # CORS
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # File Upload
    UPLOAD_DIR = "temp_uploads"
    MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = {"wav", "mp3", "ogg", "flac", "m4a"}
    
    # Model Configuration
    MODEL_PATH = os.getenv("MODEL_PATH", "models/emotion_classifier.h5")
    
    @classmethod
    def validate(cls):
        """Validate critical configuration"""
        errors = []
        
        if not cls.MURF_API_KEY:
            errors.append("MURF_API_KEY is not set")
        
        if cls.ENVIRONMENT == "production":
            if cls.ALLOWED_ORIGINS == ["*"]:
                errors.append("ALLOWED_ORIGINS should not be '*' in production")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        return True
    
    @classmethod
    def setup_logging(cls):
        """Setup application logging"""
        logging.basicConfig(
            level=getattr(logging, cls.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('app.log')
            ]
        )

config = Config()
