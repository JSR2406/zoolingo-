"""
ElevenLabs Sound-Effect generation client.

Used by ZooLingo to pre-generate consistent dog/cat emotion sounds for the
demo experience (and as training augmentation for the classifier).

API (verified against ElevenLabs docs 2026):
    POST https://api.elevenlabs.io/v1/sound-generation
    headers: xi-api-key, Content-Type: application/json
    body: {text, duration_seconds, prompt_influence, model_id}
    query: output_format (e.g. "pcm_22050" -> raw signed-16-bit PCM, 22050 Hz)
    returns: the generated audio binary
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request

ENDPOINT = "https://api.elevenlabs.io/v1/sound-generation"
DEFAULT_MODEL = "eleven_text_to_sound_v2"

# Sample rate implied by ElevenLabs "pcm_22050" output format
PCM_SAMPLE_RATE = 22050


class ElevenLabsSFX:
    """Thin HTTP client for ElevenLabs text-to-sound-effects."""

    def __init__(self, api_key=None):
        self.api_key = api_key if api_key else os.getenv("ELEVENLABS_API_KEY", "")

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def generate_sound_effect(
        self,
        text: str,
        duration_seconds: float = 2.5,
        output_format: str = "pcm_22050",
        prompt_influence: float = 0.6,
        model_id: str = DEFAULT_MODEL,
    ) -> bytes:
        """
        Generate a sound effect from a text description.

        Returns raw audio bytes. For output_format="pcm_22050" these are
        signed 16-bit little-endian PCM samples at 22050 Hz (mono).
        """
        if not self.configured:
            raise RuntimeError("ELEVENLABS_API_KEY is not configured")

        payload = {
            "text": text,
            "model_id": model_id,
            "prompt_influence": prompt_influence,
        }
        if duration_seconds:
            payload["duration_seconds"] = float(duration_seconds)

        url = ENDPOINT + "?" + urllib.parse.urlencode({"output_format": output_format})
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "xi-api-key": self.api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:500]
            raise RuntimeError(
                f"ElevenLabs sound-generation error {e.code}: {detail}"
            ) from e

    @staticmethod
    def pcm_to_samples(pcm_bytes: bytes):
        """Decode raw s16le PCM into float32 in [-1, 1]."""
        import numpy as np

        samples = np.frombuffer(pcm_bytes, dtype="<i2").astype(np.float32) / 32768.0
        return samples


sfx_client = ElevenLabsSFX()
