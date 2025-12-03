import pytest
import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.audio_processor import load_and_preprocess_audio
from services.ai_classifier import classifier, ANIMALS, EMOTIONS
from services.nlp_translator import translator

def test_audio_processor_invalid_file():
    """Test audio processor with invalid file"""
    result = load_and_preprocess_audio("nonexistent.wav")
    assert result is None

def test_classifier_returns_valid_output():
    """Test classifier returns valid animal and emotion"""
    # Create dummy features
    features = np.random.rand(13)
    
    result = classifier.predict(features)
    
    assert "animal" in result
    assert "emotion" in result
    assert "confidence" in result
    assert result["animal"] in ANIMALS
    assert result["emotion"] in EMOTIONS
    assert 0 <= result["confidence"] <= 1

def test_translator_valid_inputs():
    """Test translator with valid animal and emotion"""
    for animal in ANIMALS[:2]:  # Test first 2 animals
        for emotion in EMOTIONS[:2]:  # Test first 2 emotions
            result = translator.translate(animal, emotion)
            assert isinstance(result, str)
            assert len(result) > 0

def test_translator_invalid_inputs():
    """Test translator with invalid inputs"""
    result = translator.translate("InvalidAnimal", "InvalidEmotion")
    assert isinstance(result, str)
    assert len(result) > 0  # Should return default response
