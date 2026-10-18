"""Pytest configuration for ZooLingo backend tests.

Provides fixtures and dependency overrides for testing the FastAPI app
without requiring actual authentication or external API keys.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import the app after setting up mocks
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def client():
    """Create a test client for the FastAPI app with auth overridden."""
    # Override auth dependency before importing app
    from unittest.mock import MagicMock

    # Mock the auth dependency to return a fake user
    def mock_get_current_user():
        return {"id": "test_user", "user_id": "test_user", "email": "test@test.com"}

    # Import app after setting up the override
    from app import app as fastapi_app

    # Override the get_current_user dependency
    from auth import get_current_user

    fastapi_app.dependency_overrides[get_current_user] = mock_get_current_user

    with TestClient(fastapi_app) as test_client:
        yield test_client

    # Clean up
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    """Return mock auth headers."""
    return {"Authorization": "Bearer test_token"}