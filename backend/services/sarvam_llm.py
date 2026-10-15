"""
SARVAM-105B LLM Integration for ZooLingo translation.

Turns template English phrases into natural, context-aware translations in
English or Hindi using Sarvam AI's sovereign LLM (sarvam-105b-conversations).

Falls back to the original English text if the LLM is unavailable.
"""

import requests
import os
import time
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class SarvamLLMTranslator:
    """Multilingual translator powered by Sarvam-105B."""

    CHAT_URL = "https://api.sarvam.ai/v1/chat/completions"

    # BCP-47 codes the LLM should be instructed to emit (English + Hindi MVP)
    LANGUAGE_NAMES = {
        "hi": "Hindi (Devanagari)",
        "hi-IN": "Hindi (Devanagari)",
        "en": "English",
        "en-IN": "English (Indian)",
    }

    INTENSE_EMOTIONS = {
        "Angry",
        "Excited",
        "Scared",
        "Pain",
        "Aggressive",
        "Alert",
        "Demanding",
        "Bossy",
        "Mischievous",
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SARVAM_API_KEY")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json",
        }
        self.stats = {"requests": 0, "total_latency_ms": 0}

    def _language_name(self, language_code: str) -> str:
        return self.LANGUAGE_NAMES.get(
            language_code, language_code.split("-")[0].capitalize()
        )

    def translate(
        self,
        english_text: str,
        animal: str,
        emotion: str,
        target_language: str = "hi-IN",
        timeout: int = 15,
    ) -> str:
        """Translate an English phrase into English or Hindi (MVP)."""
        if not self.api_key:
            return english_text

        # Restrict to the English + Hindi MVP; fall back to English otherwise
        lang_key = target_language.strip()
        if lang_key not in self.LANGUAGE_NAMES:
            return english_text
        if lang_key.lower() in ("en", "en-in"):
            return english_text

        language = self._language_name(lang_key)
        tone_hint = (
            "high-energy, urgent"
            if emotion in self.INTENSE_EMOTIONS
            else "gentle, natural"
        )

        system_msg = (
            "You are ZooLingo, an AI that renders a {animal}'s vocalization into "
            "what the animal would say to its human, translated into {language}. "
            "Return ONLY the spoken translation as a first-person sentence in "
            "{language} script (no quotes, no explanation, no English). "
            "Match a {tone} tone."
        ).format(animal=animal, language=language, tone=tone_hint)

        user_msg = (
            "Animal: {animal}\n"
            "Emotion: {emotion}\n"
            'English rendering: "{text}"\n'
            "Translate the rendering above into {language} as a natural, "
            "first-person sentence."
        ).format(animal=animal, emotion=emotion, text=english_text, language=language)

        payload = {
            "model": "sarvam-105b-conversations",
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            "temperature": 0.5,
            "max_tokens": 250,
        }

        start = time.time()
        try:
            resp = requests.post(
                self.CHAT_URL, headers=self.headers, json=payload, timeout=timeout
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()

            self.stats["requests"] += 1
            self.stats["total_latency_ms"] += int((time.time() - start) * 1000)

            # Strip quotes / markdown fences if the model added them
            content = content.strip('"').strip("'")
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            return content or english_text
        except Exception as e:
            print(f"[SarvamLLM] translation failed, using English: {e}")
            return english_text

    def status(self) -> dict:
        avg = (
            int(self.stats["total_latency_ms"] / self.stats["requests"])
            if self.stats["requests"]
            else 0
        )
        return {
            "enabled": bool(self.api_key),
            "requests": self.stats["requests"],
            "avg_latency_ms": avg,
        }


llm_translator = SarvamLLMTranslator()
