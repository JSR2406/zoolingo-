"""Pytest configuration for ZooLingo backend tests.

Provides fixtures and dependency overrides for testing the FastAPI app
without requiring actual authentication or external API keys.
All external modules are mocked BEFORE importing app to prevent import errors.
"""

import sys
from unittest.mock import MagicMock

# Add parent directory to path so 'app' can be imported
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- Mock ONLY modules that import external SDKs not in requirements-core.txt ---
# Modules that can import normally (stdlib or installed deps) are NOT mocked:
#   - services.audio_processor: imports librosa (in requirements-core.txt)
#   - services.ai_classifier: imports tensorflow inside try/except (safe)
#   - services.yamnet_classifier: imports tensorflow inside try/except (safe)
#   - services.nlp_translator: imports stdlib only
#   - petcare.database: imports stdlib only
#   - petcare.router: imports from petcare.database (now works)
# Modules that ARE mocked: import external SDKs not in requirements-core.txt
MOCK_MODULES = [
    "services.murf_integration",
    "services.sarvam_integration",
    "services.sarvam_llm",
    "services.elevenlabs_demo",
    "services.elevenlabs_sfx",
    "auth",
]

def _mock_module(name: str) -> MagicMock:
    """Create a MagicMock module."""
    mod = MagicMock()
    mod.__name__ = name
    return mod

# Register all mock modules BEFORE importing app
for _mod_name in MOCK_MODULES:
    sys.modules[_mod_name] = _mock_module(_mod_name)

# Special handling: petcare.router.petcare_router must be a real FastAPI Router
from fastapi import APIRouter
import petcare.router as _petcare_router_mod
_petcare_router_mod.petcare_router = APIRouter()

# Set _get_pet_or_404 to return a proper pet dict
_petcare_router_mod._get_pet_or_404.return_value = {
    "id": 1,
    "name": "Test Pet",
    "species": "dog",
    "breed": "Golden Retriever",
    "gender": "male",
    "weight_kg": 27.5,
    "avatar_emoji": "🐶",
    "notes": "",
    "microchip_id": "",
    "date_of_birth": "2021-06-14",
    "created_at": "2021-06-14",
    "updated_at": "2021-06-14",
}

# Now import app - service modules import normally, only optional deps are mocked
from app import app as fastapi_app  # noqa: E402

# Set proper return values for mocked SARVAM TTS client
import services.sarvam_integration as _sarvam_mod
_sarvam_mod.SarvamTTSClient.return_value.generate_speech.return_value = {"success": True, "audio_data": b"fake_audio_bytes"}
_sarvam_mod.verify_speaker.return_value = "en-IN_default_voice"

# Also set auth.get_current_user return value
import auth as _auth_mod
_auth_mod.get_current_user.return_value = {
    "id": "demo_user",
    "user_id": "demo_user",
    "email": "test@example.com",
    "is_active": True,
}


@pytest.fixture(scope="session")
def client():
    """Create a test client for the FastAPI app with only optional deps mocked."""
    from fastapi.testclient import TestClient
    with TestClient(fastapi_app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers():
    """Return mock auth headers (for endpoints that require auth)."""
    return {"Authorization": "Bearer test_token"}