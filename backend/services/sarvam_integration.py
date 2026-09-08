"""
SARVAM Samvaad (Bulbul v3) TTS Integration for ZooLingo
Provides multilingual Indian language support (Hindi, Tamil, Bengali, etc.)
Get API key: https://dashboard.sarvam.ai
"""

import requests
import os
import time
import base64
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

class SarvamTTSClient:
    """Client for SARVAM Text-to-Speech API (Bulbul v3)"""

    BASE_URL = "https://api.sarvam.ai"

    # Available Indian language voice speakers (bulbul:v3)
    SPEAKERS = {
        'hindi': {
            'female': 'ritu',
            'male': 'shubh',
            'child': 'tanya'
        },
        'tamil': {
            'female': 'kavitha',
            'male': 'gokul'
        },
        'bengali': {
            'female': 'sweta',
            'male': 'amit'
        },
        'marathi': {
            'female': 'priya',
            'male': 'aditya'
        },
        'gujarati': {
            'female': 'pooja',
            'male': 'rahul'
        },
        'telugu': {
            'female': 'kavya',
            'male': 'rohan'
        },
        'kannada': {
            'female': 'shreya',
            'male': 'varun'
        },
        'malayalam': {
            'female': 'ishita',
            'male': 'sumit'
        },
        'punjabi': {
            'female': 'simran',
            'male': 'dev'
        },
        'english': {
            'female': 'neha',
            'male': 'rohan'
        }
    }

    # BCP-47 language codes
    LANGUAGE_CODES = {
        'hindi': 'hi-IN',
        'tamil': 'ta-IN',
        'bengali': 'bn-IN',
        'marathi': 'mr-IN',
        'gujarati': 'gu-IN',
        'telugu': 'te-IN',
        'kannada': 'kn-IN',
        'malayalam': 'ml-IN',
        'punjabi': 'pa-IN',
        'english': 'en-IN',
        'odia': 'od-IN'
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_speaker: str = "shubh",
        default_language_code: str = "hi-IN",
        model: str = "bulbul:v3"
    ):
        """Initialize SARVAM TTS client"""
        self.api_key = api_key or os.getenv('SARVAM_API_KEY')

        if not self.api_key:
            print("Warning: SARVAM_API_KEY not found. Using fallback TTS.")
            print("   Get free API key: https://dashboard.sarvam.ai")
            print("   You get free credits on signup")

        self.default_speaker = default_speaker
        self.default_language_code = default_language_code
        self.model = model
        self.headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json"
        }

        # Track usage for cost estimation
        self.usage_stats = {
            'total_requests': 0,
            'total_characters': 0,
            'total_cost_inr': 0.0
        }

    def generate_speech(
        self,
        text: str,
        speaker: Optional[str] = None,
        language_code: Optional[str] = None,
        pace: float = 1.0,
        sample_rate: int = 24000,
        save_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate speech using SARVAM Bulbul v3 TTS"""
        if not self.api_key:
            return {
                'success': False,
                'error': 'SARVAM_API_KEY not configured',
                'message': 'Get free API key from https://dashboard.sarvam.ai'
            }

        speaker = speaker or self.default_speaker
        language_code = language_code or self.default_language_code

        payload = {
            "text": text,
            "language_code": language_code,
            "speaker": speaker,
            "pace": max(0.5, min(2.0, pace)),
            "speech_sample_rate": sample_rate,
            "output_audio_codec": "mp3",
            "model": self.model
        }

        start_time = time.time()

        try:
            response = requests.post(
                f"{self.BASE_URL}/text-to-speech",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            latency_ms = int((time.time() - start_time) * 1000)

            # SARVAM pricing: ₹30 per 10K characters
            char_count = len(text)
            cost_inr = (char_count / 10000) * 30

            # Update usage stats
            self.usage_stats['total_requests'] += 1
            self.usage_stats['total_characters'] += char_count
            self.usage_stats['total_cost_inr'] += cost_inr

            # Decode base64 audio
            audio_data = None
            audios = result.get('audios', [])
            if audios:
                try:
                    audio_data = base64.b64decode(audios[0])
                except Exception as e:
                    print(f"Warning: Failed to decode audio: {str(e)}")

            # Save audio file if path provided
            if save_path and audio_data:
                with open(save_path, 'wb') as f:
                    f.write(audio_data)

            return {
                'success': True,
                'request_id': result.get('request_id'),
                'audio_data': audio_data,
                'char_count': char_count,
                'cost_inr': round(cost_inr, 4),
                'language_code': language_code,
                'speaker': speaker,
                'latency_ms': latency_ms,
                'usage_stats': self.usage_stats.copy()
            }

        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f"SARVAM TTS API error: {str(e)}",
                'latency_ms': int((time.time() - start_time) * 1000)
            }

    def get_available_speakers(self) -> dict:
        """Get list of available SARVAM speakers"""
        return {
            'bulbul_v3': ['shubh', 'aditya', 'ritu', 'priya', 'neha', 'rahul',
                          'pooja', 'rohan', 'simran', 'kavya', 'amit', 'dev',
                          'ishita', 'shreya', 'ratan', 'varun', 'manan', 'sumit',
                          'roopa', 'kabir', 'aayan', 'ashutosh', 'advait', 'anand',
                          'tanya', 'tarun', 'sunny', 'mani', 'gokul', 'vijay',
                          'shruti', 'suhani', 'mohit', 'kavitha', 'rehan', 'soham',
                          'rupali']
        }

    def get_usage_summary(self) -> Dict[str, Any]:
        """Get usage statistics and cost summary"""
        return {
            'total_requests': self.usage_stats['total_requests'],
            'total_characters': self.usage_stats['total_characters'],
            'total_cost_inr': round(self.usage_stats['total_cost_inr'], 4)
        }


# Example usage
if __name__ == "__main__":
    sarvam = SarvamTTSClient()

    result = sarvam.generate_speech(
        text="आपका कुत्ता भूखा है और खाना चाहता है",
        language_code="hi-IN",
        speaker="shubh",
        save_path="test_hindi.mp3"
    )

    if result['success']:
        print(f"Success! Request ID: {result['request_id'][:20]}...")
        print(f"   Characters: {result['char_count']}")
        print(f"   Cost: ₹{result['cost_inr']}")
        print(f"   Latency: {result['latency_ms']}ms")
        print(f"   Audio bytes: {len(result['audio_data']) if result['audio_data'] else 0}")
    else:
        print(f"Error: {result.get('error')}")