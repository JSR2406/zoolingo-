import os
import requests
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class MurfClient:
    def __init__(self):
        self.api_key = os.getenv("MURF_API_KEY")
        # Murf API endpoint - Update this based on actual Murf documentation
        self.base_url = "https://api.murf.ai/v1/speech/generate"
        self.timeout = 30  # seconds
        
    def generate_speech(self, text: str, voice_id: str = "en-US-1", retries: int = 2) -> Optional[bytes]:
        """
        Generate speech from text using Murf Falcon TTS.
        
        Args:
            text: Text to convert to speech
            voice_id: Voice ID to use (default: en-US-1)
            retries: Number of retry attempts
            
        Returns:
            Audio content as bytes, or None if failed
        """
        if not self.api_key:
            logger.error("Murf API Key is missing!")
            return None

        payload = {
            "voiceId": voice_id,
            "style": "General",
            "text": text,
            "rate": 0,
            "pitch": 0,
            "sampleRate": 48000,
            "format": "MP3",
            "channelType": "MONO"
        }
        
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key
        }

        for attempt in range(retries + 1):
            try:
                logger.info(f"Calling Murf API (attempt {attempt + 1}/{retries + 1})...")
                
                response = requests.post(
                    self.base_url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    logger.info("Murf TTS generation successful")
                    return response.content
                elif response.status_code == 401:
                    logger.error("Murf API authentication failed - check API key")
                    return None
                elif response.status_code == 429:
                    logger.warning("Murf API rate limit exceeded")
                    if attempt < retries:
                        import time
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                else:
                    logger.error(f"Murf API Error {response.status_code}: {response.text}")
                    if attempt < retries:
                        continue
                    return None
                    
            except requests.exceptions.Timeout:
                logger.error(f"Murf API timeout (attempt {attempt + 1})")
                if attempt < retries:
                    continue
                return None
            except requests.exceptions.ConnectionError:
                logger.error(f"Murf API connection error (attempt {attempt + 1})")
                if attempt < retries:
                    continue
                return None
            except Exception as e:
                logger.error(f"Unexpected error calling Murf API: {e}")
                return None
        
        return None

murf_client = MurfClient()

