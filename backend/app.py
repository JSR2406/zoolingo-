import os
import logging
import base64
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Form, Query, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import shutil
import uuid
from datetime import datetime
from typing import Optional
import random

from config import config, SERVERLESS
from services.audio_processor import load_and_preprocess_audio
from services.ai_classifier import classifier, ANIMALS, EMOTIONS
from services.yamnet_classifier import yamnet_classifier
from services.nlp_translator import translator
from services.murf_integration import murf_client
from services.sarvam_integration import (
    SarvamTTSClient,
    VOICES_BY_LANGUAGE,
    DEFAULT_VOICES,
    validate_speaker,
)
from services.sarvam_llm import llm_translator
from services.elevenlabs_demo import all_sounds
from services.elevenlabs_sfx import sfx_client
from petcare.database import init_db
from petcare.router import petcare_router
from auth_router import router as auth_router
from auth import (
    get_current_user,
    get_optional_user,
    check_conversion_allowed,
    reserve_conversion,
    confirm_conversion,
    release_conversion,
    get_user_conversions_used,
)

# Initialize SARVAM TTS client (primary)
sarvam_client = SarvamTTSClient()

# Intense emotions map to the "_intense" demo audio variant
INTENSE_EMOTIONS = {
    "Angry",
    "Excited",
    "Scared",
    "Pain",
    "Aggressive",
    "Alert",
    "Demanding",
    "Bossy",
    "Mischievous",
}

DEFAULT_LANGUAGE = config.SARVAM_LANGUAGE

# Normalize short language codes (e.g. "hi" -> "hi-IN") for SARVAM TTS
LANG_BY_ALPHA2 = {v.split("-")[0]: v for v in SarvamTTSClient.LANGUAGE_CODES.values()}


def normalize_language(language: Optional[str]) -> str:
    if not language:
        return DEFAULT_LANGUAGE
    lang = language.strip()
    if "-" not in lang and lang.lower() in LANG_BY_ALPHA2:
        return LANG_BY_ALPHA2[lang.lower()]
    return lang


def demo_audio_variant(emotion: str) -> str:
    return "intense" if emotion in INTENSE_EMOTIONS else "calm"


def demo_audio_url_for(animal: str, emotion: str) -> Optional[str]:
    """Path to the canned animal sound for a given animal+emotion."""
    animal_key = animal.lower()
    variant = demo_audio_variant(emotion)
    if os.path.exists(
        os.path.join(config.DEMO_AUDIO_DIR, f"{animal_key}_{variant}.wav")
    ):
        return f"/demo-audio/{animal_key}_{variant}.wav"
    return None


def finalize_translation(
    english_text: str, animal: str, emotion: str, language: Optional[str] = None
) -> str:
    """Apply LLM multilingual translation when enabled; otherwise keep English."""
    lang = normalize_language(language)
    if (
        config.USE_SARVAM_LLM
        and llm_translator.api_key
        and lang.lower() != "en-in"
        and lang.lower() != "en"
    ):
        translated = llm_translator.translate(
            english_text, animal, emotion, target_language=lang
        )
        if translated and translated.strip("\n") != "":
            return translated
    return english_text


def generate_tts_audio(
    text: str, speaker: Optional[str] = None, language: Optional[str] = None
) -> Optional[bytes]:
    """Generate TTS audio using SARVAM (primary) or Murf (fallback)."""
    # SARVAM is primary TTS
    if getattr(config, "USE_SARVAM", True) and sarvam_client.api_key:
        logger.info("Generating TTS with SARVAM (primary)...")
        lang = normalize_language(language)
        resolved_speaker = validate_speaker(speaker or config.SARVAM_VOICE_ID, lang)
        result = sarvam_client.generate_speech(
            text=text,
            language_code=lang,
            speaker=resolved_speaker,
            save_path=os.path.join(config.UPLOAD_DIR, "temp_sarvam.mp3"),
        )
        if result["success"] and result.get("audio_data"):
            return result["audio_data"]
        else:
            logger.warning(f"SARVAM TTS failed: {result.get('error')}")

    # Fallback to Murf
    if config.MURF_API_KEY:
        logger.info("Generating TTS with Murf (fallback)...")
        audio_content = murf_client.generate_speech(text)
        return audio_content

    return None


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
    description="Production-ready backend for ZooLingo Voice Agent - Translates animal sounds to human language",
    version="1.0.0",
    docs_url="/docs" if config.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if config.ENVIRONMENT != "production" else None,
)

# CORS Setup - Allow frontend origins
allowed_origins = config.ALLOWED_ORIGINS
if "*" not in allowed_origins:
    # Add common development origins
    allowed_origins.extend(
        [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure temp directory exists
os.makedirs(config.UPLOAD_DIR, exist_ok=True)

# PetCare: create tables + seed (idempotent; :memory: fallback on read-only serverless FS)
init_db()
app.include_router(petcare_router)
app.include_router(auth_router)


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
        "environment": config.ENVIRONMENT,
        "endpoints": {
            "health": "/health",
            "docs": "/docs" if config.ENVIRONMENT != "production" else "disabled",
            "process_audio": "/api/process-audio",
            "demo": "/api/demo/{demo_id}",
            "config": "/api/config",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api": "operational",
            "sarvam_integration": "operational"
            if config.SARVAM_API_KEY
            else "degraded",
            "sarvam_llm_translation": "operational"
            if (config.SARVAM_API_KEY and config.USE_SARVAM_LLM)
            else "degraded",
            "murf_integration": "operational" if config.MURF_API_KEY else "degraded",
            "elevenlabs_sfx": "operational"
            if config.ELEVENLABS_API_KEY
            else "degraded",
            "classifier": "operational",
        },
    }

    # Check if model is loaded
    if hasattr(classifier, "model") and classifier.model is not None:
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
        "sarvam_configured": bool(config.SARVAM_API_KEY),
        "sarvam_language": config.SARVAM_LANGUAGE,
        "sarvam_llm_translation": bool(config.USE_SARVAM_LLM),
        "murf_configured": bool(config.MURF_API_KEY),
        "elevenlabs_configured": bool(config.ELEVENLABS_API_KEY),
        "voices": VOICES_BY_LANGUAGE,
        "default_voice": config.SARVAM_VOICE_ID,
        "supported_animals": translator.get_supported_animals(),
        "supported_emotions": translator.get_supported_emotions(),
        "supported_languages": config.SUPPORTED_LANGUAGES
        if hasattr(config, "SUPPORTED_LANGUAGES")
        else None,
    }


@app.get("/api/languages")
async def get_languages():
    """List languages available for translation + TTS (English + Hindi MVP)."""
    languages = []
    for lang in config.SUPPORTED_LANGUAGES:
        code = lang if isinstance(lang, str) else lang.get("code")
        languages.append(
            {
                "code": code,
                "name": lang if isinstance(lang, str) else lang.get("name", code),
                "voices": VOICES_BY_LANGUAGE.get(code, []),
                "default_voice": DEFAULT_VOICES.get(code, config.SARVAM_VOICE_ID),
            }
        )
    return {
        "default": DEFAULT_LANGUAGE,
        "llm_enabled": config.USE_SARVAM_LLM and bool(config.SARVAM_API_KEY),
        "languages": languages,
    }


def validate_file_extension(filename: str) -> bool:
    """Validate file extension"""
    ext = filename.split(".")[-1].lower()
    return ext in config.ALLOWED_EXTENSIONS


@app.post("/api/process-audio")
async def process_audio(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    voice: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    """
    Process uploaded animal audio and return translation with TTS.
    Requires authentication. Consumes one conversion from the user's quota.
    """
    user_id = str(current_user["id"])
    file_path: Optional[str] = None
    output_audio_path: Optional[str] = None
    reservation_id: Optional[str] = None

    try:
        logger.info(f"Processing audio file: {file.filename} for user {user_id}")

        # Check and reserve a conversion from the user's quota
        allowed, reason = check_conversion_allowed(current_user)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=reason,
            )
        reservation_id = reserve_conversion(current_user)

        # Validate file extension
        if not validate_file_extension(file.filename):
            release_conversion(current_user, reservation_id)
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(config.ALLOWED_EXTENSIONS)}",
            )

        # Validate file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning

        if file_size > config.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max size: {config.MAX_UPLOAD_SIZE / (1024 * 1024)}MB",
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

        # 2. Classify Emotion/Intent (real YAMNet AudioSet model first, legacy fallback)
        logger.info("Classifying emotion and animal...")
        classification = None
        try:
            yamnet_result = yamnet_classifier.classify(file_path)
            if yamnet_result:
                classification = yamnet_result
                logger.info(
                    f"YAMNet detected [{', '.join(e['class'] for e in yamnet_result.get('evidence', [])[:3])}]"
                )
        except Exception as e:
            logger.warning(f"YAMNet classification failed: {e}")

        if classification is None:
            classification = classifier.predict(features)
            classification.setdefault("classifier", "legacy")

        animal = classification["animal"]
        emotion = classification["emotion"]
        confidence = classification["confidence"]

        logger.info(f"Classification: {animal} - {emotion} (confidence: {confidence})")

        # 3. Translate to Human Language
        logger.info("Generating translation...")
        base_translation = translator.translate(animal, emotion)
        target_language = language or DEFAULT_LANGUAGE
        translation_text = finalize_translation(
            base_translation, animal, emotion, target_language
        )

        # Resolve the TTS voice (validated against the target language)
        resolved_voice = validate_speaker(
            voice or config.SARVAM_VOICE_ID, target_language
        )

        # 4. Generate Speech (SARVAM primary, Murf fallback)
        audio_url = None
        tts_success = False
        if sarvam_client.api_key or config.MURF_API_KEY:
            logger.info("Generating TTS audio...")
            audio_content = generate_tts_audio(
                translation_text, speaker=resolved_voice, language=target_language
            )

            if audio_content:
                if SERVERLESS:
                    # Read-only filesystem: hand the MP3 back as a data URI instead of a static file
                    audio_url = "data:audio/mpeg;base64," + base64.b64encode(
                        audio_content
                    ).decode("ascii")
                else:
                    output_audio_filename = f"response_{filename}.mp3"
                    output_audio_path = os.path.join(
                        config.UPLOAD_DIR, output_audio_filename
                    )

                    with open(output_audio_path, "wb") as f:
                        f.write(audio_content)
                    audio_url = f"/static/{output_audio_filename}"
                logger.info(f"TTS audio generated: {audio_url}")
                tts_success = True
            else:
                logger.warning("TTS generation failed")
        else:
            logger.info("No TTS API key configured, skipping TTS")

        # Cleanup input file
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

        # Consume a conversion only after a usable interpretation AND playable
        # speech output are successfully produced.
        if tts_success and audio_url:
            confirm_conversion(current_user, reservation_id)
        else:
            # Release reservation on TTS failure - user shouldn't lose allowance
            release_conversion(current_user, reservation_id)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Speech generation failed. Please try again.",
            )

        return JSONResponse(
            content={
                "status": "success",
                "message": "Processed successfully",
                "data": {
                    "animal": animal,
                    "emotion": emotion,
                    "confidence": confidence,
                    "classifier": classification.get("classifier", "unknown"),
                    "translation": translation_text,
                    "audio_url": audio_url,
                    "language": target_language,
                    "voice": resolved_voice,
                    "conversions_used": get_user_conversions_used(current_user),
                },
            }
        )

    except HTTPException:
        # Release reservation on client errors (400, 403, etc.)
        if reservation_id is not None:
            release_conversion(current_user, reservation_id)
        raise
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}", exc_info=True)

        # Release reservation on server error
        if reservation_id is not None:
            release_conversion(current_user, reservation_id)

        # Cleanup on error
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        if output_audio_path and os.path.exists(output_audio_path):
            os.remove(output_audio_path)

        return JSONResponse(
            content={"status": "error", "message": "Internal server error"},
            status_code=500,
        )


# Demo endpoint for testing without actual audio
@app.post("/api/demo/{demo_id}")
async def process_demo(
    demo_id: str,
    language: Optional[str] = Query(None),
    voice: Optional[str] = Query(None),
):
    """
    Process a demo sound without actual audio file.
    Useful for demonstrations and testing.
    """
    try:
        logger.info(f"Processing demo: {demo_id}")

        # Parse demo_id (format: "animal-emotion", e.g., "dog-happy")
        parts = demo_id.lower().split("-")
        if len(parts) != 2:
            raise HTTPException(
                status_code=400, detail="Invalid demo ID format. Use 'animal-emotion'"
            )

        animal_key, emotion_key = parts

        # Map to proper case - support all animals and emotions
        animal_map = {
            "dog": "Dog",
            "cat": "Cat",
            "cow": "Cow",
            "lion": "Lion",
            "bird": "Bird",
            "horse": "Horse",
            "elephant": "Elephant",
            "sheep": "Sheep",
            "goat": "Goat",
            "pig": "Pig",
            "chicken": "Chicken",
            "duck": "Duck",
            "monkey": "Monkey",
            "parrot": "Parrot",
            "wolf": "Wolf",
        }
        emotion_map = {
            "happy": "Happy",
            "angry": "Angry",
            "sad": "Sad",
            "hungry": "Hungry",
            "pain": "Pain",
            "excited": "Excited",
            "scared": "Scared",
            "curious": "Curious",
            "playful": "Playful",
            "calm": "Calm",
            "demanding": "Demanding",
            "alert": "Alert",
            "mischievous": "Mischievous",
            "proud": "Proud",
            "bossy": "Bossy",
            "singing": "Singing",
            "chatty": "Chatty",
            "aggressive": "Aggressive",
            "lonely": "Lonely",
        }

        animal = animal_map.get(animal_key)
        emotion = emotion_map.get(emotion_key)

        if not animal:
            # Try to use any supported animal
            animal = animal_key.capitalize()
        if not emotion:
            # Try to use any supported emotion
            emotion = emotion_key.capitalize()

        # Generate translation
        base_translation = translator.translate(animal, emotion)
        confidence = round(random.uniform(0.85, 0.98), 2)

        # LLM multilingual translation
        target_language = language or DEFAULT_LANGUAGE
        translation_text = finalize_translation(
            base_translation, animal, emotion, target_language
        )

        # Demo audio sample (canned animal sound for the exported demo)
        demo_audio_url = demo_audio_url_for(animal, emotion)

        # Resolve the TTS voice (validated against the target language)
        resolved_voice = validate_speaker(
            voice or config.SARVAM_VOICE_ID, target_language
        )

        # Generate TTS if configured (SARVAM primary, Murf fallback)
        audio_url = None
        if sarvam_client.api_key or config.MURF_API_KEY:
            logger.info("Generating TTS audio...")
            audio_content = generate_tts_audio(
                translation_text, speaker=resolved_voice, language=target_language
            )

            if audio_content:
                if SERVERLESS:
                    # Read-only filesystem: hand the MP3 back as a data URI instead of a static file
                    audio_url = "data:audio/mpeg;base64," + base64.b64encode(
                        audio_content
                    ).decode("ascii")
                else:
                    output_filename = f"demo_{demo_id}_{uuid.uuid4().hex[:8]}.mp3"
                    output_path = os.path.join(config.UPLOAD_DIR, output_filename)

                    with open(output_path, "wb") as f:
                        f.write(audio_content)
                    audio_url = f"/static/{output_filename}"
                logger.info(f"Demo TTS generated: {audio_url}")

        return JSONResponse(
            content={
                "status": "success",
                "message": "Demo processed successfully",
                "data": {
                    "animal": animal,
                    "emotion": emotion,
                    "confidence": confidence,
                    "translation": translation_text,
                    "audio_url": audio_url,
                    "demo_audio_url": demo_audio_url,
                    "demo_mode": True,
                    "language": target_language,
                    "voice": resolved_voice,
                },
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing demo: {str(e)}", exc_info=True)
        return JSONResponse(
            content={"status": "error", "message": "Internal server error"},
            status_code=500,
        )


# Get supported animals and emotions
@app.get("/api/supported")
async def get_supported():
    """Get list of supported animals and emotions"""
    return {
        "animals": translator.get_supported_animals(),
        "emotions": translator.get_supported_emotions(),
    }


# ElevenLabs dog/cat pre-recorded demo sounds (12 sounds)
@app.get("/api/demo/sounds")
async def list_elevenlabs_sounds():
    """
    List the pre-generated ElevenLabs demo sounds (dog + cat x 6 emotions).
    Each entry includes its URL, prompt, and expected translations.
    """
    sounds = []
    for s in all_sounds():
        if not os.path.exists(os.path.join(config.ELEVENLABS_DEMO_DIR, s["filename"])):
            continue
        sounds.append(
            {
                "filename": s["filename"],
                "species": s["species"],
                "animal": s["animal"],
                "emotion": s["emotion"],
                "label": s["label"],
                "classifier_label": s["classifier_label"],
                "url": f"/elevenlabs/{s['filename']}",
                "expected_en": s["expected_en"],
                "expected_hi": s["expected_hi"],
            }
        )
    return {
        "status": "success",
        "configured": bool(config.ELEVENLABS_API_KEY),
        "total": len(sounds),
        "sounds": sounds,
    }


# Serve static files for audio playback
app.mount("/static", StaticFiles(directory=config.UPLOAD_DIR), name="static")

# Serve demo audio files (pre-generated animal sounds for the demo flow)
os.makedirs(config.DEMO_AUDIO_DIR, exist_ok=True)
app.mount(
    "/demo-audio", StaticFiles(directory=config.DEMO_AUDIO_DIR), name="demo-audio"
)

# Serve ElevenLabs pre-generated dog/cat demo sounds
os.makedirs(config.ELEVENLABS_DEMO_DIR, exist_ok=True)
app.mount(
    "/elevenlabs", StaticFiles(directory=config.ELEVENLABS_DEMO_DIR), name="elevenlabs"
)

if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting ZooLingo API in {config.ENVIRONMENT} mode")
    uvicorn.run(
        app,
        host=config.API_HOST,
        port=config.API_PORT,
        log_level=config.LOG_LEVEL.lower(),
    )
