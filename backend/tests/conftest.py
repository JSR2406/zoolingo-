"""Pytest configuration for ZooLingo backend tests.

Provides fixtures and dependency overrides for testing the FastAPI app
without requiring actual authentication or external API keys.
All external modules are mocked BEFORE importing app to prevent import errors.
"""

import sys
from unittest.mock import MagicMock
import os

# Add parent directory to path so 'app' can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- Mock ALL external dependencies BEFORE importing app ---
# This prevents ImportError from any module that has missing dependencies

from fastapi import APIRouter

def _mock_module(name: str) -> MagicMock:
    """Create a MagicMock module with common FastAPI attributes."""
    mod = MagicMock()
    mod.__name__ = name
    return mod


# List of all modules that app.py imports (directly or transitively)
MOCK_MODULES = [
    "config",
    "services.audio_processor",
    "services.ai_classifier",
    "services.yamnet_classifier",
    "services.nlp_translator",
    "services.murf_integration",
    "services.sarvam_integration",
    "services.sarvam_llm",
    "services.elevenlabs_demo",
    "services.elevenlabs_sfx",
    "petcare.database",
    "petcare.router",
    "auth",
]

# Register all mock modules BEFORE importing app
for _mod_name in MOCK_MODULES:
    sys.modules[_mod_name] = _mock_module(_mod_name)

# Special handling: petcare.router.petcare_router must be a real FastAPI Router
# because app.include_router() expects a proper Router object
import petcare.router as _petcare_router_mod
_petcare_router_mod.petcare_router = APIRouter()

# Also ensure petcare.database.init_db is a no-op mock
import petcare.database as _petcare_db_mod
_petcare_db_mod.init_db = MagicMock()

# Now import app - all imports will resolve to mocks
from app import app as fastapi_app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    """Create a test client for the FastAPI app with all dependencies mocked."""
    from fastapi.testclient import TestClient

    with TestClient(fastapi_app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers():
    """Return mock auth headers (for endpoints that require auth)."""
    return {"Authorization": "Bearer test_token"}