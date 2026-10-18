"""Pytest configuration for ZooLingo backend tests.

Provides fixtures and dependency overrides for testing the FastAPI app
without requiring actual authentication or external API keys.
"""

import os
import sys

import pytest
from fastapi.testclient import TestClient

# Add parent directory to path so 'app' can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def client():
    """Create a test client for the FastAPI app."""
    from app import app as fastapi_app

    with TestClient(fastapi_app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers():
    """Return mock auth headers (for endpoints that require auth)."""
    return {"Authorization": "Bearer test_token"}