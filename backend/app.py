import os
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import shutil
import uuid
from datetime import datetime
from typing import Optional

from config import config
from services.audio_processor import load_and_preprocess_audio
from services.ai_classifier import classifier
from services.nlp_translator import translator
from services.murf_integration import murf_client

# Setup logging
config.setup_logging()
logger = logging.getLogger(__name__)

# Validate configuration
try:
    config.validate()
    logger.info("Configuration validated successfully")
except ValueError as e:
    logger.warning(f"Configuration validation warning: {e}")
    if config.ENVIRONMENT == "production":
        raise

# Initialize FastAPI app
app = FastAPI(
    title="ZooLingo API",
    description="Production-ready backend for ZooLingo Voice Agent",
    version="1.0.0",
    docs_url="/docs" if config.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if config.ENVIRONMENT != "production" else None
)

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure temp directory exists
os.makedirs(config.UPLOAD_DIR, exist_ok=True)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now()
    logger.info(f"Request: {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    duration = (datetime.now() - start_time).total_seconds()
    logger.info(f"Response: {response.status_code} - Duration: {duration:.2f}s")
    
    return response

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "ZooLingo API is running",
        "status": "active",
        "version": "1.0.0",
        "environment": config.ENVIRONMENT
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api": "operational",
            "murf_integration": "operational" if config.MURF_API_KEY else "degraded",
            "classifier": "operational"
        }
    }
    
    # Check if model is loaded
    if hasattr(classifier, 'model') and classifier.model is not None:
        health_status["services"]["ml_model"] = "loaded"
    else:
        health_status["services"]["ml_model"] = "using_fallback"
    
    return health_status

@app.get("/api/config")
async def get_config():
    """Get non-sensitive configuration info"""
    return {
        "environment": config.ENVIRONMENT,
        "max_upload_size_mb": config.MAX_UPLOAD_SIZE / (1024 * 1024),
        "allowed_extensions": list(config.ALLOWED_EXTENSIONS),
        "murf_configured": bool(config.MURF_API_KEY)
    }

def validate_file_extension(filename: str) -> bool:
    """Validate file extension"""
    ext = filename.split(".")[-1].lower()
    return ext in config.ALLOWED_EXTENSIONS

@app.post("/api/process-audio")
async def process_audio(file: UploadFile = File(...)):
    """
    Process uploaded animal audio and return translation with TTS
    """
    file_path: Optional[str] = None
    output_audio_path: Optional[str] = None
    
    try:
        logger.info(f"Processing audio file: {file.filename}")
        
        # Validate file extension
        if not validate_file_extension(file.filename):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(config.ALLOWED_EXTENSIONS)}"
            )
        
        # Validate file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        if file_size > config.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max size: {config.MAX_UPLOAD_SIZE / (1024 * 1024)}MB"
            )
        
        # Save uploaded file
        file_extension = file.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(config.UPLOAD_DIR, filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"File saved: {file_path}")
        
        # 1. Process Audio
        logger.info("Extracting audio features...")
        features = load_and_preprocess_audio(file_path)
        if features is None:
            raise HTTPException(status_code=400, detail="Could not process audio file")
        
        # 2. Classify Emotion/Intent
        logger.info("Classifying emotion and animal...")
        classification = classifier.predict(features)
        animal = classification["animal"]
        emotion = classification["emotion"]
        confidence = classification["confidence"]
        
        logger.info(f"Classification: {animal} - {emotion} (confidence: {confidence})")
        
        # 3. Translate to Human Language
        logger.info("Generating translation...")
        translation_text = translator.translate(animal, emotion)
        
        # 4. Generate Speech (Murf)
        audio_url = None
        logger.info("Generating TTS with Murf...")
        audio_content = murf_client.generate_speech(translation_text)
        
        if audio_content:
            output_audio_filename = f"response_{filename}.mp3"
            output_audio_path = os.path.join(config.UPLOAD_DIR, output_audio_filename)
            
            with open(output_audio_path, "wb") as f:
                f.write(audio_content)
            audio_url = f"/static/{output_audio_filename}"
            logger.info(f"TTS audio generated: {audio_url}")
        else:
            logger.warning("TTS generation failed or is mocked")
        
        # Cleanup input file
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        
        return JSONResponse(content={
            "status": "success",
            "message": "Processed successfully",
            "data": {
                "animal": animal,
                "emotion": emotion,
                "confidence": confidence,
                "translation": translation_text,
                "audio_url": audio_url
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}", exc_info=True)
        
        # Cleanup on error
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        if output_audio_path and os.path.exists(output_audio_path):
            os.remove(output_audio_path)
        
        return JSONResponse(
            content={"status": "error", "message": "Internal server error"},
            status_code=500
        )

# Serve static files for audio playback
app.mount("/static", StaticFiles(directory=config.UPLOAD_DIR), name="static")

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting ZooLingo API in {config.ENVIRONMENT} mode")
    uvicorn.run(
        app,
        host=config.API_HOST,
        port=config.API_PORT,
        log_level=config.LOG_LEVEL.lower()
    )
