import pytest
from fastapi.testclient import TestClient
import os
import sys
from unittest.mock import patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

client = TestClient(app)

# Use a fixed test secret for deterministic auth in tests
os.environ["AUTH_SECRET_KEY"] = "test_secret_key_for_development"

# Mock TTS to return dummy audio bytes so tests can verify conversion consumption
MOCK_AUDIO_BYTES = b"fake_audio_bytes"


def mock_generate_tts_audio(text, speaker=None, language=None):
    """Mock TTS that returns dummy audio bytes."""
    return MOCK_AUDIO_BYTES


# Apply the mock to the app module's generate_tts_audio function
app.generate_tts_audio = mock_generate_tts_audio


def get_auth_headers(email="test@example.com", password="TestPass123!"):
    """Register and login a user, return auth headers."""
    # Register (may fail if already exists, which is fine)
    client.post("/auth/register", json={"email": email, "password": password})
    # Login
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_root_endpoint():
    """Test root endpoint returns correct response"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    assert "message" in data
    assert "version" in data


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "services" in data
    assert "timestamp" in data


def test_config_endpoint():
    """Test configuration endpoint"""
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "environment" in data
    assert "max_upload_size_mb" in data
    assert "allowed_extensions" in data


def test_auth_register():
    """Test user registration"""
    resp = client.post(
        "/auth/register", json={"email": "newuser@example.com", "password": "NewPass123!"}
    )
    assert resp.status_code == 201, f"Register failed: {resp.text}"
    data = resp.json()
    assert data["email"] == "newuser@example.com"
    assert data["plan"] == "free"
    assert data["conversions_used"] == 0


def test_auth_register_duplicate():
    """Test registering duplicate email fails"""
    client.post(
        "/auth/register", json={"email": "dup@example.com", "password": "DupPass123!"}
    )
    resp = client.post(
        "/auth/register", json={"email": "dup@example.com", "password": "DupPass123!"}
    )
    assert resp.status_code == 400


def test_auth_login():
    """Test user login returns token"""
    client.post(
        "/auth/register", json={"email": "loginuser@example.com", "password": "LoginPass123!"}
    )
    resp = client.post(
        "/auth/login", json={"email": "loginuser@example.com", "password": "LoginPass123!"}
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_auth_login_wrong_password():
    """Test login with wrong password fails"""
    client.post(
        "/auth/register", json={"email": "wrongpw@example.com", "password": "CorrectPass123!"}
    )
    resp = client.post(
        "/auth/login", json={"email": "wrongpw@example.com", "password": "WrongPass123!"}
    )
    assert resp.status_code == 401


def test_auth_me():
    """Test get current user profile"""
    headers = get_auth_headers("meuser@example.com", "MePass123!")
    resp = client.get("/auth/me", headers=headers)
    assert resp.status_code == 200, f"Me failed: {resp.text}"
    data = resp.json()
    assert data["email"] == "meuser@example.com"
    assert data["plan"] == "free"


def test_auth_me_unauthenticated():
    """Test /auth/me without token returns 401"""
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_process_audio_requires_auth():
    """Test process-audio without auth returns 401"""
    wav_header = (
        b"RIFF" + (36).to_bytes(4, "little") + b"WAVE" + b"fmt "
        + (16).to_bytes(4, "little") + (1).to_bytes(2, "little") + (1).to_bytes(2, "little")
        + (22050).to_bytes(4, "little") + (44100).to_bytes(4, "little")
        + (2).to_bytes(2, "little") + (16).to_bytes(2, "little")
        + b"data" + (0).to_bytes(4, "little")
    )
    files = {"file": ("test.wav", wav_header, "audio/wav")}
    response = client.post("/api/process-audio", files=files)
    assert response.status_code == 401


def test_process_audio_valid_mock():
    """Test process audio with valid mock audio file (authenticated)"""
    headers = get_auth_headers("audio_user@example.com", "AudioPass123!")

    # Create a minimal WAV file header (44 bytes)
    wav_header = (
        b"RIFF" + (36).to_bytes(4, "little") + b"WAVE" + b"fmt "
        + (16).to_bytes(4, "little") + (1).to_bytes(2, "little") + (1).to_bytes(2, "little")
        + (22050).to_bytes(4, "little") + (44100).to_bytes(4, "little")
        + (2).to_bytes(2, "little") + (16).to_bytes(2, "little")
        + b"data" + (0).to_bytes(4, "little")
    )

    files = {"file": ("test.wav", wav_header, "audio/wav")}
    response = client.post("/api/process-audio", files=files, headers=headers)

    # Should succeed even with mock data
    assert response.status_code == 200, f"Process failed: {response.text}"
    data = response.json()
    assert data["status"] == "success"
    assert "data" in data
    assert "animal" in data["data"]
    assert "emotion" in data["data"]
    assert "translation" in data["data"]
    assert "confidence" in data["data"]
    assert "conversions_used" in data["data"]
    assert data["data"]["conversions_used"] == 1


def test_process_audio_consumes_quota():
    """Test that free tier users are blocked after 2 conversions"""
    headers = get_auth_headers("quota_user@example.com", "QuotaPass123!")

    wav_header = (
        b"RIFF" + (36).to_bytes(4, "little") + b"WAVE" + b"fmt "
        + (16).to_bytes(4, "little") + (1).to_bytes(2, "little") + (1).to_bytes(2, "little")
        + (22050).to_bytes(4, "little") + (44100).to_bytes(4, "little")
        + (2).to_bytes(2, "little") + (16).to_bytes(2, "little")
        + b"data" + (0).to_bytes(4, "little")
    )

    # First conversion
    resp1 = client.post(
        "/api/process-audio", files={"file": ("test.wav", wav_header, "audio/wav")}, headers=headers
    )
    assert resp1.status_code == 200, f"First conversion failed: {resp1.text}"
    assert resp1.json()["data"]["conversions_used"] == 1

    # Second conversion
    resp2 = client.post(
        "/api/process-audio", files={"file": ("test.wav", wav_header, "audio/wav")}, headers=headers
    )
    assert resp2.status_code == 200, f"Second conversion failed: {resp2.text}"
    assert resp2.json()["data"]["conversions_used"] == 2

    # Third conversion should be blocked
    resp3 = client.post(
        "/api/process-audio", files={"file": ("test.wav", wav_header, "audio/wav")}, headers=headers
    )
    assert resp3.status_code == 403, f"Third conversion should be blocked: {resp3.text}"
    assert "exhausted" in resp3.json()["detail"].lower()


def test_process_audio_invalid_extension():
    """Test process audio with invalid file extension (authenticated)"""
    headers = get_auth_headers("ext_user@example.com", "ExtPass123!")
    files = {"file": ("test.txt", b"fake content", "text/plain")}
    response = client.post("/api/process-audio", files=files, headers=headers)
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]


def test_process_audio_no_file():
    """Test process audio endpoint without file (authenticated)"""
    headers = get_auth_headers("nofile_user@example.com", "NoFilePass123!")
    response = client.post("/api/process-audio", headers=headers)
    assert response.status_code == 422  # Unprocessable Entity
