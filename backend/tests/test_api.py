import pytest
from fastapi.testclient import TestClient
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

client = TestClient(app)

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

def test_process_audio_no_file():
    """Test process audio endpoint without file"""
    response = client.post("/api/process-audio")
    assert response.status_code == 422  # Unprocessable Entity

def test_process_audio_invalid_extension():
    """Test process audio with invalid file extension"""
    files = {"file": ("test.txt", b"fake content", "text/plain")}
    response = client.post("/api/process-audio", files=files)
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]

def test_process_audio_valid_mock():
    """Test process audio with valid mock audio file"""
    # Create a minimal WAV file header (44 bytes)
    wav_header = (
        b'RIFF' + (36).to_bytes(4, 'little') +
        b'WAVE' + b'fmt ' + (16).to_bytes(4, 'little') +
        (1).to_bytes(2, 'little') + (1).to_bytes(2, 'little') +
        (22050).to_bytes(4, 'little') + (44100).to_bytes(4, 'little') +
        (2).to_bytes(2, 'little') + (16).to_bytes(2, 'little') +
        b'data' + (0).to_bytes(4, 'little')
    )
    
    files = {"file": ("test.wav", wav_header, "audio/wav")}
    response = client.post("/api/process-audio", files=files)
    
    # Should succeed even with mock data
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "data" in data
    assert "animal" in data["data"]
    assert "emotion" in data["data"]
    assert "translation" in data["data"]
    assert "confidence" in data["data"]
